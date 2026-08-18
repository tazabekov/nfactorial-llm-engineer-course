import app


class FakeAgent:
    def __init__(self, answer="ответ"):
        self.answer = answer
        self.spoken = []
        self.videos = []

    async def ask(self, text, audio_path, image_path, history):
        return {
            "question": text or "распознано",
            "answer": self.answer,
            "history": history + [{"role": "assistant", "content": self.answer}],
            "tool_log": [{"name": "twogis__search_restaurants",
                          "arguments": {"query": "суши"}, "result_size": 2}],
        }

    async def speak(self, text):
        self.spoken.append(text)
        return "/tmp/a.mp3"

    async def make_video(self, audio_path):
        self.videos.append(audio_path)
        return "/tmp/v.mp4"


def test_format_tool_log_is_readable():
    text = app.format_tool_log(
        [{"name": "twogis__search_restaurants", "arguments": {"query": "суши"}, "result_size": 2}]
    )
    assert "twogis__search_restaurants" in text
    assert "суши" in text


def test_format_tool_log_empty():
    assert "не вызывались" in app.format_tool_log([])


async def test_on_send_appends_both_messages():
    agent = FakeAgent()
    textbox, chat, history, log = await app.on_send("привет", None, None, [], agent)
    assert textbox == ""
    assert chat[-2]["role"] == "user"
    assert chat[-1]["role"] == "assistant"
    assert "twogis" in log


class TrimmedHistoryAgent(FakeAgent):
    """Имитирует поведение реального Agent после trim_history: реплика
    пользователя уже есть в возвращаемой истории, но история обрезана так,
    что первым отображаемым сообщением оказывается более ранний ответ
    ассистента (а не текущий вопрос пользователя)."""

    async def ask(self, text, audio_path, image_path, history):
        question = text or "распознано"
        return {
            "question": question,
            "answer": self.answer,
            "history": [
                {"role": "assistant", "content": "старый ответ (обрезанный ход)"},
                {"role": "user", "content": question},
                {"role": "assistant", "content": self.answer},
            ],
            "tool_log": [],
        }


async def test_on_send_does_not_duplicate_question_after_trim():
    agent = TrimmedHistoryAgent()
    textbox, chat, history, log = await app.on_send("новый вопрос", None, None, [], agent)

    occurrences = [m for m in chat if m["role"] == "user" and m["content"] == "новый вопрос"]
    assert len(occurrences) == 1
    assert chat[-2] == {"role": "user", "content": "новый вопрос"}
    assert chat[-1] == {"role": "assistant", "content": agent.answer}


class CapReachedAgent(FakeAgent):
    """Имитирует поведение run_turn (agent/llm.py) при срабатывании лимита
    вызовов инструментов: CAP_REACHED_MESSAGE возвращается как answer, но в
    history остаётся только assistant-сообщение с tool_calls и пустым
    content — сам текст ответа в history не попадает. _as_display_messages
    отбрасывает такое сообщение (пустой content), поэтому последней
    отображаемой репликой оказывается вопрос ПОЛЬЗОВАТЕЛЯ."""

    async def ask(self, text, audio_path, image_path, history):
        question = text or "распознано"
        return {
            "question": question,
            "answer": self.answer,
            "history": history + [{"role": "user", "content": question}],
            "tool_log": [],
        }


async def test_on_send_uses_result_answer_when_history_ends_on_user_message():
    """I2: раньше в этом сценарии на кнопку "Озвучить" уходил вопрос
    пользователя вместо ответа модели — платная озвучка/видео улетали на
    чужой (пользовательский) текст."""
    agent = CapReachedAgent(
        answer="Я исчерпал лимит обращений к источникам и отвечаю по тому, что успел собрать."
    )
    textbox, chat, history, log = await app.on_send(
        "где поесть суши недорого", None, None, [], agent
    )

    assert chat[-1] == {"role": "assistant", "content": agent.answer}
    # Именно это значение build_ui._send отдаёт в last_answer (State,
    # привязанный к кнопке "Озвучить") — проверяем через extract_last_answer,
    # так же, как это делает сам _send.
    assert app.extract_last_answer(chat) == agent.answer
    assert app.extract_last_answer(chat) != "где поесть суши недорого"


class EmptySubmitAgent(FakeAgent):
    """Имитирует pipeline.ask на пустой сабмит: question == "", answer —
    подсказка пользователю, history не тронута вовсе."""

    async def ask(self, text, audio_path, image_path, history):
        return {
            "question": "",
            "answer": "Напиши вопрос, запиши голос или пришли фото.",
            "history": history,
            "tool_log": [],
        }


async def test_on_send_shows_empty_submit_hint():
    """M2: подсказку на пустой сабмит раньше нигде не показывали —
    pipeline.ask её возвращает в answer, но history не меняет, а on_send
    полагался только на history."""
    agent = EmptySubmitAgent()
    textbox, chat, history, log = await app.on_send("", None, None, [], agent)

    assert chat[-1] == {
        "role": "assistant",
        "content": "Напиши вопрос, запиши голос или пришли фото.",
    }


async def test_on_speak_without_video_returns_audio_only():
    agent = FakeAgent()
    audio, video, status = await app.on_speak("текст ответа", False, agent)
    assert audio == "/tmp/a.mp3"
    assert video is None
    assert agent.videos == []


async def test_on_speak_with_video_calls_generator():
    agent = FakeAgent()
    audio, video, status = await app.on_speak("текст ответа", True, agent)
    assert video == "/tmp/v.mp4"
    assert agent.videos == ["/tmp/a.mp3"]


async def test_on_speak_reports_failure_without_crashing():
    class BrokenAgent(FakeAgent):
        async def speak(self, text):
            raise RuntimeError("fal недоступен")

    audio, video, status = await app.on_speak("текст", True, BrokenAgent())
    assert audio is None
    assert "недоступен" in status


async def test_on_speak_mock_mode_status_says_so_not_gotovo(monkeypatch):
    """C1: в mock-режиме статус не должен звучать как "Готово" — файл
    пустой заглушка, а не настоящая запись."""
    monkeypatch.setattr(app.config, "FAL_MOCK", True)
    agent = FakeAgent()
    _, _, status = await app.on_speak("текст ответа", True, agent)
    assert "Готово" not in status
    assert "mock" in status.lower() or "заглушк" in status.lower()


async def test_on_speak_real_mode_status_says_gotovo(monkeypatch):
    """Реальный режим (FAL_MOCK=0) не должен потерять прежний текст."""
    monkeypatch.setattr(app.config, "FAL_MOCK", False)
    agent = FakeAgent()
    _, _, status = await app.on_speak("текст ответа", True, agent)
    assert status == "Готово: аудио и видео."


def test_mock_banner_present_when_fal_mock_on(monkeypatch):
    monkeypatch.setattr(app.config, "FAL_MOCK", True)
    banner = app.mock_banner_text()
    assert banner is not None
    assert "FAL_MOCK" in banner


def test_mock_banner_absent_when_fal_mock_off(monkeypatch):
    monkeypatch.setattr(app.config, "FAL_MOCK", False)
    assert app.mock_banner_text() is None


def test_build_ui_constructs_without_errors():
    """Интерфейс должен собираться — иначе приложение падает на старте.

    Этот тест ловит несовместимости с версией Gradio (например, удалённый
    в Gradio 6 параметр Chatbot(type=...)), которые остальные тесты не видят:
    они дёргают обработчики напрямую, минуя build_ui.
    """
    demo = app.build_ui(FakeAgent())
    assert demo is not None
