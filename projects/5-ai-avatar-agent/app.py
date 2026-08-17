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

    return "", display, chat, format_tool_log(result["tool_log"])


async def on_speak(answer: str, make_video: bool, agent):
    """Озвучивает последний ответ и, если попросили, снимает видео."""
    if not answer or not answer.strip():
        return None, None, "Сначала получи текстовый ответ."
    try:
        audio_path = await agent.speak(answer)
    except Exception as error:  # noqa: BLE001
        return None, None, f"Озвучка не удалась: {error}"

    if not make_video:
        return str(audio_path), None, "Готово: аудио."

    try:
        video_path = await agent.make_video(str(audio_path))
    except Exception as error:  # noqa: BLE001
        return str(audio_path), None, f"Аудио готово, видео не собралось: {error}"
    return str(audio_path), str(video_path), "Готово: аудио и видео."


def build_ui(agent: Agent) -> gr.Blocks:
    """Собирает интерфейс. agent передаётся снаружи, чтобы его можно было подменить."""
    with gr.Blocks(title="AI Avatar Agent — рестораны Алматы") as demo:
        gr.Markdown(
            "# 🍽️ Проводник по ресторанам Алматы\n"
            "Спроси текстом, голосом или пришли фото заведения."
        )
        history_state = gr.State([])
        last_answer = gr.State("")

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(type="messages", height=420, label="Диалог")
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
            answer = display[-1]["content"] if display else ""
            return textbox_value, display, new_history, log, answer

        send.click(
            _send,
            [textbox, audio_in, image_in, history_state],
            [textbox, chatbot, history_state, tool_log, last_answer],
        )
        textbox.submit(
            _send,
            [textbox, audio_in, image_in, history_state],
            [textbox, chatbot, history_state, tool_log, last_answer],
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
