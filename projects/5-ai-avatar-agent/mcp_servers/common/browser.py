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
        self._start_lock = asyncio.Lock()

    async def start(self) -> None:
        if self._browser is not None:
            return
        # Отдельный лок именно под запуск: `_lock` держится throttle'ом на
        # время сна между навигациями, и если бы запуск браузера ждал на нём
        # же, старт процесса встал бы за троттлингом. Двойная проверка внутри
        # лока нужна, чтобы при параллельных вызовах Chromium запускался
        # только один раз, а не по разу на каждого дождавшегося.
        async with self._start_lock:
            if self._browser is not None:
                return
            self._playwright = await async_playwright().start()
            try:
                self._browser = await self._playwright.chromium.launch(headless=True)
            except Exception:
                # Частичный запуск: playwright поднялся, а браузер — нет.
                # Останавливаем драйвер, чтобы не оставлять осиротевший процесс.
                await self._playwright.stop()
                self._playwright = None
                raise

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

    async def fetch_html(
        self,
        url: str,
        wait_selector: str,
        cookies: list[dict[str, Any]] | None = None,
    ) -> str:
        """Открывает страницу и возвращает её HTML после появления нужного блока.

        `cookies` позволяет предустановить куки перед первой навигацией — например,
        чтобы сразу пропустить заглушку-интерстишл сайта («обновите браузер» у
        2ГИС), которая иначе перекрывает реальный контент на первой загрузке.
        """
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
            if cookies:
                await context.add_cookies(cookies)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            try:
                await page.wait_for_selector(wait_selector, timeout=PAGE_TIMEOUT_MS // 2)
            except Exception:  # noqa: BLE001 — селектор мог не появиться, HTML всё равно нужен
                pass
            return await page.content()
        finally:
            await context.close()
