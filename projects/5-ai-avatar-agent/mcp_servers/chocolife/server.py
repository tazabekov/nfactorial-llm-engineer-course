"""MCP-сервер акций и скидок Chocolife.

Отдельный процесс, транспорт stdio. Агент подключается к нему как MCP-клиент и
вызывает инструмент через function calling — никаких прямых импортов из агента.

Запуск вручную:  .venv/bin/python mcp_servers/chocolife/server.py
Офлайн-режим:    AVATAR_AGENT_OFFLINE=1 .venv/bin/python mcp_servers/chocolife/server.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastmcp import FastMCP  # noqa: E402

from config import FIXTURES_DIR, OFFLINE  # noqa: E402
from mcp_servers.chocolife.parser import parse_deals  # noqa: E402
from mcp_servers.common.browser import BrowserPool, with_retry  # noqa: E402
from mcp_servers.common.cache import cache_get, cache_set  # noqa: E402
from mcp_servers.common.models import DealsResult  # noqa: E402

mcp = FastMCP(
    "chocolife",
    instructions="Скидки, акции и купоны на рестораны Алматы по данным Chocolife.",
)

POOL = BrowserPool()
# Важное наблюдение (эмпирически, см. README): узкая категория "Рестораны,
# кафе и бары" (/restorany-kafe-i-bary/) — и тем более более узкие подкатегории
# вроде /catalog/na-shashlyki/ — у Chocolife сейчас почти всегда отдают 0-2
# живых предложения, а фильтрация по подкатегориям на сайте фактически не
# работает: узкие разделы отдают ту же общую подборку "популярного сейчас",
# что и другие узкие разделы (проверено вручную — набор карточек совпадает
# для разных подкатегорий и включает караоке, spa, детские парки и т.д.).
# Единственная страница, где каталог гарантированно не пуст — главная
# ("текущие акции" по всему городу). Поэтому вживую ходим туда, а category/
# city в сигнатуре инструмента остаются для совместимости интерфейса с 2GIS
# и на будущее, если Chocolife заведёт рабочую фильтрацию по категориям.
CATALOG_URL = "https://chocolife.me/"
CARD_WAIT_SELECTOR = "cl-deal"
NAMESPACE = "chocolife"
# Как и в twogis/server.py: офлайн-фикстуры и живые данные кэшируются в
# разных неймспейсах, иначе фикстура, закэшированная под
# AVATAR_AGENT_OFFLINE=1, может 24 часа отдаваться как боевой результат.
NAMESPACE_OFFLINE = "chocolife-offline"


def _offline_html() -> str:
    return (FIXTURES_DIR / "chocolife_deals.html").read_text(encoding="utf-8")


@mcp.tool
async def search_deals(
    category: str = "рестораны",
    city: str = "Алматы",
    limit: int = 8,
) -> DealsResult:
    """Ищет действующие скидки и купоны на заведения.

    Args:
        category: Категория акций, по умолчанию рестораны, кафе и бары.
            Chocolife не поддерживает надёжную фильтрацию по узким
            категориям (см. комментарий у CATALOG_URL), поэтому параметр
            принимается для единообразия интерфейса, а фактически
            возвращаются текущие активные акции по городу.
        city: Город. Сейчас поддерживается только Алматы.
        limit: Сколько предложений вернуть, максимум 8.

    Returns:
        Список акций с ценой со скидкой, размером скидки и ссылкой на
        предложение. При неудаче список пуст, а причина указана в поле error.
    """
    # Неймспейс выбираем в момент вызова, а не при импорте модуля: тесты
    # подменяют server.OFFLINE через monkeypatch уже после импорта.
    namespace = NAMESPACE_OFFLINE if OFFLINE else NAMESPACE
    cache_key = f"{category}|{city}|{limit}"
    cached = cache_get(namespace, cache_key)
    if cached is not None:
        return DealsResult(**{**cached, "cached": True})

    try:
        html = _offline_html() if OFFLINE else await with_retry(
            lambda: POOL.fetch_html(CATALOG_URL, CARD_WAIT_SELECTOR)
        )
        deals = parse_deals(html, limit=limit)
    except Exception as error:  # noqa: BLE001 — наружу отдаём текст, а не трейсбек
        return DealsResult(results=[], error=f"Не удалось получить данные Chocolife: {error}")

    if not deals:
        return DealsResult(
            results=[],
            error="Каталог загрузился, но ни одной акции распознать не удалось.",
        )

    result = DealsResult(results=deals)
    cache_set(namespace, cache_key, result.model_dump())
    return result


if __name__ == "__main__":
    mcp.run()
