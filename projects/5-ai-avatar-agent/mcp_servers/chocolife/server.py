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
# Источник — категория "Рестораны, кафе и бары", как и требует задание
# (https://chocolife.me/restorany-kafe-i-bary/), а не главная страница со
# случайной подборкой (караоке, spa, детские парки). Эмпирически (см. README)
# эта категория сейчас отдаёт всего 2 живых предложения — это честные данные,
# а не баг парсера: в Алматы сейчас мало активных акций на рестораны.
# Инструмент должен отвечать на вопрос "скидки на рестораны", а не выдавать
# больше результатов ценой их нерелевантности.
CATALOG_URL = "https://chocolife.me/restorany-kafe-i-bary/"
# Запасной источник на случай, если категория опустеет полностью (0 акций):
# главная страница с общей подборкой. Используется только как явный fallback
# (см. ниже), никогда молча.
FALLBACK_CATALOG_URL = "https://chocolife.me/"
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
    """Ищет действующие скидки и купоны на рестораны, кафе и бары.

    Args:
        category: Категория акций, по умолчанию рестораны, кафе и бары.
            Chocolife не поддерживает надёжную фильтрацию по узким
            подкатегориям внутри раздела (см. README), поэтому параметр
            принимается для единообразия интерфейса с 2GIS, а источником
            всегда служит раздел "Рестораны, кафе и бары" целиком.
        city: Город. Сейчас поддерживается только Алматы.
        limit: Сколько предложений вернуть, максимум 8.

    Returns:
        Список акций с ценой со скидкой, размером скидки и ссылкой на
        предложение. Поле source называет фактический источник: если
        ресторанная категория оказалась пуста, сервер один раз явно
        подстраховывается общей подборкой акций на главной, и это видно
        в source (а не подменяется молча под видом ресторанных скидок).
        При неудаче список пуст, а причина указана в поле error.
    """
    # Неймспейс выбираем в момент вызова, а не при импорте модуля: тесты
    # подменяют server.OFFLINE через monkeypatch уже после импорта.
    namespace = NAMESPACE_OFFLINE if OFFLINE else NAMESPACE
    cache_key = f"{category}|{city}|{limit}"
    cached = cache_get(namespace, cache_key)
    if cached is not None:
        return DealsResult(**{**cached, "cached": True})

    if OFFLINE:
        try:
            deals = parse_deals(_offline_html(), limit=limit)
        except Exception as error:  # noqa: BLE001 — наружу отдаём текст, а не трейсбек
            return DealsResult(results=[], error=f"Не удалось получить данные Chocolife: {error}")
        source = "chocolife.me/restorany-kafe-i-bary (офлайн-фикстура)"
    else:
        try:
            html = await with_retry(lambda: POOL.fetch_html(CATALOG_URL, CARD_WAIT_SELECTOR))
            deals = parse_deals(html, limit=limit)
        except Exception as error:  # noqa: BLE001 — наружу отдаём текст, а не трейсбек
            return DealsResult(results=[], error=f"Не удалось получить данные Chocolife: {error}")

        source = "chocolife.me/restorany-kafe-i-bary"
        if not deals:
            # Ресторанная категория сейчас регулярно отдаёт 0-2 живых акции
            # (см. README) — это честно, но если акций 0, лучше явно
            # подстраховаться общей подборкой, чем вернуть пустой ответ.
            # Fallback — не молчаливая подмена: source ниже прямо говорит,
            # что это уже не «рестораны», а общая подборка по городу.
            try:
                fallback_html = await with_retry(
                    lambda: POOL.fetch_html(FALLBACK_CATALOG_URL, CARD_WAIT_SELECTOR)
                )
                deals = parse_deals(fallback_html, limit=limit)
            except Exception:  # noqa: BLE001 — фолбэк лучше пропустить, чем упасть
                deals = []
            if deals:
                source = (
                    "chocolife.me (общая подборка акций по городу — "
                    "ресторанная категория сейчас пуста, среди результатов "
                    "могут быть не только рестораны)"
                )

    if not deals:
        return DealsResult(
            results=[],
            source=source,
            error="Каталог загрузился, но ни одной акции распознать не удалось.",
        )

    result = DealsResult(results=deals, source=source)
    cache_set(namespace, cache_key, result.model_dump())
    return result


if __name__ == "__main__":
    mcp.run()
