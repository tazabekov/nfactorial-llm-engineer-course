from pathlib import Path

import pytest

from voice import asr, clone, tts


async def test_transcribe_returns_stripped_text(monkeypatch):
    async def fake_upload(path):
        return "https://mock/audio.m4a"

    async def fake_run(model, arguments, mock_result):
        assert model == "fal-ai/whisper"
        assert arguments["audio_url"] == "https://mock/audio.m4a"
        return {"text": "  где поужинать  "}

    monkeypatch.setattr(asr.falcost, "upload", fake_upload)
    monkeypatch.setattr(asr.falcost, "run_model", fake_run)
    assert await asr.transcribe("/tmp/q.m4a") == "где поужинать"


async def test_voice_id_is_read_from_cache_without_calling_fal(tmp_path, monkeypatch):
    cache_file = tmp_path / "voice_id.txt"
    cache_file.write_text("voice-123", encoding="utf-8")
    monkeypatch.setattr(clone, "VOICE_ID_FILE", cache_file)

    async def explode(*args, **kwargs):
        raise AssertionError("клонировать повторно нельзя — это деньги")

    monkeypatch.setattr(clone.falcost, "run_model", explode)
    assert await clone.get_voice_id() == "voice-123"


async def test_clone_saves_custom_voice_id(tmp_path, monkeypatch):
    cache_file = tmp_path / "voice_id.txt"
    monkeypatch.setattr(clone, "VOICE_ID_FILE", cache_file)
    sample = tmp_path / "sample.m4a"
    sample.write_bytes(b"audio")

    async def fake_upload(path):
        return "https://mock/sample.m4a"

    async def fake_run(model, arguments, mock_result):
        assert model == "fal-ai/minimax/voice-clone"
        return {"custom_voice_id": "voice-999"}

    monkeypatch.setattr(clone.falcost, "upload", fake_upload)
    monkeypatch.setattr(clone.falcost, "run_model", fake_run)
    assert await clone.get_voice_id(str(sample)) == "voice-999"
    assert cache_file.read_text(encoding="utf-8").strip() == "voice-999"


async def test_clone_without_sample_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(clone, "VOICE_ID_FILE", tmp_path / "нет.txt")
    with pytest.raises(FileNotFoundError):
        await clone.get_voice_id(str(tmp_path / "нет.m4a"))


async def test_tts_uses_nested_voice_setting(tmp_path, monkeypatch):
    seen = {}

    async def fake_run(model, arguments, mock_result):
        seen.update(arguments)
        return {"audio": {"url": "https://mock/answer.mp3"}}

    def fake_download(url, target):
        Path(target).write_bytes(b"mp3")
        return Path(target)

    monkeypatch.setattr(tts.falcost, "run_model", fake_run)
    monkeypatch.setattr(tts.falcost, "download", fake_download)
    monkeypatch.setattr(tts, "OUTPUT_DIR", tmp_path)
    path = await tts.synthesize("Привет", "voice-1")
    assert seen["voice_setting"]["voice_id"] == "voice-1"
    assert path.exists()
