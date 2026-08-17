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


def trim_history(messages: list, limit: int = MAX_HISTORY_MESSAGES) -> list:
    """Оставляет последние сообщения: суммаризация для этого проекта не окупается."""
    return messages[-limit:] if len(messages) > limit else messages


def build_user_message(text: str, image_path: str | None) -> dict:
    """Собирает сообщение пользователя, при наличии фото — мультимодальное."""
    if not image_path:
        return {"role": "user", "content": text}
    mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    data_url = f"data:{mime};base64,{encode_image(image_path)}"
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": f"{text}\n\n(Путь к присланному фото: {image_path})"},
            {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
        ],
    }


async def _dispatch(name: str, arguments: dict, toolset: Any, client: Any) -> str:
    """Направляет вызов в MCP или в локальный skill."""
    if toolset.handles(name):
        return await toolset.call(name, arguments)
    if name == "analyze_restaurant_photo":
        result = await analyze_restaurant_photo(arguments.get("image_path", ""), client)
        return json.dumps(result, ensure_ascii=False)
    return json.dumps({"error": f"Неизвестный инструмент: {name}"}, ensure_ascii=False)


async def run_turn(
    client: Any,
    toolset: Any,
    history: list,
    user_message: dict,
) -> tuple[str, list, list]:
    """Прогоняет один ход диалога.

    Возвращает текст ответа, обновлённую историю и лог вызовов инструментов
    за этот ход.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + trim_history(history)
    messages.append(user_message)

    tools = toolset.specs() + [ANALYZE_TOOL_SPEC]
    log_start = len(getattr(toolset, "call_log", []))
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
            # Лимит проверяется на границе хода, а не внутри пачки: на каждый
            # tool_call обязан быть ответ, иначе следующий запрос к API упадёт.
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
                payload = await _dispatch(call.function.name, arguments, toolset, client)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": payload}
            )
            calls_made += 1

    new_history = trim_history([m for m in messages if _is_history_message(m)])
    call_log = list(getattr(toolset, "call_log", [])[log_start:])
    return answer, new_history, call_log


def _is_history_message(message: Any) -> bool:
    """Системный промпт в историю не кладём — он добавляется на каждом ходу."""
    if isinstance(message, dict):
        return message.get("role") != "system"
    return True
