from pathlib import Path

from agent import pipeline


class FakeToolset:
    def __init__(self, *args, **kwargs):
        self.call_log = []
        self.opened = False

    async def open(self):
        self.opened = True

    async def close(self):
        self.opened = False

    def specs(self):
        return []

    def handles(self, name):
        return False


async def test_ask_transcribes_audio_when_no_text(monkeypatch):
    agent = pipeline.Agent()
    agent._toolset = FakeToolset()

    async def fake_transcribe(path):
        return "распознанный вопрос"

    async def fake_run_turn(client, toolset, history, user_message):
        return f"ответ на: {user_message['content']}", history + [user_message], []

    monkeypatch.setattr(pipeline, "transcribe", fake_transcribe)
    monkeypatch.setattr(pipeline, "run_turn", fake_run_turn)

    result = await agent.ask("", "/tmp/a.m4a", None, [])
    assert result["question"] == "распознанный вопрос"
    assert "распознанный вопрос" in result["answer"]


async def test_ask_returns_tool_log(monkeypatch):
    agent = pipeline.Agent()
    agent._toolset = FakeToolset()

    async def fake_run_turn(client, toolset, history, user_message):
        return "готово", history, [{"name": "twogis__search_restaurants", "result_size": 3}]

    monkeypatch.setattr(pipeline, "run_turn", fake_run_turn)
    result = await agent.ask("вопрос", None, None, [])
    assert result["tool_log"][0]["name"] == "twogis__search_restaurants"


async def test_start_is_lazy_and_idempotent(monkeypatch):
    created = []

    class TrackingToolset(FakeToolset):
        def __init__(self, servers):
            super().__init__()
            created.append(servers)

    monkeypatch.setattr(pipeline, "McpToolset", TrackingToolset)
    agent = pipeline.Agent()
    await agent.start()
    await agent.start()
    assert len(created) == 1


async def test_speak_uses_cached_voice(monkeypatch, tmp_path):
    agent = pipeline.Agent()
    calls = []

    async def fake_voice_id(sample_path=None):
        calls.append("voice")
        return "voice-1"

    async def fake_synthesize(text, voice_id):
        calls.append(f"tts:{voice_id}")
        return tmp_path / "a.mp3"

    monkeypatch.setattr(pipeline, "get_voice_id", fake_voice_id)
    monkeypatch.setattr(pipeline, "synthesize", fake_synthesize)
    path = await agent.speak("Привет")
    assert calls == ["voice", "tts:voice-1"]
    assert path == tmp_path / "a.mp3"


async def test_make_video_delegates(monkeypatch, tmp_path):
    agent = pipeline.Agent()

    async def fake_generate(audio_path, photo_path=None):
        return tmp_path / "v.mp4"

    monkeypatch.setattr(pipeline, "generate_video", fake_generate)
    assert await agent.make_video("/tmp/a.mp3") == tmp_path / "v.mp4"


def test_server_paths_point_to_existing_files():
    for path in pipeline.SERVER_PATHS.values():
        assert Path(path).exists()


def test_agent_construction_without_api_key(monkeypatch):
    """Agent() не должен трогать окружение: ключ может отсутствовать."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pipeline.Agent()


async def test_client_created_once_and_reused(monkeypatch):
    """Ленивый клиент собирается один раз (при первом обращении к атрибуту)
    и переиспользуется между вызовами."""
    created = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            created.append(1)
            self.marker = "fake"

    monkeypatch.setattr(pipeline, "AsyncOpenAI", FakeClient)
    agent = pipeline.Agent()

    first = agent._client.marker
    second = agent._client.marker

    assert len(created) == 1
    assert first == second == "fake"
