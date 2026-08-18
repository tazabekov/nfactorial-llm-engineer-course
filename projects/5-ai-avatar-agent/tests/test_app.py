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


def test_build_ui_constructs_without_errors():
    """Интерфейс должен собираться — иначе приложение падает на старте.

    Этот тест ловит несовместимости с версией Gradio (например, удалённый
    в Gradio 6 параметр Chatbot(type=...)), которые остальные тесты не видят:
    они дёргают обработчики напрямую, минуя build_ui.
    """
    demo = app.build_ui(FakeAgent())
    assert demo is not None
