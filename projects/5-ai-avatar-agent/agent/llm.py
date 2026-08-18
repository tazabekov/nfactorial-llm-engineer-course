"""Цикл tool calling: сердце агента.

Не знает ни про Gradio, ни про fal, ни про Playwright — только про сообщения,
инструменты и модель.
"""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

from config import AGENT_MODEL, MAX_HISTORY_MESSAGES, MAX_TOOL_CALLS
from agent.skills import ANALYZE_TOOL_SPEC, analyze_restaurant_photo, encode_image

SYSTEM_PROMPT = """Ты — персональный проводник по ресторанам Алматы.

Правила:
1. Отвечай только на основе данных, полученных из инструментов. Ничего не выдумывай:
   ни названий, ни адресов, ни цен.
2. Если инструмент вернул пустой список или поле error — честно скажи, что данные
   получить не удалось, и предложи уточнить запрос.
3. Найдя подходящие заведения в 2GIS, проверь по Chocolife, нет ли на них скидок.
4. Если пользователь прислал фотографию заведения — вызови analyze_restaurant_photo
   и учти вердикт в рекомендации.
5. Ответ должен звучать 15–30 секунд вслух: три-четыре предложения, максимум три
   заведения, с адресом и одной причиной выбора для каждого. Без списков и markdown —
   текст пойдёт в озвучку.
6. Помни, о чём шла речь раньше в диалоге, и не переспрашивай уже сказанное."""

CAP_REACHED_MESSAGE = (
    "Я исчерпал лимит обращений к источникам и отвечаю по тому, что успел собрать."
)


def _msg_role(message: Any) -> str:
    """Роль сообщения независимо от формы: dict (user/tool) или raw SDK-объект
    (assistant — сырые ответы модели в истории всегда только ассистентские)."""
    if isinstance(message, dict):
        return message.get("role", "")
    return "assistant"


def _msg_tool_calls(message: Any) -> list:
    """tool_calls сообщения независимо от формы, либо пустой список."""
    if isinstance(message, dict):
        return message.get("tool_calls") or []
    return getattr(message, "tool_calls", None) or []


def _call_id(call: Any) -> str:
    return call["id"] if isinstance(call, dict) else call.id


def _msg_tool_call_id(message: Any) -> str | None:
    if isinstance(message, dict):
        return message.get("tool_call_id")
    return getattr(message, "tool_call_id", None)


def trim_history(messages: list, limit: int = MAX_HISTORY_MESSAGES) -> list:
    """Оставляет последние сообщения, но не в ущерб парности tool-вызовов.

    Инвариант, который обязан выполняться на выходе: для каждого assistant-
    сообщения с tool_calls в результате присутствуют tool-сообщения на ВСЕ его
    call_id, и у каждого tool-сообщения в результате есть его assistant-
    родитель. Простая обрезка messages[-limit:] ничего не знает про роли и
    может отрезать историю ровно между assistant-сообщением с tool_calls и
    его ответами (или оставить только хвост таких ответов) — тогда в начале
    среза окажется "осиротевшее" tool-сообщение или assistant с недоответившим
    tool_calls, и следующий вызов API с такой историей будет отклонён.

    Поэтому после обрезки по количеству мы проходим от начала среза и убираем
    подряд: (а) tool-сообщения, чей assistant-родитель уже не попал в срез,
    и (б) assistant-сообщения с tool_calls, не все call_id которых нашли
    ответ внутри среза (вместе с теми их ответами, что всё-таки попали —
    иначе они сами станут осиротевшими). Хвост среза трогать не нужно: он
    всегда заканчивается на завершённом обмене (см. run_turn).
    """
    sliced = messages[-limit:] if len(messages) > limit else list(messages)

    result = list(sliced)
    changed = True
    while changed and result:
        changed = False
        head = result[0]
        if _msg_role(head) == "tool":
            result.pop(0)
            changed = True
            continue
        calls = _msg_tool_calls(head)
        if calls:
            ids = {_call_id(c) for c in calls}
            present_ids = {
                _msg_tool_call_id(m) for m in result if _msg_role(m) == "tool"
            }
            if not ids.issubset(present_ids):
                result.pop(0)
                result = [
                    m
                    for m in result
                    if not (_msg_role(m) == "tool" and _msg_tool_call_id(m) in ids)
                ]
                changed = True
    return result


def build_user_message(text: str, image_path: str | None) -> dict:
    """Собирает сообщение пользователя, при наличии фото — мультимодальное.

    Если файл фото пропал или не читается, не роняем ход исключением (как и
    analyze_restaurant_photo в agent/skills.py) — деградируем до текстового
    сообщения с честной припиской, что фото прочитать не удалось.
    """
    if not image_path:
        return {"role": "user", "content": text}
    try:
        mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        data_url = f"data:{mime};base64,{encode_image(image_path)}"
    except OSError as error:
        return {
            "role": "user",
            "content": f"{text}\n\n(Не удалось прочитать присланное фото: {error})",
        }
    # Путь к файлу в текст НЕ кладём: этот текст идёт прямиком в чат, который
    # видит пользователь (app.py собирает отображаемые реплики именно из
    # частей content с type == "text"), а локальный путь на диске сервера —
    # техническая деталь, которая ему не нужна и не должна быть видна. Модели
    # путь всё равно нужен — она передаёт его аргументом image_path в вызов
    # analyze_restaurant_photo — поэтому run_turn отдельно подмешивает его
    # системной подсказкой, которая в chat-историю не попадает (см. M4).
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
        ],
    }


async def _dispatch(
    name: str, arguments: dict, toolset: Any, client: Any, call_log: list
) -> str:
    """Направляет вызов в MCP или в локальный skill.

    MCP-вызовы toolset регистрирует в собственном call_log сам — этот кусок
    журнала run_turn считывает отдельно (см. срез toolset.call_log ниже).
    Локальные skill-вызовы toolset не видит вообще, поэтому здесь они
    записываются в call_log, принадлежащий run_turn — в той же форме
    (name, arguments, result_size/error), чтобы UI показывал их наравне с
    MCP-вызовами и не выглядело так, будто инструмент не вызывался.
    """
    if toolset.handles(name):
        return await toolset.call(name, arguments)
    if name == "analyze_restaurant_photo":
        result = await analyze_restaurant_photo(arguments.get("image_path", ""), client)
        payload = json.dumps(result, ensure_ascii=False)
        if isinstance(result, dict) and "error" in result:
            call_log.append({"name": name, "arguments": arguments, "error": result["error"]})
        else:
            call_log.append(
                {"name": name, "arguments": arguments, "result_size": len(payload)}
            )
        return payload
    return json.dumps({"error": f"Неизвестный инструмент: {name}"}, ensure_ascii=False)


async def run_turn(
    client: Any,
    toolset: Any,
    history: list,
    user_message: dict,
    image_path: str | None = None,
) -> tuple[str, list, list]:
    """Прогоняет один ход диалога.

    ``image_path`` — путь к присланному фото (если оно было), нужен только
    модели, чтобы передать его аргументом в вызов analyze_restaurant_photo.
    В user_message (и тем самым в chat-истории, которую видит пользователь)
    этого пути нет намеренно — см. build_user_message. Подсказка идёт
    отдельным system-сообщением, которое в конце хода отфильтровывается из
    persist-истории вместе с основным системным промптом
    (_is_history_message исключает role == "system").

    Возвращает текст ответа, обновлённую историю и лог вызовов инструментов
    за этот ход.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + trim_history(history)
    messages.append(user_message)
    if image_path:
        messages.append(
            {
                "role": "system",
                "content": (
                    f"Путь к файлу присланного фото для аргумента image_path "
                    f"инструмента analyze_restaurant_photo: {image_path}"
                ),
            }
        )

    tools = toolset.specs() + [ANALYZE_TOOL_SPEC]
    log_start = len(getattr(toolset, "call_log", []))
    local_log: list = []
    calls_made = 0
    answer = ""

    while True:
        completion = await client.chat.completions.create(
            model=AGENT_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        message = completion.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            answer = message.content or ""
            break

        if calls_made >= MAX_TOOL_CALLS:
            # Лимит достигнут: assistant-сообщение с tool_calls уже добавлено в
            # messages, а ни один из этих вызовов ещё не обработан. Оставить их
            # без ответа нельзя — OpenAI-совместимое API требует ровно одно
            # tool-сообщение на каждый tool_call, иначе следующий run_turn,
            # получив эту историю на вход, немедленно упадёт с ошибкой формата.
            # Вырезать assistant-сообщение из истории было бы проще, но тогда
            # стёрлось бы честное свидетельство того, что модель пыталась звать
            # инструменты — а UI и следующий ход должны видеть, что попытка
            # была, просто бюджет закончился. Поэтому отвечаем каждому
            # незакрытому вызову короткой tool-заглушкой и только потом рвём цикл.
            for call in message.tool_calls:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {"error": "лимит вызовов инструментов исчерпан"},
                            ensure_ascii=False,
                        ),
                    }
                )
            answer = CAP_REACHED_MESSAGE
            break

        for call in message.tool_calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                payload = json.dumps(
                    {"error": "аргументы пришли не в формате JSON"}, ensure_ascii=False
                )
            else:
                payload = await _dispatch(call.function.name, arguments, toolset, client, local_log)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": payload}
            )
            calls_made += 1

    new_history = trim_history([m for m in messages if _is_history_message(m)])
    # Лог за этот ход = MCP-вызовы (их регистрирует toolset.call_log — берём
    # только то, что появилось начиная с log_start) + локальные skill-вызовы
    # (analyze_restaurant_photo), которые toolset не видит и не пишет к себе.
    # toolset.call_log при этом не трогаем — это его собственный список.
    call_log = list(getattr(toolset, "call_log", [])[log_start:]) + local_log
    return answer, new_history, call_log


def _is_history_message(message: Any) -> bool:
    """Системный промпт в историю не кладём — он добавляется на каждом ходу."""
    if isinstance(message, dict):
        return message.get("role") != "system"
    return True
