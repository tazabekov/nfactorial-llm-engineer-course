import json

import pytest

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


async def test_attempts_one_makes_single_attempt_then_raises(monkeypatch, tmp_path):
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
        await falcost.run_model("fal-ai/creatify/aurora", {}, {"video": "x"}, attempts=1)
    except RuntimeError:
        pass
    else:
        raise AssertionError("должно было упасть")
    assert len(attempts) == 1


async def test_attempts_default_still_makes_two(monkeypatch, tmp_path):
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


async def test_attempts_zero_or_negative_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(falcost, "FAL_MOCK", False)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")

    async def explode(*args, **kwargs):
        raise AssertionError("attempts<1 должен быть отклонён раньше сетевого вызова")

    monkeypatch.setattr(falcost.fal_client, "subscribe_async", explode)

    for bad_value in (0, -1):
        try:
            await falcost.run_model("fal-ai/whisper", {}, {"text": "x"}, attempts=bad_value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"attempts={bad_value} должен был быть отклонён")


def test_total_spent_sums_log(monkeypatch, tmp_path):
    log = tmp_path / "costs.jsonl"
    monkeypatch.setattr(falcost, "COST_LOG", log)
    falcost.record_cost("fal-ai/minimax/voice-clone")
    falcost.record_cost("fal-ai/minimax/voice-clone")
    assert falcost.total_spent() == falcost.PRICES["fal-ai/minimax/voice-clone"] * 2


def test_download_in_mock_mode_never_hits_network_even_with_realistic_url(monkeypatch, tmp_path):
    """download() должен смотреть на FAL_MOCK, а не угадывать mock по виду URL.

    Правдоподобный fal-URL (как в реальном ответе fal.media) не должен
    приводить к сетевому запросу, если включён mock-режим.
    """
    monkeypatch.setattr(falcost, "FAL_MOCK", True)

    def explode(*args, **kwargs):
        raise AssertionError("в mock-режиме download не должен трогать сеть")

    monkeypatch.setattr(falcost.urllib.request, "urlretrieve", explode)
    target = tmp_path / "out" / "result.mp4"
    result = falcost.download("https://v3.fal.media/files/tiger/abc123_output.mp4", target)
    assert result == target
    assert result.exists()


def test_unknown_model_records_flagged_entry_and_warns(monkeypatch, tmp_path, capsys):
    log = tmp_path / "costs.jsonl"
    monkeypatch.setattr(falcost, "COST_LOG", log)
    falcost.record_cost("fal-ai/some-new-model-nobody-priced-yet")
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert entries[0]["model"] == "fal-ai/some-new-model-nobody-priced-yet"
    assert entries[0]["unknown_price"] is True
    assert entries[0]["usd"] == 0.0
    captured = capsys.readouterr()
    assert "fal-ai/some-new-model-nobody-priced-yet" in captured.err


def test_total_spent_survives_corrupted_log_lines(monkeypatch, tmp_path):
    log = tmp_path / "costs.jsonl"
    monkeypatch.setattr(falcost, "COST_LOG", log)
    lines = [
        json.dumps({"at": 1.0, "model": "fal-ai/whisper", "usd": 0.01}),
        "42",  # валидный JSON, но не объект (например, оборванная запись)
        '{"at": 2.0, "model": "fal-ai/whisper", "usd"',  # truncated / невалидный JSON
        json.dumps({"at": 3.0, "model": "fal-ai/whisper", "usd": 0.01}),
    ]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert falcost.total_spent() == 0.02


def test_download_in_mock_mode_preserves_existing_real_file(monkeypatch, tmp_path):
    """Mock-режим не должен затирать уже скачанный настоящий файл.

    Сценарий из задания: дорогое видео генерируют последним, поэтому
    разработчик мог получить реальный файл, а затем перезапустить пайплайн
    в mock-режиме для отладки остального кода. Существующий непустой
    target — это тот самый результат, его нужно оставить нетронутым.
    """
    monkeypatch.setattr(falcost, "FAL_MOCK", True)
    target = tmp_path / "out" / "result.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"real video bytes")

    result = falcost.download("https://v3.fal.media/files/tiger/abc123_output.mp4", target)

    assert result == target
    assert target.read_bytes() == b"real video bytes"


def test_download_in_mock_mode_creates_placeholder_when_no_target(monkeypatch, tmp_path):
    """А если сохранять нечего — заглушка по-прежнему создаётся как раньше."""
    monkeypatch.setattr(falcost, "FAL_MOCK", True)
    target = tmp_path / "out" / "result.mp4"

    result = falcost.download("https://v3.fal.media/files/tiger/abc123_output.mp4", target)

    assert result == target
    assert target.exists()
    assert target.read_bytes() == b""


async def test_run_model_proceeds_when_below_budget_ceiling(monkeypatch, tmp_path):
    """I6: пока total_spent() ниже потолка, платный вызов должен пройти как
    обычно — бюджетный guard не должен мешать нормальной работе."""
    monkeypatch.setattr(falcost, "FAL_MOCK", False)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")
    monkeypatch.setattr(falcost, "FAL_BUDGET_CEILING_USD", 5.0)

    async def fake_subscribe(model, arguments=None, **kwargs):
        return {"ok": True}

    monkeypatch.setattr(falcost.fal_client, "subscribe_async", fake_subscribe)
    result = await falcost.run_model("fal-ai/whisper", {}, {"text": "x"})
    assert result == {"ok": True}


async def test_run_model_refuses_when_at_or_above_budget_ceiling(monkeypatch, tmp_path):
    """I6: как только total_spent() достиг потолка (или превысил его),
    run_model обязан отказать ДО реального платного вызова — деньги не
    должны тратиться сверх заявленного лимита."""
    monkeypatch.setattr(falcost, "FAL_MOCK", False)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")
    monkeypatch.setattr(falcost, "FAL_BUDGET_CEILING_USD", 1.0)
    # Уже потрачено ровно 1.00 — это "на уровне потолка", а не "выше".
    falcost.record_cost("fal-ai/creatify/aurora")

    async def explode(*args, **kwargs):
        raise AssertionError("бюджет исчерпан — платный вызов делать нельзя")

    monkeypatch.setattr(falcost.fal_client, "subscribe_async", explode)

    with pytest.raises(RuntimeError) as exc:
        await falcost.run_model("fal-ai/whisper", {}, {"text": "x"})
    message = str(exc.value)
    assert "1.0" in message or "1.00" in message
    assert "FAL_BUDGET_CEILING_USD" in message


async def test_run_model_budget_guard_does_not_apply_in_mock_mode(monkeypatch, tmp_path):
    """I6: mock-вызовы не должны затрагиваться потолком бюджета — они и так
    ничего не стоят и не должны отказывать даже при "исчерпанном" логе."""
    monkeypatch.setattr(falcost, "FAL_MOCK", True)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")
    monkeypatch.setattr(falcost, "FAL_BUDGET_CEILING_USD", 1.0)
    falcost.record_cost("fal-ai/creatify/aurora")

    async def explode(*args, **kwargs):
        raise AssertionError("в mock-режиме сеть трогать нельзя")

    monkeypatch.setattr(falcost.fal_client, "subscribe_async", explode)
    result = await falcost.run_model("fal-ai/whisper", {}, {"text": "заглушка"})
    assert result == {"text": "заглушка"}


def test_total_spent_warns_on_bad_amount_but_sums_valid_entries(monkeypatch, tmp_path, capsys):
    """Запись с некорректным usd не должна исчезать без следа.

    TypeError при сложении числа со строкой перехватывается (падать нельзя),
    но потеря записи из суммы должна быть видна в stderr — так же, как для
    неизвестных моделей.
    """
    log = tmp_path / "costs.jsonl"
    monkeypatch.setattr(falcost, "COST_LOG", log)
    lines = [
        json.dumps({"at": 1.0, "model": "fal-ai/whisper", "usd": 0.01}),
        json.dumps({"at": 2.0, "model": "fal-ai/whisper", "usd": "n/a"}),
        json.dumps({"at": 3.0, "model": "fal-ai/whisper", "usd": 0.01}),
    ]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    total = falcost.total_spent()

    assert total == 0.02
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
