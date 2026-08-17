import json

import falcost


async def test_mock_mode_returns_mock_and_skips_network(monkeypatch, tmp_path):
    monkeypatch.setattr(falcost, "FAL_MOCK", True)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")

    async def explode(*args, **kwargs):
        raise AssertionError("в mock-режиме сеть трогать нельзя")

    monkeypatch.setattr(falcost.fal_client, "subscribe_async", explode)
    result = await falcost.run_model("fal-ai/whisper", {"a": 1}, {"text": "заглушка"})
    assert result == {"text": "заглушка"}


async def test_real_mode_calls_fal_and_records_cost(monkeypatch, tmp_path):
    monkeypatch.setattr(falcost, "FAL_MOCK", False)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")
    seen = {}

    async def fake_subscribe(model, arguments=None, **kwargs):
        seen["model"] = model
        seen["arguments"] = arguments
        return {"ok": True}

    monkeypatch.setattr(falcost.fal_client, "subscribe_async", fake_subscribe)
    result = await falcost.run_model("fal-ai/whisper", {"a": 1}, {"text": "заглушка"})
    assert result == {"ok": True}
    assert seen["model"] == "fal-ai/whisper"
    entries = [json.loads(line) for line in (tmp_path / "costs.jsonl").read_text().splitlines()]
    assert entries[0]["model"] == "fal-ai/whisper"


async def test_failure_retries_then_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(falcost, "FAL_MOCK", False)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")
    attempts = []

    async def flaky(model, arguments=None, **kwargs):
        attempts.append(1)
        raise RuntimeError("fal недоступен")

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(falcost.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(falcost.fal_client, "subscribe_async", flaky)
    try:
        await falcost.run_model("fal-ai/whisper", {}, {"text": "x"})
    except RuntimeError:
        pass
    else:
        raise AssertionError("должно было упасть")
    assert len(attempts) == 2


def test_total_spent_sums_log(monkeypatch, tmp_path):
    log = tmp_path / "costs.jsonl"
    monkeypatch.setattr(falcost, "COST_LOG", log)
    falcost.record_cost("fal-ai/minimax/voice-clone")
    falcost.record_cost("fal-ai/minimax/voice-clone")
    assert falcost.total_spent() == falcost.PRICES["fal-ai/minimax/voice-clone"] * 2
