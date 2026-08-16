import time

import pytest

from mcp_servers.common import browser


async def test_with_retry_returns_first_success():
    calls = []

    async def factory():
        calls.append(1)
        return "ok"

    assert await browser.with_retry(factory) == "ok"
    assert len(calls) == 1


async def test_with_retry_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(browser.asyncio, "sleep", _no_sleep)
    calls = []

    async def factory():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("сеть отвалилась")
        return "ok"

    assert await browser.with_retry(factory, attempts=3) == "ok"
    assert len(calls) == 3


async def test_with_retry_reraises_after_last_attempt(monkeypatch):
    monkeypatch.setattr(browser.asyncio, "sleep", _no_sleep)

    async def factory():
        raise RuntimeError("всё плохо")

    with pytest.raises(RuntimeError, match="всё плохо"):
        await browser.with_retry(factory, attempts=2)


async def test_throttle_waits_between_calls(monkeypatch):
    monkeypatch.setattr(browser, "THROTTLE_SECONDS", 0.05)
    pool = browser.BrowserPool()
    start = time.monotonic()
    await pool._throttle()
    await pool._throttle()
    assert time.monotonic() - start >= 0.05


async def _no_sleep(_seconds):
    return None
