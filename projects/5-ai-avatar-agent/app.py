"""Gradio-интерфейс агента.

Текстовый ответ приходит всегда и сразу. Озвучка и видео — только по кнопке:
это самые дорогие шаги, автоматически их запускать нельзя.
"""

from __future__ import annotations

import json

import gradio as gr

import config
from agent.pipeline import Agent


def format_tool_log(entries: list[dict]) -> str:
    """Готовит лог вызовов инструментов для показа в интерфейсе."""
    if not entries:
        return "Инструменты не вызывались."
    lines = []
    for entry in entries:
        arguments = json.dumps(entry.get("arguments", {}), ensure_ascii=False)
        if entry.get("error"):
            lines.append(f"❌ {entry['name']}({arguments}) → ошибка: {entry['error']}")
        else:
            lines.append(f"🛠 {entry['name']}({arguments}) → записей: {entry.get('result_size', 0)}")
    return "\n".join(lines)


def _as_display_messages(history: list) -> list[dict]:
    """Оставляет для чата только реплики пользователя и ассистента.

    Записи истории бывают двух форм: сообщения пользователя и инструментов —
    обычные словари, а ответы ассистента — сырые объекты OpenAI SDK
    (атрибуты, не ключи), поэтому доступ к роли и содержимому — с оглядкой
    на обе формы.
    """
    display: list[dict] = []
    for message in history:
        role = message.get("role") if isinstance(message, dict) else getattr(message, "role", None)
        if role not in ("user", "assistant"):
            continue
        content = message.get("content") if isinstance(message, dict) else message.content
        if isinstance(content, list):
            content = " ".join(part.get("text", "") for part in content if part.get("type") == "text")
        if not content:
            continue
        display.append({"role": role, "content": content})
    return display


def extract_last_answer(display: list[dict]) -> str:
    """Достаёт текст последнего ответа ассистента из отображаемого чата.

    Используется, чтобы привязать к кнопке «Озвучить» именно ответ, а не
    последнюю реплику вообще. on_send гарантирует (см. ниже), что когда
    result["answer"] непусто, оно оказывается последним элементом display
    с ролью assistant — поэтому этой проверки достаточно: если последняя
    реплика не assistant (например, ответ модели пуст и его нечем было
    показать), безопаснее вернуть пустую строку, чем случайно отдать на
    озвучку вопрос пользователя за ~$1.02 (см. I2 финального ревью).
    """
    if display and display[-1]["role"] == "assistant":
        return display[-1]["content"]
    return ""


async def on_send(text, audio, image, history, agent):
    """Обрабатывает отправку сообщения: возвращает очищенное поле, чат, историю и лог."""
    try:
        result = await agent.ask(text or "", audio, image, history)
    except Exception as error:  # noqa: BLE001
        raise gr.Error(f"Агент не смог ответить: {error}") from error

    chat = result["history"]
    display = _as_display_messages(chat)

    # Фейковые (и некоторые реальные) реализации агента могут не класть
    # реплику пользователя в возвращаемую историю сами — гарантируем, что
    # в диалоге виден и вопрос, и ответ, а не только ответ.
    #
    # Раньше решение "добавлять или нет" принималось по тому, является ли
    # ПЕРВОЕ отображаемое сообщение репликой пользователя. Это ломалось на
    # длинных сессиях: после того как trim_history (agent/llm.py) обрезает
    # историю по MAX_HISTORY_MESSAGES, первым отображаемым сообщением может
    # оказаться ответ ассистента на более ранний, уже не показываемый ход —
    # хотя текущий вопрос пользователя уже присутствует в history дальше.
    # Guard срабатывал и подставлял текущий вопрос ещё раз, в начало чата,
    # хотя он уже корректно стоял внизу — пользователь видел вопрос дважды.
    #
    # Теперь проверяем содержимое, а не позицию: если текущий вопрос уже
    # встречается среди реплик пользователя в display — ничего не делаем.
    # Если нет (как в тестовом двойнике, который не кладёт реплику
    # пользователя в историю сам) — вставляем его на правильное по смыслу
    # место: непосредственно перед ответом ассистента на этот вопрос, а не
    # в начало диалога.
    question = result.get("question") or text or ""
    if question:
        already_shown = any(
            message["role"] == "user" and message["content"] == question
            for message in display
        )
        if not already_shown:
            if display and display[-1]["role"] == "assistant":
                display = display[:-1] + [{"role": "user", "content": question}] + display[-1:]
            else:
                display = display + [{"role": "user", "content": question}]

    # I2/M2: result["answer"] — единственный правдивый источник ответа.
    # Раньше вызывающая сторона (build_ui._send) брала display[-1]["content"]
    # напрямую, а run_turn (agent/llm.py) при срабатывании лимита вызовов
    # инструментов кладёт в историю только assistant-сообщение с tool_calls
    # и пустым content — сам CAP_REACHED_MESSAGE в history не попадает. Из-за
    # этого _as_display_messages отбрасывал это сообщение (пустой content),
    # и последней отображаемой репликой оставался вопрос ПОЛЬЗОВАТЕЛЯ — его
    # затем и озвучивали за ~$1.02 при нажатии "Озвучить". То же самое
    # затрагивало M2: пустой сабмит — result["answer"] заполнен подсказкой
    # ("Напиши вопрос..."), но pipeline.ask не трогает history вовсе, и
    # подсказка нигде не показывалась.
    #
    # Чиним в одном месте: если result["answer"] непустой и его ещё нет в
    # конце display как ответа ассистента — дописываем его туда сами. После
    # этого extract_last_answer() и любой другой код, читающий "последний
    # ответ" из display, видит правильный текст.
    answer = result.get("answer") or ""
    if answer and extract_last_answer(display) != answer:
        display = display + [{"role": "assistant", "content": answer}]

    return "", display, chat, format_tool_log(result["tool_log"])


def mock_banner_text() -> str | None:
    """Текст предупреждения о mock-режиме для шапки интерфейса.

    None, если FAL_MOCK выключен — тогда баннер вообще не рисуется. Вынесено
    в отдельную функцию, чтобы её можно было проверить тестом без разбора
    внутренностей gr.Blocks.
    """
    if not config.FAL_MOCK:
        return None
    return (
        "🧪 **Включён режим заглушки (FAL_MOCK=1).** Распознавание голоса, "
        "озвучка ответа и видео с аватаром — ПОДДЕЛЬНЫЕ: голосовой вопрос "
        "заменяется заранее заданным текстом (с префиксом "
        "«[РЕЖИМ ЗАГЛУШКИ...]»), а аудио- и видеофайлы — пустышки на 0 байт. "
        "Чтобы включить настоящие платные вызовы fal.ai, поставь `FAL_MOCK=0` "
        "и задай `FAL_KEY` в `.env` в корне репозитория."
    )


async def on_speak(answer: str, make_video: bool, agent):
    """Озвучивает последний ответ и, если попросили, снимает видео."""
    if not answer or not answer.strip():
        return None, None, "Сначала получи текстовый ответ."
    try:
        audio_path = await agent.speak(answer)
    except Exception as error:  # noqa: BLE001
        return None, None, f"Озвучка не удалась: {error}"

    # C1: в mock-режиме falcost.download() пишет 0-байтовые файлы-заглушки.
    # Нельзя говорить пользователю "Готово" — это создаёт впечатление, что
    # получен настоящий звук/видео, хотя файл пустой.
    if not make_video:
        if config.FAL_MOCK:
            status = (
                "🧪 Mock-режим: аудио НЕ озвучено по-настоящему, файл — "
                "пустая заглушка. Выключи FAL_MOCK, чтобы получить реальный звук."
            )
        else:
            status = "Готово: аудио."
        return str(audio_path), None, status

    try:
        video_path = await agent.make_video(str(audio_path))
    except Exception as error:  # noqa: BLE001
        return str(audio_path), None, f"Аудио готово, видео не собралось: {error}"

    if config.FAL_MOCK:
        status = (
            "🧪 Mock-режим: аудио и видео НЕ сгенерированы по-настоящему, "
            "файлы — пустые заглушки. Выключи FAL_MOCK, чтобы получить реальный результат."
        )
    else:
        status = "Готово: аудио и видео."
    return str(audio_path), str(video_path), status


def build_ui(agent: Agent) -> gr.Blocks:
    """Собирает интерфейс. agent передаётся снаружи, чтобы его можно было подменить."""
    with gr.Blocks(title="AI Avatar Agent — рестораны Алматы") as demo:
        gr.Markdown(
            "# 🍽️ Проводник по ресторанам Алматы\n"
            "Спроси текстом, голосом или пришли фото заведения."
        )
        banner = mock_banner_text()
        if banner:
            gr.Markdown(banner)
        history_state = gr.State([])
        last_answer = gr.State("")

        with gr.Row():
            with gr.Column(scale=3):
                # В Gradio 6 формат сообщений ({"role", "content"}) единственный,
                # а параметр type удалён — передавать его нельзя, приложение упадёт
                # на старте. В Gradio 5 он был обязателен, поэтому версия закреплена
                # в requirements.txt.
                chatbot = gr.Chatbot(height=420, label="Диалог")
                textbox = gr.Textbox(
                    placeholder="Где поужинать в центре на двоих, бюджет 15 000 тенге?",
                    label="Вопрос",
                )
                with gr.Row():
                    audio_in = gr.Audio(
                        sources=["microphone", "upload"], type="filepath", label="Голос"
                    )
                    image_in = gr.Image(type="filepath", label="Фото заведения или блюда")
                send = gr.Button("Спросить", variant="primary")

            with gr.Column(scale=2):
                make_video = gr.Checkbox(label="Сгенерировать видео с аватаром", value=False)
                speak = gr.Button("🎙️ Озвучить последний ответ")
                status = gr.Markdown("")
                audio_out = gr.Audio(label="Ответ голосом", interactive=False)
                video_out = gr.Video(label="Видео с аватаром", interactive=False)
                with gr.Accordion("Лог вызовов инструментов", open=True):
                    tool_log = gr.Textbox(label="", lines=8, interactive=False)

        async def _send(text, audio, image, history):
            # Ни один платный шаг (озвучка, видео) здесь не запускается —
            # только текстовый ответ. Это единственный обработчик, привязанный
            # к отправке вопроса.
            textbox_value, display, new_history, log = await on_send(
                text, audio, image, history, agent
            )
            # I2: берём ответ через extract_last_answer(), а не сырым
            # display[-1] — on_send уже гарантирует, что непустой
            # result["answer"] оказывается там последней репликой ассистента,
            # а extract_last_answer() дополнительно подстраховывает: если
            # последняя реплика всё же не ассистентская, отдаёт "", а не
            # чужой вопрос, который иначе улетел бы в платную озвучку/видео.
            answer = extract_last_answer(display)
            # M3: очищаем поля голоса и фото после успешной отправки — иначе
            # следующий ход молча повторно пришлёт то же фото и заново
            # распознает то же аудио (лишние токены и повторный платный
            # вызов ASR).
            return textbox_value, display, new_history, log, answer, None, None

        send.click(
            _send,
            [textbox, audio_in, image_in, history_state],
            [textbox, chatbot, history_state, tool_log, last_answer, audio_in, image_in],
        )
        textbox.submit(
            _send,
            [textbox, audio_in, image_in, history_state],
            [textbox, chatbot, history_state, tool_log, last_answer, audio_in, image_in],
        )

        async def _speak(answer, video_wanted):
            # Срабатывает только по явному нажатию кнопки — единственный
            # путь, откуда вызываются platные agent.speak/agent.make_video.
            return await on_speak(answer, video_wanted, agent)

        speak.click(_speak, [last_answer, make_video], [audio_out, video_out, status])

    return demo


def main() -> None:
    # Ключи проверяем синхронно, до старта интерфейса. MCP-серверы поднимутся
    # лениво внутри событийного цикла Gradio — см. комментарий в Agent.start().
    config.load_environment()
    config.require_keys(need_fal=not config.FAL_MOCK)
    build_ui(Agent()).launch()


if __name__ == "__main__":
    main()
