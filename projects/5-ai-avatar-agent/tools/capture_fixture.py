"""Снимает живую страницу и кладёт её HTML в tests/fixtures.

Запускать вручную, когда селекторы перестали работать:
    .venv/bin/python tools/capture_fixture.py <url> <имя_файла> <css-селектор>
"""

from __future__ import annotations

import asyncio
import sys

from config import FIXTURES_DIR
from mcp_servers.common.browser import BrowserPool

# 2ГИС перед реальным контентом показывает интерстишл «обновите браузер» —
# он пропадает, если заранее подставить эту куку (так делает и обычный клик
# по кнопке «Пропустить»). Без неё headless-браузер получает только заглушку
# на ~11 КБ вместо страницы поиска.
_TWOGIS_COOKIES = [{"name": "dg5_museum_accept", "value": "true", "domain": "2gis.kz", "path": "/"}]


async def main() -> None:
    if len(sys.argv) != 4:
        sys.exit("Использование: capture_fixture.py <url> <имя_файла> <селектор>")
    url, filename, selector = sys.argv[1:4]
    cookies = _TWOGIS_COOKIES if "2gis.kz" in url else None
    pool = BrowserPool()
    try:
        html = await pool.fetch_html(url, selector, cookies=cookies)
    finally:
        await pool.stop()
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    target = FIXTURES_DIR / filename
    target.write_text(html, encoding="utf-8")
    print(f"Сохранено: {target} ({len(html)} символов)")


if __name__ == "__main__":
    asyncio.run(main())
