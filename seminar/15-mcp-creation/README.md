# 15 — MCP Creation: AI-Agent with FastMCP

Цель: создать кастомные MCP-инструменты для LLM и подключить готовый Playwright MCP.

**Стек:** Python 3.12, `fastmcp`, `httpx`, Node.js (для Playwright MCP).

---

## Установка

```bash
# 1. Создать и активировать виртуальное окружение (uv)
uv venv --python 3.12 .venv
source .venv/bin/activate

# 2. Установить зависимости
uv pip install -r requirements.txt

# 3. Убедиться, что Node.js установлен (нужен для Playwright MCP)
node --version   # должно быть >= 18
```

---

## Файлы проекта

| Файл | Назначение |
|---|---|
| `weather_server.py` | FastMCP-сервер: инструменты погоды + заметок |
| `requirements.txt` | Python-зависимости |
| `.mcp.json` | Конфигурация MCP для Claude Code / Cursor |
| `my_notes/` | Папка для сохранённых заметок (создаётся автоматически) |

---

## Задание 1 — Инструмент «Умная погода»

**Инструмент:** `get_weather(city_name: str)`

Использует два бесплатных API без ключей:
1. [Open-Meteo Geocoding](https://geocoding-api.open-meteo.com) — название города → координаты
2. [Open-Meteo Forecast](https://api.open-meteo.com) — координаты → текущая погода

**Тестовый промпт:**
```
Какая сейчас погода в Алматы?
```

**Критерий приёмки:** агент вызывает `get_weather`, возвращает температуру °C, скорость ветра и описание погоды.

---

## Задание 2 — Инструмент «Афиша» (Playwright MCP)

Playwright MCP даёт ИИ браузер. Никакого кода писать не нужно — подключите готовый сервер.

### Подключение

**Claude Desktop** (`Settings → Developer → Edit Config`):
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

**Cursor** (`Settings → MCP → Add new MCP Server`):
```
Name:    playwright
Type:    command
Command: npx @playwright/mcp@latest
```

**VS Code (терминал):**
```bash
code --add-mcp '{"name":"playwright","command":"npx","args":["@playwright/mcp@latest"]}'
```

**Тестовый промпт:**
```
Открой сайт https://sxodim.com/almaty с помощью browser_navigate,
затем сделай browser_snapshot и найди 5 ближайших мероприятий в Алматы.
Верни мне список с названиями и датами.
```

**Критерий приёмки:** агент открывает браузер, читает страницу через snapshot и возвращает список реальных мероприятий.

---

## Задание 3 — Инструмент «Менеджер заметок»

**Инструменты** (все в `weather_server.py`):

| Инструмент | Что делает |
|---|---|
| `save_note(filename, content)` | Создаёт `my_notes/<filename>.txt` |
| `list_notes()` | Список всех `.txt` файлов в `my_notes/` |
| `read_note(filename)` | Читает содержимое заметки |

**Тестовые промпты:**
```
Сохрани рецепт пиццы в файл pizza
```
```
Какие у меня есть заметки?
```
```
Прочитай заметку pizza
```

**Критерий приёмки:** после первого запроса появляется `my_notes/pizza.txt` с рецептом.

---

## Задание 4 — Агент-Планировщик (финальный босс)

Убедитесь, что оба сервера подключены (`weather-agent` + `playwright`), затем отправьте промпт:

```
Я живу в Алматы. Спланируй мне сегодняшний вечер.
Сначала проверь погоду с помощью своего инструмента get_weather.
Если температура ниже 10 градусов, зайди на сайт https://sxodim.com/almaty
через Playwright и найди мероприятия в помещениях (театры, стендапы, концерты).
Если тепло — предложи прогулку на улице.
Составь красивое расписание на вечер по часам и сохрани его в файл
'my_perfect_evening' с помощью save_note.
```

**Критерий приёмки:** агент самостоятельно:
1. Вызывает `get_weather("Алматы")` → получает температуру
2. Если < 10°C → использует Playwright для поиска мероприятий на sxodim.com
3. Генерирует план вечера по часам
4. Вызывает `save_note("my_perfect_evening", ...)` → сохраняет файл
5. В папке `my_notes/` появляется `my_perfect_evening.txt`

---

## Бонус — Поиск в 2GIS (Playwright MCP)

```
Зайди на 2gis.kz/almaty, найди 5 ближайших кофеен через поиск на сайте.
Для каждой верни название и адрес.
```

Агент должен:
1. `browser_navigate` → `https://2gis.kz/almaty`
2. `browser_snapshot` → найти поле поиска
3. `browser_type` → "кофейни"
4. `browser_press_key` → Enter
5. `browser_wait_for` → загрузка результатов
6. `browser_snapshot` → вернуть 3–5 результатов с названиями и адресами

---

## Запуск сервера вручную (отладка)

```bash
source .venv/bin/activate
python weather_server.py
```

Сервер ждёт JSON-RPC команды через stdin/stdout — это нормально, клиент (Claude Desktop / Cursor) управляет им сам.

### Быстрая проверка инструментов без клиента

```bash
source .venv/bin/activate
python - <<'EOF'
from weather_server import get_weather, save_note, list_notes, read_note

# Task 1
print(get_weather("Алматы"))

# Task 3
print(save_note("test", "Тестовая заметка"))
print(list_notes())
print(read_note("test"))
EOF
```

---

## Конфигурация для Claude Code (`.mcp.json`)

Файл `.mcp.json` в этой папке уже настроен. Перезапустите Claude Code из этой директории — оба сервера подключатся автоматически.
