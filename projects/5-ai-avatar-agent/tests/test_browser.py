import asyncio
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


async def test_start_launches_browser_only_once_under_concurrency(monkeypatch):
    start_calls = []
    launch_calls = []

    class _StubBrowser:
        async def close(self):
            return None

    class _StubChromium:
        async def launch(self, **kwargs):
            launch_calls.append(kwargs)
            await asyncio.sleep(0)  # даём другим корутинам шанс вклиниться
            return _StubBrowser()

    class _StubPlaywright:
        chromium = _StubChromium()

        async def stop(self):
            return None

    class _StubAsyncPlaywright:
        async def start(self):
            start_calls.append(1)
            await asyncio.sleep(0)  # тоже отдаём управление, чтобы вскрыть гонку
            return _StubPlaywright()

    monkeypatch.setattr(browser, "async_playwright", lambda: _StubAsyncPlaywright())

    pool = browser.BrowserPool()
    await asyncio.gather(*(pool.start() for _ in range(5)))

    assert len(start_calls) == 1
    assert len(launch_calls) == 1
    assert pool._browser is not None


async def test_throttle_serialises_concurrent_calls(monkeypatch):
    monkeypatch.setattr(browser, "THROTTLE_SECONDS", 0.05)
    pool = browser.BrowserPool()

    start = time.monotonic()
    await asyncio.gather(*(pool._throttle() for _ in range(4)))
    elapsed = time.monotonic() - start

    assert elapsed >= 3 * 0.05


async def _no_sleep(_seconds):
    return None
