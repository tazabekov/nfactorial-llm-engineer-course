"""MCP-сервер поиска заведений в 2GIS.

Отдельный процесс, транспорт stdio. Агент подключается к нему как MCP-клиент и
вызывает инструмент через function calling — никаких прямых импортов из агента.

Запуск вручную:  .venv/bin/python mcp_servers/twogis/server.py
Офлайн-режим:    AVATAR_AGENT_OFFLINE=1 .venv/bin/python mcp_servers/twogis/server.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastmcp import FastMCP  # noqa: E402

from config import FIXTURES_DIR, OFFLINE  # noqa: E402
from mcp_servers.common.browser import BrowserPool, with_retry  # noqa: E402
from mcp_servers.common.cache import cache_get, cache_set  # noqa: E402
from mcp_servers.common.models import SearchResult  # noqa: E402
from mcp_servers.twogis.parser import build_search_url, parse_restaurants  # noqa: E402

mcp = FastMCP(
    "twogis",
    instructions="Поиск ресторанов, кафе и баров Алматы по данным 2GIS.",
)

POOL = BrowserPool()
CARD_WAIT_SELECTOR = "a[href*='/firm/']"
NAMESPACE = "twogis"
# Офлайн-фикстуры и живые данные кэшируются в разных неймспейсах: иначе
# результат, закэшированный в офлайн-режиме, мог бы «просочиться» в боевой
# ответ после переключения AVATAR_AGENT_OFFLINE обратно на 0 (и наоборот).
NAMESPACE_OFFLINE = "twogis-offline"

# 2ГИС перед реальным контентом показывает интерстишл «обновите браузер» —
# он пропадает, если заранее подставить эту куку (так делает и обычный клик
# по кнопке «Пропустить»). Без неё headless-браузер получает только заглушку
# на ~11 КБ вместо страницы поиска, и парсер не находит ни одной карточки.
# Та же кука используется в tools/capture_fixture.py, где приём был найден
# и проверен на живом сайте.
_TWOGIS_COOKIES = [{"name": "dg5_museum_accept", "value": "true", "domain": "2gis.kz", "path": "/"}]


def _offline_html() -> str:
    return (FIXTURES_DIR / "twogis_search.html").read_text(encoding="utf-8")


@mcp.tool
async def search_restaurants(
    query: str,
    location: str = "Алматы",
    limit: int = 8,
) -> SearchResult:
    """Ищет заведения в 2GIS по свободному запросу.

    Args:
        query: Что искать, например "итальянский ресторан" или "суши Достык".
        location: Город. Сейчас поддерживается только Алматы.
        limit: Сколько заведений вернуть, максимум 8.

    Returns:
        Список заведений с адресом, рейтингом, кухней и часами работы.
        При неудаче список пуст, а причина указана в поле error.
    """
    # Неймспейс выбираем в момент вызова (а не при импорте модуля), потому что
    # тесты подменяют server.OFFLINE через monkeypatch уже после импорта.
    namespace = NAMESPACE_OFFLINE if OFFLINE else NAMESPACE
    cache_key = f"{query}|{location}|{limit}"
    cached = cache_get(namespace, cache_key)
    if cached is not None:
        return SearchResult(**{**cached, "cached": True})

    try:
        if OFFLINE:
            html = _offline_html()
        else:
            url = build_search_url(query, "almaty")
            html = await with_retry(
                lambda: POOL.fetch_html(url, CARD_WAIT_SELECTOR, cookies=_TWOGIS_COOKIES)
            )
        restaurants = parse_restaurants(html, limit=limit)
    except Exception as error:  # noqa: BLE001 — наружу отдаём текст, а не трейсбек
        return SearchResult(results=[], error=f"Не удалось получить данные 2GIS: {error}")

    if not restaurants:
        return SearchResult(
            results=[],
            error="Страница загрузилась, но ни одной карточки распознать не удалось.",
        )

    result = SearchResult(results=restaurants)
    cache_set(namespace, cache_key, result.model_dump())
    return result


if __name__ == "__main__":
    mcp.run()
