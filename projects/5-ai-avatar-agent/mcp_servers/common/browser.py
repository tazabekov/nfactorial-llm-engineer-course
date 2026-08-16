"""Общий браузерный слой для MCP-серверов.

Один Chromium на процесс: запуск браузера — самая дорогая операция, поднимать
его на каждый запрос нельзя. Изоляция обеспечивается свежим контекстом на запрос.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

from playwright.async_api import Browser, Playwright, async_playwright

from config import PAGE_TIMEOUT_MS, THROTTLE_SECONDS

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


async def with_retry(factory: Callable[[], Awaitable[Any]], attempts: int = 2) -> Any:
    """Повторяет операцию с экспоненциальным бэкоффом, пробрасывая последнюю ошибку."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await factory()
        except Exception as error:  # noqa: BLE001 — сеть падает как угодно
            last_error = error
            if attempt < attempts - 1:
                await asyncio.sleep(2**attempt)
    raise last_error  # type: ignore[misc]


class BrowserPool:
    """Держит один браузер и следит, чтобы навигации не шли чаще, чем можно."""

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._last_navigation = 0.0
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._browser is not None:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)

    async def stop(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def _throttle(self) -> None:
        async with self._lock:
            elapsed = time.monotonic() - self._last_navigation
            if elapsed < THROTTLE_SECONDS:
                await asyncio.sleep(THROTTLE_SECONDS - elapsed)
            self._last_navigation = time.monotonic()

    async def fetch_html(self, url: str, wait_selector: str) -> str:
        """Открывает страницу и возвращает её HTML после появления нужного блока."""
        await self.start()
        await self._throttle()
        assert self._browser is not None
        context = await self._browser.new_context(
            user_agent=USER_AGENT,
            locale="ru-RU",
            timezone_id="Asia/Almaty",
            viewport={"width": 1280, "height": 900},
        )
        try:
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            try:
                await page.wait_for_selector(wait_selector, timeout=PAGE_TIMEOUT_MS // 2)
            except Exception:  # noqa: BLE001 — селектор мог не появиться, HTML всё равно нужен
                pass
            return await page.content()
        finally:
            await context.close()
