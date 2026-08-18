from pathlib import Path

import pytest

from avatar import generate


async def test_uses_aurora_with_spec_parameters(tmp_path, monkeypatch):
    photo = tmp_path / "me.jpg"
    photo.write_bytes(b"jpg")
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"mp3")
    seen = {}

    async def fake_upload(path):
        return f"https://mock/{Path(path).name}"

    async def fake_run(model, arguments, mock_result, attempts=2):
        seen["model"] = model
        seen["arguments"] = arguments
        seen["attempts"] = attempts
        return {"video": {"url": "https://mock/v.mp4"}}

    monkeypatch.setattr(generate.falcost, "upload", fake_upload)
    monkeypatch.setattr(generate.falcost, "run_model", fake_run)
    monkeypatch.setattr(generate.falcost, "download", lambda url, target: Path(target))
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)

    await generate.generate_video(str(audio), str(photo))
    assert seen["model"] == "fal-ai/creatify/aurora"
    assert seen["arguments"]["guidance_scale"] == 1
    assert seen["arguments"]["audio_guidance_scale"] == 2
    assert seen["arguments"]["resolution"] == "720p"
    assert seen["attempts"] == 1


async def test_falls_back_to_kling_when_aurora_fails(tmp_path, monkeypatch):
    photo = tmp_path / "me.jpg"
    photo.write_bytes(b"jpg")
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"mp3")
    models = []

    async def fake_upload(path):
        return "https://mock/file"

    attempts_seen = []

    async def fake_run(model, arguments, mock_result, attempts=2):
        models.append(model)
        attempts_seen.append(attempts)
        if model == "fal-ai/creatify/aurora":
            raise RuntimeError("aurora недоступна")
        return {"video": {"url": "https://mock/v.mp4"}}

    monkeypatch.setattr(generate.falcost, "upload", fake_upload)
    monkeypatch.setattr(generate.falcost, "run_model", fake_run)
    monkeypatch.setattr(generate.falcost, "download", lambda url, target: Path(target))
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)

    await generate.generate_video(str(audio), str(photo))
    assert models == ["fal-ai/creatify/aurora", "fal-ai/kling-video/ai-avatar/v2/standard"]
    assert attempts_seen == [1, 1]


async def test_both_models_failing_costs_exactly_two_paid_invocations(tmp_path, monkeypatch):
    """Бюджетная гарантия: худший случай generate_video() — 2 платных вызова.

    Даже если и основная модель, и fallback падают, каждая должна быть
    вызвана ровно один раз (attempts=1), а не по два раза каждая (как было
    бы со штатным retry falcost.run_model). Иначе один неудачный прогон мог
    бы стоить до 4 платных попыток при бюджете проекта ~$15-20.
    """
    photo = tmp_path / "me.jpg"
    photo.write_bytes(b"jpg")
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"mp3")
    invocations = []

    async def fake_upload(path):
        return "https://mock/file"

    async def fake_run(model, arguments, mock_result, attempts=2):
        invocations.append((model, attempts))
        raise RuntimeError(f"{model} недоступна")

    monkeypatch.setattr(generate.falcost, "upload", fake_upload)
    monkeypatch.setattr(generate.falcost, "run_model", fake_run)
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)

    with pytest.raises(RuntimeError):
        await generate.generate_video(str(audio), str(photo))

    assert len(invocations) == 2
    assert invocations == [
        ("fal-ai/creatify/aurora", 1),
        ("fal-ai/kling-video/ai-avatar/v2/standard", 1),
    ]


async def test_missing_photo_raises_with_helpful_message(tmp_path, monkeypatch):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"mp3")
    monkeypatch.setattr(generate, "DEFAULT_PHOTO", tmp_path / "нет.jpg")
    with pytest.raises(FileNotFoundError, match="assets-private"):
        await generate.generate_video(str(audio))
