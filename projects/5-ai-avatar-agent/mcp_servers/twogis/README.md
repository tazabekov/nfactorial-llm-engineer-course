# MCP-сервер 2GIS

Ищет заведения Алматы на 2gis.kz и отдаёт их агенту через MCP.

**Инструмент:** `search_restaurants(query, location="Алматы", limit=8) -> SearchResult`

**Транспорт:** stdio. Сервер запускается агентом как дочерний процесс, вручную
запускать не нужно.

**Ручной запуск для отладки:**

    .venv/bin/python mcp_servers/twogis/server.py

**Офлайн-режим** (отдаёт сохранённую страницу вместо браузера, полезно для отладки
агента без сети):

    AVATAR_AGENT_OFFLINE=1 .venv/bin/python mcp_servers/twogis/server.py

**Зависимости:** Chromium ставится командой `.venv/bin/playwright install chromium`.

**Кэш:** результаты живут 24 часа в `cache/`. Удалите файлы `twogis-*.json`, чтобы
принудительно перечитать сайт.

**Обход интерстишла:** 2ГИС перед реальным контентом показывает headless-браузерам
заглушку «обновите браузер» (~11 КБ вместо страницы поиска). В боевом (не офлайн,
не кэш) пути сервер предустанавливает куку `dg5_museum_accept=true` для домена
`2gis.kz` перед навигацией — так же, как это делает `tools/capture_fixture.py`.
Без этой куки `search_restaurants` в реальном режиме всегда будет возвращать
пустой список.

**Если парсер сломался:** селекторы 2GIS обфусцированы и меняются. Снимите свежую
страницу и поправьте `parser.py`:

    .venv/bin/python tools/capture_fixture.py "https://2gis.kz/almaty/search/рестораны" twogis_search.html "a[href*='/firm/']"
