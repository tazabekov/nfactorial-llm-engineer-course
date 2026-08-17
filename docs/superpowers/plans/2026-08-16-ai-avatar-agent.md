# AI Avatar Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Мультимодальный агент-проводник по ресторанам Алматы: текст/фото/голос на входе, данные из двух собственных MCP-серверов, ответ текстом плюс — по кнопке — аудио клонированным голосом и видео с говорящим аватаром.

**Architecture:** Три процесса. Gradio-приложение работает MCP-клиентом и поднимает два stdio MCP-сервера (`twogis`, `chocolife`) как дочерние процессы. Серверы парсят сайты через Playwright и ничего не знают про LLM; агент на `openai` SDK крутит цикл tool calling и ничего не знает про Playwright. Медиа-генерация (fal.ai) отделена от диалога и запускается явным действием пользователя.

**Tech Stack:** Python 3.12, `fastmcp` 3, `playwright`, `openai` 2.x, `gradio` 5, `fal-client`, `pydantic` 2, `pytest` + `pytest-asyncio`.

**Спека:** `docs/superpowers/specs/2026-08-16-ai-avatar-agent-design.md`
**Задание:** `projects/5-ai-avatar-agent/TASK.md`

## Global Constraints

- Рабочий каталог всего плана: `projects/5-ai-avatar-agent/`. Все пути в задачах даны относительно корня репозитория.
- Python 3.12, venv лежит в `projects/5-ai-avatar-agent/.venv`, создаётся через `python3.12 -m venv`.
- Ключи читаются из **корневого** `.env` репозитория: `OPENAI_API_KEY`, `FALAI_API_KEY`. `FALAI_API_KEY` копируется в `FAL_KEY` — именно его читает fal SDK.
- Модель агента по умолчанию: `gpt-5.4-mini` (проверено — доступна на аккаунте). Переопределяется переменной `AGENT_MODEL`.
- Модель аватара: `fal-ai/creatify/aurora` с `guidance_scale: 1`, `audio_guidance_scale: 2`, `resolution: "720p"`. Запасная: `fal-ai/kling-video/ai-avatar/v2/standard`.
- Модели fal: ASR `fal-ai/whisper`, клон голоса `fal-ai/minimax/voice-clone` (возвращает **`custom_voice_id`**), TTS `fal-ai/minimax/speech-02-hd` (голос передаётся вложенным **`voice_setting`**).
- **Ни один тест не ходит в сеть и не тратит деньги.** Всё внешнее — за интерфейсами, в тестах подменяется.
- Все платные вызовы fal (клон голоса, TTS, видео) в режиме `FAL_MOCK=1` возвращают заглушки. `FAL_MOCK=1` — значение по умолчанию в разработке; реальные вызовы включаются явно.
- Комментарии, докстринги и текст интерфейса — на русском, как и везде в репозитории.
- Коммиты в стиле репозитория: `feat(project-5): ...`, `test(project-5): ...`, `docs(project-5): ...`.
- Захардкоженных ответов про рестораны нет нигде. Пустой результат парсера → честное «не нашёл» в ответе агента.
- Тесты гермитичны по отношению к дисковому TTL-кэшу: `conftest.py` содержит автоприменяемую (`autouse`) фикстуру, которая на каждый тест подменяет `mcp_servers.common.cache.CACHE_DIR` на временный каталог. Прогон тестов никогда не читает и не пишет в боевой `projects/5-ai-avatar-agent/cache/`, и результат одного прогона не зависит от файлов, оставленных предыдущим. При добавлении новых MCP-серверов, которые кэшируют результаты, не заводите собственную ссылку на каталог кэша в обход `mcp_servers.common.cache` — иначе автофикстура перестанет их покрывать.

---

## File Structure

| Файл | Ответственность |
|---|---|
| `config.py` | Все константы: модели, лимиты, пути, флаги режимов. Проверка ключей. |
| `mcp_servers/common/models.py` | Pydantic-модели данных: `Restaurant`, `SearchResult`, `Deal`, `DealsResult`. |
| `mcp_servers/common/cache.py` | TTL-кэш на диске: `cache_get`, `cache_set`. |
| `mcp_servers/common/browser.py` | `BrowserPool` (один Chromium на процесс), троттлинг, ретраи, `fetch_html`. |
| `mcp_servers/twogis/parser.py` | Чистая функция `parse_restaurants(html) -> list[Restaurant]`. |
| `mcp_servers/twogis/server.py` | FastMCP-сервер: инструмент `search_restaurants`. |
| `mcp_servers/chocolife/parser.py` | Чистая функция `parse_deals(html) -> list[Deal]`. |
| `mcp_servers/chocolife/server.py` | FastMCP-сервер: инструмент `search_deals`. |
| `agent/mcp_bridge.py` | MCP → OpenAI tool specs, диспетчер вызовов, лог вызовов. |
| `agent/skills.py` | Локальный инструмент `analyze_restaurant_photo`. |
| `agent/llm.py` | Цикл tool calling, история, потолок итераций. |
| `agent/pipeline.py` | Оркестратор: ASR → агент → TTS → аватар. Единственное место, знающее весь порядок. |
| `voice/asr.py` | Распознавание речи через fal. |
| `voice/clone.py` | Клон голоса, кэш `custom_voice_id`. |
| `voice/tts.py` | Синтез речи клонированным голосом. |
| `avatar/generate.py` | Видео с аватаром (Aurora, фолбэк Kling). |
| `falcost.py` | Обёртка над fal: mock-режим, учёт расходов, ретраи. |
| `app.py` | Gradio Blocks: чат, входы, лог инструментов, кнопка медиа. |
| `tests/` | Тесты всех перечисленных модулей плюс HTML-фикстуры. |

---

### Task 1: Каркас проекта, конфигурация и проверка ключей

**Files:**
- Create: `projects/5-ai-avatar-agent/requirements.txt`
- Create: `projects/5-ai-avatar-agent/.env.example`
- Create: `projects/5-ai-avatar-agent/.gitignore`
- Create: `projects/5-ai-avatar-agent/config.py`
- Create: `projects/5-ai-avatar-agent/pytest.ini`
- Test: `projects/5-ai-avatar-agent/tests/test_config.py`

**Interfaces:**
- Consumes: ничего.
- Produces: `config.BASE_DIR: Path`, `config.CACHE_DIR: Path`, `config.ASSETS_PRIVATE_DIR: Path`, `config.OUTPUT_DIR: Path`, `config.FIXTURES_DIR: Path`, `config.AGENT_MODEL: str`, `config.MAX_TOOL_CALLS: int`, `config.MAX_HISTORY_MESSAGES: int`, `config.CACHE_TTL_SECONDS: int`, `config.THROTTLE_SECONDS: float`, `config.AVATAR_MODEL: str`, `config.AVATAR_FALLBACK_MODEL: str`, `config.ASR_MODEL: str`, `config.TTS_MODEL: str`, `config.VOICE_CLONE_MODEL: str`, `config.OFFLINE: bool`, `config.FAL_MOCK: bool`, `config.load_environment() -> None`, `config.require_keys(need_fal: bool) -> None`.

- [ ] **Step 1: Создать venv и поставить зависимости**

```bash
cd projects/5-ai-avatar-agent
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
```

Записать `projects/5-ai-avatar-agent/requirements.txt`:

```
fastmcp>=3.0
playwright>=1.49
openai>=2.0
gradio>=5.0
fal-client>=0.5
pydantic>=2.9
python-dotenv>=1.0
pytest>=8.0
pytest-asyncio>=0.24
```

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

Ожидаемо: установка проходит, `playwright install` скачивает Chromium.

- [ ] **Step 2: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_config.py`:

```python
import pytest

import config


def test_require_keys_reports_all_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FAL_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        config.require_keys(need_fal=True)
    message = str(exc.value)
    assert "OPENAI_API_KEY" in message
    assert "FAL_KEY" in message


def test_require_keys_passes_when_present(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("FAL_KEY", "y")
    config.require_keys(need_fal=True)


def test_require_keys_ignores_fal_when_not_needed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.delenv("FAL_KEY", raising=False)
    config.require_keys(need_fal=False)


def test_directories_are_absolute_and_exist():
    for path in (config.CACHE_DIR, config.OUTPUT_DIR, config.ASSETS_PRIVATE_DIR):
        assert path.is_absolute()
        assert path.exists()
```

- [ ] **Step 3: Запустить тест и убедиться, что он падает**

`projects/5-ai-avatar-agent/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`.

- [ ] **Step 4: Реализовать config.py**

`projects/5-ai-avatar-agent/config.py`:

```python
"""Конфигурация проекта: пути, модели, лимиты, режимы работы.

Все остальные модули берут константы отсюда и не читают os.environ напрямую,
кроме ключей API.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent

CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_PRIVATE_DIR = BASE_DIR / "assets-private"
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"

for _directory in (CACHE_DIR, OUTPUT_DIR, ASSETS_PRIVATE_DIR):
    _directory.mkdir(parents=True, exist_ok=True)

# --- Модели ---------------------------------------------------------------
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-5.4-mini")
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-5.4-mini")
ASR_MODEL = "fal-ai/whisper"
VOICE_CLONE_MODEL = "fal-ai/minimax/voice-clone"
TTS_MODEL = "fal-ai/minimax/speech-02-hd"
AVATAR_MODEL = os.getenv("AVATAR_MODEL", "fal-ai/creatify/aurora")
AVATAR_FALLBACK_MODEL = "fal-ai/kling-video/ai-avatar/v2/standard"

# --- Лимиты ---------------------------------------------------------------
MAX_TOOL_CALLS = 6           # потолок вызовов инструментов на один ход
MAX_HISTORY_MESSAGES = 20    # сколько сообщений диалога держим в памяти
CACHE_TTL_SECONDS = 24 * 60 * 60
THROTTLE_SECONDS = 2.0       # минимальная пауза между навигациями браузера
PAGE_TIMEOUT_MS = 30_000

# --- Режимы ---------------------------------------------------------------
# OFFLINE: MCP-серверы отдают фикстуры вместо браузера.
OFFLINE = os.getenv("AVATAR_AGENT_OFFLINE", "0") == "1"
# FAL_MOCK: платные вызовы fal возвращают заглушки. По умолчанию включён.
FAL_MOCK = os.getenv("FAL_MOCK", "1") == "1"


def load_environment() -> None:
    """Загружает ключи из корневого .env и настраивает FAL_KEY для fal SDK."""
    load_dotenv(REPO_ROOT / ".env")
    fal_key = os.getenv("FALAI_API_KEY")
    if fal_key and not os.getenv("FAL_KEY"):
        os.environ["FAL_KEY"] = fal_key


def require_keys(need_fal: bool) -> None:
    """Падает на старте со списком недостающих переменных окружения."""
    needed = ["OPENAI_API_KEY"]
    if need_fal:
        needed.append("FAL_KEY")
    missing = [name for name in needed if not os.getenv(name)]
    if missing:
        sys.exit(
            f"❌ Нет переменных окружения: {', '.join(missing)}. "
            f"Добавь их в .env в корне репозитория ({REPO_ROOT / '.env'})."
        )
```

- [ ] **Step 5: Запустить тесты и убедиться, что проходят**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_config.py -v`
Expected: PASS, 4 passed.

- [ ] **Step 6: Написать .env.example и .gitignore**

`projects/5-ai-avatar-agent/.env.example`:

```
# Ключи берутся из .env в корне репозитория. Этот файл — шаблон для проверяющего.
OPENAI_API_KEY=
FALAI_API_KEY=

# Необязательные переопределения
# AGENT_MODEL=gpt-5.4-mini
# AVATAR_MODEL=fal-ai/creatify/aurora
# AVATAR_AGENT_OFFLINE=0
# FAL_MOCK=1
```

`projects/5-ai-avatar-agent/.gitignore`:

```
.venv/
__pycache__/
.pytest_cache/
cache/
output/
assets-private/
*.mp3
*.mp4
!assets/demo.mp4
```

- [ ] **Step 7: Коммит**

```bash
git add projects/5-ai-avatar-agent/
git commit -m "feat(project-5): каркас проекта, конфигурация и проверка ключей"
```

---

### Task 2: Модели данных и TTL-кэш

**Files:**
- Create: `projects/5-ai-avatar-agent/mcp_servers/__init__.py`
- Create: `projects/5-ai-avatar-agent/mcp_servers/common/__init__.py`
- Create: `projects/5-ai-avatar-agent/mcp_servers/common/models.py`
- Create: `projects/5-ai-avatar-agent/mcp_servers/common/cache.py`
- Test: `projects/5-ai-avatar-agent/tests/test_cache.py`

**Interfaces:**
- Consumes: `config.CACHE_DIR`, `config.CACHE_TTL_SECONDS`.
- Produces: `models.Restaurant`, `models.SearchResult`, `models.Deal`, `models.DealsResult`; `cache.cache_get(namespace: str, key: str) -> dict | None`, `cache.cache_set(namespace: str, key: str, value: dict) -> None`.

- [ ] **Step 1: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_cache.py`:

```python
import time

from mcp_servers.common import cache


def test_set_then_get_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.cache_set("twogis", "суши центр", {"items": [1, 2]})
    assert cache.cache_get("twogis", "суши центр") == {"items": [1, 2]}


def test_miss_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    assert cache.cache_get("twogis", "ничего") is None


def test_expired_entry_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cache, "CACHE_TTL_SECONDS", 0)
    cache.cache_set("twogis", "суши", {"items": []})
    time.sleep(0.01)
    assert cache.cache_get("twogis", "суши") is None


def test_key_normalisation_ignores_case_and_spaces(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.cache_set("twogis", "  Суши  Центр ", {"items": [1]})
    assert cache.cache_get("twogis", "суши центр") == {"items": [1]}
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_cache.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_servers'`.

- [ ] **Step 3: Реализовать модели**

`projects/5-ai-avatar-agent/mcp_servers/__init__.py` и `projects/5-ai-avatar-agent/mcp_servers/common/__init__.py` — пустые файлы.

`projects/5-ai-avatar-agent/mcp_servers/common/models.py`:

```python
"""Модели данных, которые MCP-серверы возвращают агенту.

FastMCP выводит из них JSON-схему, поэтому описания полей видит LLM.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Restaurant(BaseModel):
    name: str = Field(description="Название заведения")
    address: str = Field(default="", description="Адрес")
    rating: float | None = Field(default=None, description="Рейтинг, если указан")
    price_range: str = Field(default="", description="Ценовая категория")
    cuisine: str = Field(default="", description="Кухня")
    working_hours: str = Field(default="", description="Часы работы")
    phone: str = Field(default="", description="Телефон")


class SearchResult(BaseModel):
    results: list[Restaurant] = Field(default_factory=list)
    source: str = Field(default="2gis.kz", description="Источник данных")
    cached: bool = Field(default=False, description="Ответ отдан из кэша")
    error: str = Field(default="", description="Причина, если данные получить не удалось")


class Deal(BaseModel):
    title: str = Field(description="Название акции")
    restaurant_name: str = Field(default="", description="Заведение")
    original_price: int | None = Field(default=None, description="Цена без скидки, тенге")
    discount_price: int | None = Field(default=None, description="Цена со скидкой, тенге")
    discount_percent: int | None = Field(default=None, description="Размер скидки, %")
    description: str = Field(default="", description="Описание предложения")
    url: str = Field(default="", description="Ссылка на предложение")


class DealsResult(BaseModel):
    results: list[Deal] = Field(default_factory=list)
    source: str = Field(default="chocolife.me")
    cached: bool = Field(default=False)
    error: str = Field(default="")
```

- [ ] **Step 4: Реализовать кэш**

`projects/5-ai-avatar-agent/mcp_servers/common/cache.py`:

```python
"""TTL-кэш результатов парсинга на диске.

Повторный запрос в пределах TTL не поднимает браузер — это и экономия времени,
и вежливость к сайтам, которые иначе начнут нас блокировать.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from config import CACHE_DIR, CACHE_TTL_SECONDS


def _normalise(key: str) -> str:
    return re.sub(r"\s+", " ", key).strip().lower()


def _path(namespace: str, key: str) -> Path:
    digest = hashlib.sha256(_normalise(key).encode("utf-8")).hexdigest()[:16]
    return Path(CACHE_DIR) / f"{namespace}-{digest}.json"


def cache_get(namespace: str, key: str) -> dict | None:
    """Возвращает значение из кэша или None, если его нет или оно протухло."""
    path = _path(namespace, key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if time.time() - payload.get("saved_at", 0) > CACHE_TTL_SECONDS:
        return None
    return payload.get("value")


def cache_set(namespace: str, key: str, value: dict) -> None:
    """Кладёт значение в кэш вместе с меткой времени."""
    path = _path(namespace, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"saved_at": time.time(), "key": _normalise(key), "value": value}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
```

- [ ] **Step 5: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_cache.py -v`
Expected: PASS, 4 passed.

- [ ] **Step 6: Коммит**

```bash
git add projects/5-ai-avatar-agent/mcp_servers projects/5-ai-avatar-agent/tests/test_cache.py
git commit -m "feat(project-5): модели данных и TTL-кэш для MCP-серверов"
```

---

### Task 3: Браузерный слой — пул, троттлинг, ретраи

**Files:**
- Create: `projects/5-ai-avatar-agent/mcp_servers/common/browser.py`
- Test: `projects/5-ai-avatar-agent/tests/test_browser.py`

**Interfaces:**
- Consumes: `config.THROTTLE_SECONDS`, `config.PAGE_TIMEOUT_MS`.
- Produces: `browser.BrowserPool` с `async start()`, `async fetch_html(url: str, wait_selector: str) -> str`, `async stop()`; `browser.with_retry(coro_factory, attempts: int = 2) -> Any`.

- [ ] **Step 1: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_browser.py`:

```python
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
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_browser.py -v`
Expected: FAIL — `ImportError: cannot import name 'browser'`.

- [ ] **Step 3: Реализовать браузерный слой**

`projects/5-ai-avatar-agent/mcp_servers/common/browser.py`:

```python
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
```

- [ ] **Step 4: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_browser.py -v`
Expected: PASS, 6 passed.

- [ ] **Step 5: Коммит**

```bash
git add projects/5-ai-avatar-agent/mcp_servers/common/browser.py projects/5-ai-avatar-agent/tests/test_browser.py
git commit -m "feat(project-5): браузерный пул с троттлингом и ретраями"
```

---

### Task 4: Парсер 2GIS и фикстура

**Files:**
- Create: `projects/5-ai-avatar-agent/tools/capture_fixture.py`
- Create: `projects/5-ai-avatar-agent/tests/fixtures/twogis_search.html` (снимается вживую)
- Create: `projects/5-ai-avatar-agent/mcp_servers/twogis/__init__.py`
- Create: `projects/5-ai-avatar-agent/mcp_servers/twogis/parser.py`
- Test: `projects/5-ai-avatar-agent/tests/test_twogis_parser.py`

**Interfaces:**
- Consumes: `models.Restaurant`, `browser.BrowserPool`.
- Produces: `parser.parse_restaurants(html: str, limit: int = 8) -> list[Restaurant]`, `parser.build_search_url(query: str, location: str) -> str`.

- [ ] **Step 1: Написать скрипт снятия фикстур**

`projects/5-ai-avatar-agent/tools/capture_fixture.py`:

```python
"""Снимает живую страницу и кладёт её HTML в tests/fixtures.

Запускать вручную, когда селекторы перестали работать:
    .venv/bin/python tools/capture_fixture.py <url> <имя_файла> <css-селектор>
"""

from __future__ import annotations

import asyncio
import sys

from config import FIXTURES_DIR
from mcp_servers.common.browser import BrowserPool


async def main() -> None:
    if len(sys.argv) != 4:
        sys.exit("Использование: capture_fixture.py <url> <имя_файла> <селектор>")
    url, filename, selector = sys.argv[1:4]
    pool = BrowserPool()
    try:
        html = await pool.fetch_html(url, selector)
    finally:
        await pool.stop()
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    target = FIXTURES_DIR / filename
    target.write_text(html, encoding="utf-8")
    print(f"Сохранено: {target} ({len(html)} символов)")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Снять живую фикстуру 2GIS**

```bash
cd projects/5-ai-avatar-agent
.venv/bin/python tools/capture_fixture.py \
  "https://2gis.kz/almaty/search/рестораны" twogis_search.html "div._1kf6gff"
```

Expected: файл `tests/fixtures/twogis_search.html` создан, размер больше 100 КБ.
Открыть его и найти реальные классы карточек — селекторы 2GIS обфусцированы и меняются, поэтому **следующий шаг пишется под то, что реально в файле**, а не под то, что здесь угадано.

- [ ] **Step 3: Написать падающий тест под снятую фикстуру**

`projects/5-ai-avatar-agent/tests/test_twogis_parser.py`:

```python
from config import FIXTURES_DIR
from mcp_servers.twogis import parser


def _html() -> str:
    return (FIXTURES_DIR / "twogis_search.html").read_text(encoding="utf-8")


def test_parses_at_least_three_restaurants():
    results = parser.parse_restaurants(_html())
    assert len(results) >= 3


def test_every_result_has_non_empty_name():
    for restaurant in parser.parse_restaurants(_html()):
        assert restaurant.name.strip()


def test_respects_limit():
    assert len(parser.parse_restaurants(_html(), limit=2)) == 2


def test_empty_html_gives_empty_list():
    assert parser.parse_restaurants("<html><body></body></html>") == []


def test_build_search_url_encodes_query():
    url = parser.build_search_url("суши бар", "almaty")
    assert url.startswith("https://2gis.kz/almaty/search/")
    assert " " not in url
```

- [ ] **Step 4: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_twogis_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_servers.twogis'`.

- [ ] **Step 5: Реализовать парсер**

`projects/5-ai-avatar-agent/mcp_servers/twogis/__init__.py` — пустой файл.

`projects/5-ai-avatar-agent/mcp_servers/twogis/parser.py`. Классы в примере ниже — заглушка структуры; **подставить реальные, найденные в фикстуре на шаге 2**. Логика поиска карточек намеренно не завязана на один класс: сначала пробуем прицельный селектор, при неудаче — эвристику по ссылкам на карточки фирм.

```python
"""Разбор страницы поиска 2GIS в список заведений.

Функция чистая: на входе HTML, на выходе модели. Это позволяет тестировать
парсер на сохранённой странице, не поднимая браузер.
"""

from __future__ import annotations

import re
from urllib.parse import quote

from bs4 import BeautifulSoup

from mcp_servers.common.models import Restaurant

CARD_SELECTOR = "div[class*='_1kf6gff']"
FIRM_LINK_PATTERN = re.compile(r"/firm/\d+")


def build_search_url(query: str, location: str = "almaty") -> str:
    """Собирает URL поиска: пробелы кодируются, иначе Playwright ругается."""
    return f"https://2gis.kz/{location}/search/{quote(query)}"


def _text(node, selector: str) -> str:
    found = node.select_one(selector)
    return found.get_text(" ", strip=True) if found else ""


def _rating(node) -> float | None:
    match = re.search(r"\b([0-5][.,]\d)\b", node.get_text(" ", strip=True))
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def parse_restaurants(html: str, limit: int = 8) -> list[Restaurant]:
    """Достаёт карточки заведений со страницы поиска."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(CARD_SELECTOR)
    if not cards:
        cards = [
            link.find_parent("div")
            for link in soup.find_all("a", href=FIRM_LINK_PATTERN)
            if link.find_parent("div") is not None
        ]

    restaurants: list[Restaurant] = []
    seen: set[str] = set()
    for card in cards:
        if card is None:
            continue
        name = _text(card, "span[class*='_1al0wlf']") or _text(card, "a span") or _text(card, "a")
        name = name.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        restaurants.append(
            Restaurant(
                name=name,
                address=_text(card, "span[class*='_er2xx9']"),
                rating=_rating(card),
                price_range=_text(card, "span[class*='_1p8iqzq']"),
                cuisine=_text(card, "span[class*='_oqoid']"),
                working_hours=_text(card, "span[class*='_49kxlr']"),
                phone=_text(card, "a[href^='tel:']"),
            )
        )
        if len(restaurants) >= limit:
            break
    return restaurants
```

Добавить `beautifulsoup4>=4.12` в `requirements.txt` и установить:

```bash
cd projects/5-ai-avatar-agent && .venv/bin/pip install "beautifulsoup4>=4.12"
```

- [ ] **Step 6: Прогнать тесты и починить селекторы под реальный HTML**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_twogis_parser.py -v`
Expected: PASS, 5 passed. Если падает — смотреть фикстуру и править селекторы в `parser.py`, тесты не трогать.

- [ ] **Step 7: Коммит**

```bash
git add projects/5-ai-avatar-agent/mcp_servers/twogis projects/5-ai-avatar-agent/tools \
        projects/5-ai-avatar-agent/tests/test_twogis_parser.py \
        projects/5-ai-avatar-agent/tests/fixtures/twogis_search.html \
        projects/5-ai-avatar-agent/requirements.txt
git commit -m "feat(project-5): парсер 2GIS на сохранённой фикстуре"
```

---

### Task 5: MCP-сервер 2GIS

**Files:**
- Create: `projects/5-ai-avatar-agent/mcp_servers/twogis/server.py`
- Create: `projects/5-ai-avatar-agent/mcp_servers/twogis/README.md`
- Test: `projects/5-ai-avatar-agent/tests/test_twogis_server.py`

**Interfaces:**
- Consumes: `parser.parse_restaurants`, `parser.build_search_url`, `cache.cache_get`, `cache.cache_set`, `browser.BrowserPool`, `config.OFFLINE`, `models.SearchResult`.
- Produces: модуль с объектом `mcp` (`FastMCP`) и инструментом `search_restaurants(query: str, location: str = "Алматы", limit: int = 8) -> SearchResult`.

- [ ] **Step 1: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_twogis_server.py`:

```python
from fastmcp import Client

from mcp_servers.twogis import server


async def test_tool_is_exposed_with_expected_name():
    async with Client(server.mcp) as client:
        names = [tool.name for tool in await client.list_tools()]
    assert "search_restaurants" in names


async def test_offline_mode_returns_results_from_fixture(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", True)
    async with Client(server.mcp) as client:
        result = await client.call_tool("search_restaurants", {"query": "рестораны-офлайн-тест"})
    assert result.data.error == ""
    assert len(result.data.results) >= 3


async def test_cache_prevents_second_fetch(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", False)
    calls = []

    async def fake_fetch(url, selector, cookies=None):
        calls.append(url)
        return (server.FIXTURES_DIR / "twogis_search.html").read_text(encoding="utf-8")

    monkeypatch.setattr(server.POOL, "fetch_html", fake_fetch)
    async with Client(server.mcp) as client:
        first = await client.call_tool("search_restaurants", {"query": "уник-запрос-кэш"})
        second = await client.call_tool("search_restaurants", {"query": "уник-запрос-кэш"})
    assert len(calls) == 1
    assert first.data.cached is False
    assert second.data.cached is True


async def test_parser_failure_yields_error_and_no_results(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", False)

    async def broken_fetch(url, selector, cookies=None):
        raise RuntimeError("сайт недоступен")

    monkeypatch.setattr(server.POOL, "fetch_html", broken_fetch)
    async with Client(server.mcp) as client:
        result = await client.call_tool("search_restaurants", {"query": "что-то новое"})
    assert result.data.results == []
    assert "недоступен" in result.data.error


async def test_offline_cache_does_not_leak_into_live_mode(monkeypatch):
    query = "уник-запрос-неймспейс"

    # Сначала кладём результат в кэш в офлайн-режиме.
    monkeypatch.setattr(server, "OFFLINE", True)
    async with Client(server.mcp) as client:
        offline_result = await client.call_tool("search_restaurants", {"query": query})
    assert offline_result.data.cached is False

    # Переключаемся в боевой режим и убеждаемся, что данные из офлайн-кэша
    # не отдаются: инструмент реально идёт за данными через fetch_html.
    monkeypatch.setattr(server, "OFFLINE", False)
    calls = []

    async def fake_fetch(url, selector, cookies=None):
        calls.append(url)
        return (server.FIXTURES_DIR / "twogis_search.html").read_text(encoding="utf-8")

    monkeypatch.setattr(server.POOL, "fetch_html", fake_fetch)
    async with Client(server.mcp) as client:
        live_result = await client.call_tool("search_restaurants", {"query": query})

    assert len(calls) == 1
    assert live_result.data.cached is False


async def test_parser_exception_is_caught_and_reported_as_error(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", True)

    def broken_parser(html, limit):
        raise ValueError("неожиданная разметка")

    monkeypatch.setattr(server, "parse_restaurants", broken_parser)
    async with Client(server.mcp) as client:
        result = await client.call_tool(
            "search_restaurants", {"query": "запрос-с-битым-парсером"}
        )
    assert result.data.results == []
    assert "неожиданная разметка" in result.data.error
```

> **Примечание (по факту реализации):** `result.data` в fastmcp 3.4.7 — это
> гидратированный pydantic-подобный объект (`Root`), а не `dict`, поэтому
> доступ к полям идёт через атрибуты (`result.data.error`), а не через
> `result.data["error"]`. Сигнатура `fetch_html` также получила `cookies`
> (см. Step 3) — фейковые фетчеры в тестах должны принимать этот параметр.
>
> **Примечание (ревью, раунд 1):** кэш офлайн- и боевого режимов должен жить
> в разных неймспейсах (`test_offline_cache_does_not_leak_into_live_mode`) —
> иначе фикстура, закэшированная под `AVATAR_AGENT_OFFLINE=1`, может 24 часа
> отдаваться как настоящий боевой результат после отключения офлайн-режима.
> `parse_restaurants` должен вызываться внутри `try`/`except`
> (`test_parser_exception_is_caught_and_reported_as_error`) — иначе исключение
> парсера долетает до LLM как сырая ошибка протокола MCP, а не как заполненное
> поле `error` из контракта инструмента.

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_twogis_server.py -v`
Expected: FAIL — `ImportError: cannot import name 'server'`.

- [ ] **Step 3: Реализовать сервер**

`projects/5-ai-avatar-agent/mcp_servers/twogis/server.py`:

```python
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
```

> **Примечание (ревью, раунд 1):** `parse_restaurants` вызывается внутри
> `try`/`except` вместе с получением html — так исключение парсера тоже
> превращается в заполненное поле `error`, а не улетает наружу как сырая
> ошибка протокола MCP.

- [ ] **Step 4: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_twogis_server.py -v`
Expected: PASS, 6 passed.

- [ ] **Step 5: Проверить сервер как настоящий процесс**

```bash
cd projects/5-ai-avatar-agent
AVATAR_AGENT_OFFLINE=1 .venv/bin/python -c "
import asyncio
from fastmcp import Client

async def main():
    async with Client('mcp_servers/twogis/server.py') as client:
        tools = await client.list_tools()
        print('инструменты:', [t.name for t in tools])
        result = await client.call_tool('search_restaurants', {'query': 'рестораны'})
        print('найдено:', len(result.data.results))

asyncio.run(main())
"
```

Expected: `инструменты: ['search_restaurants']` и ненулевое число найденных.

- [ ] **Step 6: Написать README сервера**

`projects/5-ai-avatar-agent/mcp_servers/twogis/README.md`:

```markdown
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

**Если парсер сломался:** селекторы 2GIS обфусцированы и меняются. Снимите свежую
страницу и поправьте `parser.py`:

    .venv/bin/python tools/capture_fixture.py "https://2gis.kz/almaty/search/рестораны" twogis_search.html "a[href*='/firm/']"
```

- [ ] **Step 7: Коммит**

```bash
git add projects/5-ai-avatar-agent/mcp_servers/twogis projects/5-ai-avatar-agent/tests/test_twogis_server.py
git commit -m "feat(project-5): MCP-сервер 2GIS с кэшем и офлайн-режимом"
```

---

### Task 6: Парсер и MCP-сервер Chocolife

**Files:**
- Create: `projects/5-ai-avatar-agent/mcp_servers/chocolife/__init__.py`
- Create: `projects/5-ai-avatar-agent/mcp_servers/chocolife/parser.py`
- Create: `projects/5-ai-avatar-agent/mcp_servers/chocolife/server.py`
- Create: `projects/5-ai-avatar-agent/mcp_servers/chocolife/README.md`
- Create: `projects/5-ai-avatar-agent/tests/fixtures/chocolife_deals.html` (снимается вживую)
- Test: `projects/5-ai-avatar-agent/tests/test_chocolife.py`

**Interfaces:**
- Consumes: `browser.BrowserPool`, `cache`, `models.Deal`, `models.DealsResult`, `config.OFFLINE`.
- Produces: `parser.parse_deals(html: str, limit: int = 8) -> list[Deal]`, модуль `server` с объектом `mcp` и инструментом `search_deals(category: str = "рестораны", city: str = "Алматы", limit: int = 8) -> DealsResult`.

- [ ] **Step 1: Снять фикстуру**

```bash
cd projects/5-ai-avatar-agent
.venv/bin/python tools/capture_fixture.py \
  "https://chocolife.me/restorany-kafe-i-bary/" chocolife_deals.html "a[href*='/deal']"
```

Expected: файл `tests/fixtures/chocolife_deals.html` создан. Открыть, найти реальную разметку карточек акций.

- [ ] **Step 2: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_chocolife.py`:

```python
from fastmcp import Client

from config import FIXTURES_DIR
from mcp_servers.chocolife import parser, server


def _html() -> str:
    return (FIXTURES_DIR / "chocolife_deals.html").read_text(encoding="utf-8")


def test_parses_at_least_three_deals():
    assert len(parser.parse_deals(_html())) >= 3


def test_every_deal_has_title():
    for deal in parser.parse_deals(_html()):
        assert deal.title.strip()


def test_prices_are_integers_or_none():
    for deal in parser.parse_deals(_html()):
        assert deal.discount_price is None or isinstance(deal.discount_price, int)


def test_empty_html_gives_empty_list():
    assert parser.parse_deals("<html></html>") == []


async def test_server_exposes_search_deals():
    async with Client(server.mcp) as client:
        names = [tool.name for tool in await client.list_tools()]
    assert "search_deals" in names


async def test_offline_mode_returns_deals(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", True)
    async with Client(server.mcp) as client:
        result = await client.call_tool("search_deals", {"category": "рестораны"})
    assert result.data["error"] == ""
    assert len(result.data["results"]) >= 3


async def test_fetch_failure_yields_error(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", False)

    async def broken_fetch(url, selector):
        raise RuntimeError("chocolife лежит")

    monkeypatch.setattr(server.POOL, "fetch_html", broken_fetch)
    async with Client(server.mcp) as client:
        result = await client.call_tool("search_deals", {"category": "уникальное"})
    assert result.data["results"] == []
    assert "лежит" in result.data["error"]
```

- [ ] **Step 3: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_chocolife.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_servers.chocolife'`.

- [ ] **Step 4: Реализовать парсер**

`projects/5-ai-avatar-agent/mcp_servers/chocolife/__init__.py` — пустой файл.

`projects/5-ai-avatar-agent/mcp_servers/chocolife/parser.py`. Селекторы подставить по снятой фикстуре:

```python
"""Разбор каталога акций Chocolife в список предложений."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from mcp_servers.common.models import Deal

CARD_SELECTOR = "div[class*='deal-card'], article[class*='deal']"
DEAL_LINK_PATTERN = re.compile(r"/deal|/discount")


def _price(text: str) -> int | None:
    """Достаёт первое число из строки вида '9 900 ₸'."""
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else None


def _text(node, selector: str) -> str:
    found = node.select_one(selector)
    return found.get_text(" ", strip=True) if found else ""


def parse_deals(html: str, limit: int = 8) -> list[Deal]:
    """Достаёт карточки акций со страницы каталога."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(CARD_SELECTOR)
    if not cards:
        cards = [
            link.find_parent("div")
            for link in soup.find_all("a", href=DEAL_LINK_PATTERN)
            if link.find_parent("div") is not None
        ]

    deals: list[Deal] = []
    seen: set[str] = set()
    for card in cards:
        if card is None:
            continue
        title = _text(card, "h3") or _text(card, "a[title]") or _text(card, "a")
        title = title.strip()
        if not title or title in seen:
            continue
        seen.add(title)

        link = card.select_one("a[href]")
        href = link["href"] if link else ""
        if href.startswith("/"):
            href = f"https://chocolife.me{href}"

        original = _price(_text(card, "[class*='old-price'], s, del"))
        discounted = _price(_text(card, "[class*='new-price'], [class*='price']"))
        percent_text = _text(card, "[class*='discount'], [class*='sale']")
        percent = _price(percent_text)

        deals.append(
            Deal(
                title=title,
                restaurant_name=_text(card, "[class*='merchant'], [class*='company']"),
                original_price=original,
                discount_price=discounted,
                discount_percent=percent if percent and percent <= 100 else None,
                description=_text(card, "[class*='description'], p"),
                url=href,
            )
        )
        if len(deals) >= limit:
            break
    return deals
```

- [ ] **Step 5: Реализовать сервер**

`projects/5-ai-avatar-agent/mcp_servers/chocolife/server.py`:

```python
"""MCP-сервер акций и скидок Chocolife.

Отдельный процесс, транспорт stdio.

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
CATALOG_URL = "https://chocolife.me/restorany-kafe-i-bary/"
CARD_WAIT_SELECTOR = "a[href*='deal']"
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
        city: Город. Сейчас поддерживается только Алматы.
        limit: Сколько предложений вернуть, максимум 8.

    Returns:
        Список акций с ценами до и после скидки и ссылкой на предложение.
        При неудаче список пуст, а причина указана в поле error.
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
    except Exception as error:  # noqa: BLE001
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
```

> **Примечание (ревью Task 5, раунд 1):** та же связка правок из
> `mcp_servers/twogis/server.py` применена и здесь — отдельный неймспейс
> кэша для офлайн/боевого режима и `parse_deals` внутри `try`/`except`,
> чтобы исключение парсера превращалось в заполненный `error`, а не
> улетало наружу как сырая ошибка протокола MCP. При написании теста для
> Step 2 добавить туда же аналоги
> `test_offline_cache_does_not_leak_into_live_mode` и
> `test_parser_exception_is_caught_and_reported_as_error` из
> `tests/test_twogis_server.py`.

- [ ] **Step 6: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_chocolife.py -v`
Expected: PASS, 9 passed (после исправления в раунде 1 ниже — было 7, добавлены
два теста на fallback). Если парсинг-тесты падают — править селекторы под
фикстуру.

> **Примечание (исправление, раунд 1, 2026-08-17):** первая реализация Task 6
> отклонилась от этого плана — `CATALOG_URL` указывал на главную страницу
> chocolife.me вместо категории `/restorany-kafe-i-bary/`, потому что
> категория отдаёт всего 2 живые акции, а не ≥3, под которые был написан
> тест. Это было исправлено обратно на план: `CATALOG_URL` снова —
> `/restorany-kafe-i-bary/`, фикстура переснята с этой страницы (2 живые
> акции подтверждены вручную — DOM-разметка `div.deal`, TransferState JSON
> в HTML не найден), порог теста снижен до `>= 2` с явным комментарием,
> почему это не регресс. Дополнительно добавлен явный fallback на главную
> страницу на случай, если категория отдаст 0 акций — но только с пометкой
> в `DealsResult.source`, чтобы агент/пользователь могли отличить
> ресторанные скидки от общей подборки. Подробности и живой прогон — в
> `.superpowers/sdd/task-6-report.md`, раздел "Fix round 1".

- [ ] **Step 7: Написать README сервера и закоммитить**

`projects/5-ai-avatar-agent/mcp_servers/chocolife/README.md`:

```markdown
# MCP-сервер Chocolife

Ищет скидки и купоны на рестораны Алматы в каталоге chocolife.me.

**Инструмент:** `search_deals(category="рестораны", city="Алматы", limit=8) -> DealsResult`

**Транспорт:** stdio, запускается агентом как дочерний процесс.

**Ручной запуск:**

    .venv/bin/python mcp_servers/chocolife/server.py

**Офлайн-режим:**

    AVATAR_AGENT_OFFLINE=1 .venv/bin/python mcp_servers/chocolife/server.py

**Кэш:** 24 часа, файлы `cache/chocolife-*.json`.

**Обновить фикстуру при поломке селекторов:**

    .venv/bin/python tools/capture_fixture.py "https://chocolife.me/restorany-kafe-i-bary/" chocolife_deals.html "cl-deal"
```

> **Примечание (раунд 1):** актуальный README (см. отчёт по исправлению)
> дополнительно фиксирует находку "категория и правда маленькая" (2 живые
> акции на момент съёмки) и документирует явный fallback на главную с
> пометкой в `source` — оба пункта в этом плане изначально не были описаны.

```bash
git add projects/5-ai-avatar-agent/mcp_servers/chocolife projects/5-ai-avatar-agent/tests/test_chocolife.py \
        projects/5-ai-avatar-agent/tests/fixtures/chocolife_deals.html
git commit -m "feat(project-5): MCP-сервер Chocolife с парсером акций"
```

---

### Task 7: Мост MCP → инструменты OpenAI

**Files:**
- Create: `projects/5-ai-avatar-agent/agent/__init__.py`
- Create: `projects/5-ai-avatar-agent/agent/mcp_bridge.py`
- Test: `projects/5-ai-avatar-agent/tests/test_mcp_bridge.py`

**Interfaces:**
- Consumes: `fastmcp.Client`.
- Produces: `mcp_bridge.McpToolset` с `async open()`, `async close()`, `specs() -> list[dict]`, `async call(name: str, arguments: dict) -> str`, `handles(name: str) -> bool`, атрибут `call_log: list[dict]`; функция `mcp_bridge.tool_spec_from_mcp(server_name: str, tool) -> dict`.

- [ ] **Step 1: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_mcp_bridge.py`:

```python
import json

from fastmcp import FastMCP
from pydantic import BaseModel

from agent import mcp_bridge

echo_server = FastMCP("echo")


class Answer(BaseModel):
    text: str


@echo_server.tool
def say(word: str) -> Answer:
    """Повторяет слово.

    Args:
        word: Что повторить.
    """
    return Answer(text=word * 2)


@echo_server.tool
def boom() -> Answer:
    """Всегда падает."""
    raise ValueError("инструмент сломался")


def test_tool_spec_has_openai_shape():
    class FakeTool:
        name = "say"
        description = "Повторяет слово."
        inputSchema = {"type": "object", "properties": {"word": {"type": "string"}}}

    spec = mcp_bridge.tool_spec_from_mcp("echo", FakeTool())
    assert spec["type"] == "function"
    assert spec["function"]["name"] == "echo__say"
    assert spec["function"]["parameters"]["properties"]["word"]["type"] == "string"


async def test_specs_are_prefixed_by_server_name():
    toolset = mcp_bridge.McpToolset({"echo": echo_server})
    await toolset.open()
    try:
        names = [spec["function"]["name"] for spec in toolset.specs()]
    finally:
        await toolset.close()
    assert "echo__say" in names


async def test_call_returns_json_payload():
    toolset = mcp_bridge.McpToolset({"echo": echo_server})
    await toolset.open()
    try:
        payload = await toolset.call("echo__say", {"word": "ку"})
    finally:
        await toolset.close()
    assert json.loads(payload)["text"] == "куку"


async def test_failing_tool_returns_error_payload_not_exception():
    toolset = mcp_bridge.McpToolset({"echo": echo_server})
    await toolset.open()
    try:
        payload = await toolset.call("echo__boom", {})
    finally:
        await toolset.close()
    assert "error" in json.loads(payload)


async def test_call_log_records_every_invocation():
    toolset = mcp_bridge.McpToolset({"echo": echo_server})
    await toolset.open()
    try:
        await toolset.call("echo__say", {"word": "а"})
    finally:
        await toolset.close()
    assert toolset.call_log[0]["name"] == "echo__say"
    assert toolset.call_log[0]["arguments"] == {"word": "а"}


def test_handles_only_known_prefixes():
    toolset = mcp_bridge.McpToolset({"echo": echo_server})
    assert toolset.handles("echo__say") is True
    assert toolset.handles("analyze_restaurant_photo") is False
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_mcp_bridge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent'`.

- [ ] **Step 3: Реализовать мост**

`projects/5-ai-avatar-agent/agent/__init__.py` — пустой файл.

`projects/5-ai-avatar-agent/agent/mcp_bridge.py`:

```python
"""Мост между MCP-серверами и function calling OpenAI.

Здесь и только здесь мы знаем, что часть инструментов живёт в чужих процессах.
Для LLM все инструменты выглядят одинаково.
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp import Client

SEPARATOR = "__"


def tool_spec_from_mcp(server_name: str, tool: Any) -> dict:
    """Превращает описание MCP-инструмента в спецификацию функции OpenAI."""
    # Имя поля со схемой отличается между версиями MCP SDK — проверяем оба.
    schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None) or {}
    return {
        "type": "function",
        "function": {
            "name": f"{server_name}{SEPARATOR}{tool.name}",
            "description": (tool.description or "").strip(),
            "parameters": schema or {"type": "object", "properties": {}},
        },
    }


class McpToolset:
    """Держит клиентов к нескольким MCP-серверам и разруливает вызовы по имени.

    Ключи словаря — короткие имена серверов, значения — либо путь к server.py
    (тогда сервер поднимается отдельным процессом), либо объект FastMCP
    (тогда соединение in-memory, это используется в тестах).
    """

    def __init__(self, servers: dict[str, Any]) -> None:
        self._servers = servers
        self._clients: dict[str, Client] = {}
        self._specs: list[dict] = []
        self.call_log: list[dict] = []

    async def open(self) -> None:
        """Поднимает серверы и собирает список их инструментов.

        При частичном сбое (если один из серверов не открыть или list_tools() упадёт)
        закрывает уже открытые клиенты, очищает внутреннее состояние и пробрасывает
        исключение. После этого можно снова вызвать open().
        """
        opened_clients: dict[str, Client] = {}
        try:
            for name, target in self._servers.items():
                client = Client(target)
                await client.__aenter__()
                opened_clients[name] = client
                self._clients[name] = client
                for tool in await client.list_tools():
                    self._specs.append(tool_spec_from_mcp(name, tool))
        except Exception:
            # Закрываем все уже открытые клиенты в best-effort режиме
            for name, client in opened_clients.items():
                try:
                    await client.__aexit__(None, None, None)
                except Exception:
                    # Игнорируем ошибки при закрытии, чтобы не скрыть исходное исключение
                    pass
            # Возвращаем состояние в то же, что было до попытки открыть
            self._clients.clear()
            self._specs.clear()
            raise

    async def close(self) -> None:
        for client in self._clients.values():
            await client.__aexit__(None, None, None)
        self._clients.clear()
        self._specs.clear()

    def specs(self) -> list[dict]:
        return list(self._specs)

    def handles(self, name: str) -> bool:
        server_name = name.split(SEPARATOR)[0]
        return server_name in self._servers

    async def call(self, name: str, arguments: dict) -> str:
        """Вызывает инструмент и возвращает JSON-строку для сообщения роли tool."""
        server_name, _, tool_name = name.partition(SEPARATOR)
        client = self._clients.get(server_name)
        entry: dict[str, Any] = {"name": name, "arguments": arguments}
        if client is None:
            entry["error"] = "сервер не подключён"
            self.call_log.append(entry)
            return json.dumps({"error": f"MCP-сервер {server_name} не подключён"}, ensure_ascii=False)

        try:
            result = await client.call_tool(tool_name, arguments, raise_on_error=False)
        except Exception as error:  # noqa: BLE001 — падение сервера не должно ронять диалог
            entry["error"] = str(error)
            self.call_log.append(entry)
            return json.dumps({"error": f"Вызов {name} не удался: {error}"}, ensure_ascii=False)

        if result.is_error:
            text = result.content[0].text if result.content else "неизвестная ошибка"
            entry["error"] = text
            self.call_log.append(entry)
            return json.dumps({"error": text}, ensure_ascii=False)

        # structured_content уже приходит от fastmcp обычным словарём (он
        # строится раньше, чем .data, и именно из него .data валидируется),
        # поэтому это самый надёжный источник. .data используем только как
        # запасной вариант и прогоняем через _to_jsonable, потому что это
        # не словарь, а объект с доступом по атрибутам.
        payload = result.structured_content
        if payload is None and result.data is not None:
            payload = _to_jsonable(result.data)
        if payload is None:
            payload = {"text": result.content[0].text if result.content else ""}

        if isinstance(payload, dict) and isinstance(payload.get("results"), list):
            entry["result_size"] = len(payload["results"])
        elif isinstance(payload, list):
            entry["result_size"] = len(payload)
        else:
            entry["result_size"] = 1 if payload else 0
        self.call_log.append(entry)
        return json.dumps(payload, ensure_ascii=False, default=str)
```

- [ ] **Step 4: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_mcp_bridge.py -v`
Expected: PASS, 6 passed.

- [ ] **Step 5: Коммит**

```bash
git add projects/5-ai-avatar-agent/agent projects/5-ai-avatar-agent/tests/test_mcp_bridge.py
git commit -m "feat(project-5): мост MCP-инструментов в function calling OpenAI"
```

---

### Task 8: Custom skill — ресторанный критик

**Files:**
- Create: `projects/5-ai-avatar-agent/agent/skills.py`
- Test: `projects/5-ai-avatar-agent/tests/test_skills.py`

**Interfaces:**
- Consumes: `config.VISION_MODEL`.
- Produces: `skills.RestaurantVerdict` (Pydantic), `skills.ANALYZE_TOOL_SPEC: dict`, `async skills.analyze_restaurant_photo(image_path: str, client) -> dict`, `skills.encode_image(path: str) -> str`.

- [ ] **Step 1: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_skills.py`:

```python
import base64

import pytest

from agent import skills


class FakeParsed:
    def __init__(self, verdict):
        self.parsed = verdict
        self.refusal = None


class FakeCompletions:
    def __init__(self, verdict):
        self._verdict = verdict
        self.last_kwargs = None

    async def parse(self, **kwargs):
        self.last_kwargs = kwargs

        class Result:
            choices = [type("C", (), {"message": FakeParsed(self._verdict)})()]

        return Result()


class FakeClient:
    def __init__(self, verdict):
        self.chat = type("Chat", (), {"completions": FakeCompletions(verdict)})()


def test_tool_spec_declares_image_path():
    spec = skills.ANALYZE_TOOL_SPEC
    assert spec["function"]["name"] == "analyze_restaurant_photo"
    assert "image_path" in spec["function"]["parameters"]["properties"]


def test_encode_image_returns_base64(tmp_path):
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0test")
    encoded = skills.encode_image(str(image))
    assert base64.b64decode(encoded) == b"\xff\xd8\xff\xe0test"


async def test_analyze_returns_dict_with_all_fields(tmp_path):
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0test")
    verdict = skills.RestaurantVerdict(
        level="mid-range", status="романтический", description="Уютно", confidence=0.8
    )
    client = FakeClient(verdict)
    result = await skills.analyze_restaurant_photo(str(image), client)
    assert result == {
        "level": "mid-range",
        "status": "романтический",
        "description": "Уютно",
        "confidence": 0.8,
    }


async def test_analyze_uses_detail_low(tmp_path):
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0test")
    verdict = skills.RestaurantVerdict(
        level="casual", status="семейный", description="ок", confidence=0.5
    )
    client = FakeClient(verdict)
    await skills.analyze_restaurant_photo(str(image), client)
    content = client.chat.completions.last_kwargs["messages"][0]["content"]
    image_part = [part for part in content if part["type"] == "image_url"][0]
    assert image_part["image_url"]["detail"] == "low"


async def test_missing_file_returns_error_dict():
    result = await skills.analyze_restaurant_photo("/нет/такого.jpg", FakeClient(None))
    assert "error" in result
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_skills.py -v`
Expected: FAIL — `ImportError: cannot import name 'skills'`.

- [ ] **Step 3: Реализовать skill**

`projects/5-ai-avatar-agent/agent/skills.py`:

```python
"""Собственный инструмент агента: оценка заведения по фотографии.

Агент вызывает его сам через function calling, когда пользователь прислал фото
интерьера, вывески или зала. Результат влияет на итоговую рекомендацию.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from config import VISION_MODEL

SYSTEM_PROMPT = (
    "Ты ресторанный критик. По фотографии заведения определи его уровень, "
    "тип и атмосферу. Опирайся на видимые признаки: сервировку, мебель, свет, "
    "посуду, оформление зала. Если фотография не про заведение общепита, "
    "поставь низкую уверенность и честно скажи об этом в описании."
)


class RestaurantVerdict(BaseModel):
    level: Literal["фастфуд", "casual", "mid-range", "fine dining"] = Field(
        description="Уровень заведения"
    )
    status: str = Field(description="Тип: семейный, романтический, бизнес-ланч, молодёжный")
    description: str = Field(description="Краткая характеристика атмосферы и аудитории")
    confidence: float = Field(ge=0.0, le=1.0, description="Уверенность модели от 0 до 1")


ANALYZE_TOOL_SPEC: dict = {
    "type": "function",
    "function": {
        "name": "analyze_restaurant_photo",
        "description": (
            "Оценивает заведение по фотографии интерьера, вывески или зала: "
            "уровень, тип и атмосферу. Вызывай этот инструмент всегда, когда "
            "пользователь прислал фотографию заведения."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Путь к файлу фотографии, полученной от пользователя",
                }
            },
            "required": ["image_path"],
        },
    },
}


def encode_image(path: str) -> str:
    """Кодирует картинку в base64 для передачи в vision-модель."""
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


async def analyze_restaurant_photo(image_path: str, client: Any) -> dict:
    """Отдаёт фото vision-модели и возвращает структурированный вердикт."""
    path = Path(image_path)
    if not path.exists():
        return {"error": f"Файл не найден: {image_path}"}

    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    data_url = f"data:{mime};base64,{encode_image(str(path))}"

    try:
        completion = await client.chat.completions.parse(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": SYSTEM_PROMPT},
                        # detail: low — картинка съедает заметно меньше токенов,
                        # для оценки уровня заведения этого разрешения достаточно.
                        {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
                    ],
                }
            ],
            response_format=RestaurantVerdict,
        )
    except Exception as error:  # noqa: BLE001
        return {"error": f"Не удалось проанализировать фото: {error}"}

    message = completion.choices[0].message
    if not getattr(message, "parsed", None):
        return {"error": getattr(message, "refusal", None) or "модель не вернула разбор"}
    return message.parsed.model_dump()
```

- [ ] **Step 4: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_skills.py -v`
Expected: PASS, 5 passed.

- [ ] **Step 5: Коммит**

```bash
git add projects/5-ai-avatar-agent/agent/skills.py projects/5-ai-avatar-agent/tests/test_skills.py
git commit -m "feat(project-5): custom skill — оценка заведения по фото"
```

---

### Task 9: Цикл агента

**Files:**
- Create: `projects/5-ai-avatar-agent/agent/llm.py`
- Test: `projects/5-ai-avatar-agent/tests/test_llm.py`

**Interfaces:**
- Consumes: `config.AGENT_MODEL`, `config.MAX_TOOL_CALLS`, `config.MAX_HISTORY_MESSAGES`, `mcp_bridge.McpToolset`, `skills.ANALYZE_TOOL_SPEC`, `skills.analyze_restaurant_photo`.
- Produces: `llm.SYSTEM_PROMPT: str`, `llm.trim_history(messages: list, limit: int) -> list`, `llm.build_user_message(text: str, image_path: str | None) -> dict`, `async llm.run_turn(client, toolset, history: list, user_message: dict) -> tuple[str, list, list]` — возвращает `(ответ, новая_история, лог_вызовов)`.

- [ ] **Step 1: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_llm.py`:

```python
import json

from agent import llm, skills


class FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.type = "function"
        self.function = type("F", (), {"name": name, "arguments": json.dumps(arguments)})()


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self):
        return {"role": "assistant", "content": self.content}


class FakeCompletions:
    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        message = self._script.pop(0)

        class Result:
            choices = [type("C", (), {"message": message})()]

        return Result()


class FakeClient:
    def __init__(self, script):
        self.completions = FakeCompletions(script)
        self.chat = type("Chat", (), {"completions": self.completions})()


class FakeToolset:
    def __init__(self):
        self.call_log = []
        self.calls = []

    def specs(self):
        return [{"type": "function", "function": {"name": "twogis__search_restaurants",
                                                  "description": "", "parameters": {}}}]

    def handles(self, name):
        return name.startswith("twogis__")

    async def call(self, name, arguments):
        self.calls.append((name, arguments))
        self.call_log.append({"name": name, "arguments": arguments, "result_size": 1})
        return json.dumps({"results": [{"name": "Бочка"}]}, ensure_ascii=False)


async def test_plain_answer_without_tools():
    client = FakeClient([FakeMessage(content="Привет")])
    answer, history, log = await llm.run_turn(
        client, FakeToolset(), [], llm.build_user_message("привет", None)
    )
    assert answer == "Привет"
    last = history[-1]
    content = last["content"] if isinstance(last, dict) else last.content
    assert content == "Привет"
    assert log == []


async def test_tool_call_is_executed_and_answered():
    toolset = FakeToolset()
    client = FakeClient([
        FakeMessage(tool_calls=[FakeToolCall("c1", "twogis__search_restaurants", {"query": "суши"})]),
        FakeMessage(content="Рекомендую Бочку"),
    ])
    answer, history, log = await llm.run_turn(
        client, toolset, [], llm.build_user_message("где поесть", None)
    )
    assert answer == "Рекомендую Бочку"
    assert toolset.calls == [("twogis__search_restaurants", {"query": "суши"})]
    assert log[0]["name"] == "twogis__search_restaurants"
    tool_messages = [m for m in history if isinstance(m, dict) and m.get("role") == "tool"]
    assert tool_messages[0]["tool_call_id"] == "c1"


async def test_every_call_in_batch_gets_a_reply():
    toolset = FakeToolset()
    batch = [
        FakeToolCall("a", "twogis__search_restaurants", {"query": "1"}),
        FakeToolCall("b", "twogis__search_restaurants", {"query": "2"}),
    ]
    client = FakeClient([FakeMessage(tool_calls=batch), FakeMessage(content="готово")])
    _, history, _ = await llm.run_turn(
        client, toolset, [], llm.build_user_message("вопрос", None)
    )
    ids = [m["tool_call_id"] for m in history if isinstance(m, dict) and m.get("role") == "tool"]
    assert ids == ["a", "b"]


async def test_iteration_cap_stops_the_loop(monkeypatch):
    monkeypatch.setattr(llm, "MAX_TOOL_CALLS", 2)
    toolset = FakeToolset()
    endless = [
        FakeMessage(tool_calls=[FakeToolCall(str(i), "twogis__search_restaurants", {"query": "x"})])
        for i in range(5)
    ]
    client = FakeClient(endless)
    answer, _, _ = await llm.run_turn(
        client, toolset, [], llm.build_user_message("вопрос", None)
    )
    assert answer == llm.CAP_REACHED_MESSAGE
    assert len(toolset.calls) == 2


async def test_malformed_arguments_do_not_crash():
    toolset = FakeToolset()
    bad = FakeToolCall("c1", "twogis__search_restaurants", {})
    bad.function.arguments = "{не json"
    client = FakeClient([FakeMessage(tool_calls=[bad]), FakeMessage(content="ладно")])
    answer, history, _ = await llm.run_turn(
        client, toolset, [], llm.build_user_message("вопрос", None)
    )
    assert answer == "ладно"
    tool_messages = [m for m in history if isinstance(m, dict) and m.get("role") == "tool"]
    assert "error" in tool_messages[0]["content"]


async def test_cap_reached_history_has_no_dangling_tool_calls(monkeypatch):
    """После срабатывания лимита в истории не должно оставаться
    assistant-сообщения с tool_calls без ответа на каждый call_id — иначе
    следующий run_turn, получив такую историю, будет отклонён API."""
    monkeypatch.setattr(llm, "MAX_TOOL_CALLS", 2)
    toolset = FakeToolset()
    endless = [
        FakeMessage(tool_calls=[FakeToolCall(str(i), "twogis__search_restaurants", {"query": "x"})])
        for i in range(5)
    ]
    client = FakeClient(endless)
    answer, history, _ = await llm.run_turn(
        client, toolset, [], llm.build_user_message("вопрос", None)
    )
    assert answer == llm.CAP_REACHED_MESSAGE

    answered_ids = {
        m["tool_call_id"] for m in history if isinstance(m, dict) and m.get("role") == "tool"
    }
    for message in history:
        tool_calls = message.get("tool_calls") if isinstance(message, dict) else message.tool_calls
        if not tool_calls:
            continue
        for call in tool_calls:
            call_id = call["id"] if isinstance(call, dict) else call.id
            assert call_id in answered_ids, (
                f"assistant tool_call {call_id} остался без ответа в истории"
            )


class FakeVisionCompletions:
    """Заглушка client.chat.completions.parse для vision-вызова skill'а."""

    def __init__(self, verdict):
        self._verdict = verdict

    async def parse(self, **kwargs):
        message = type("M", (), {"parsed": self._verdict, "refusal": None})()

        class Result:
            choices = [type("C", (), {"message": message})()]

        return Result()


class FakeClientWithVision(FakeClient):
    """FakeClient, который умеет и chat.completions.create (агентский цикл),
    и chat.completions.parse (внутри analyze_restaurant_photo)."""

    def __init__(self, script, verdict):
        super().__init__(script)
        self.completions.parse = FakeVisionCompletions(verdict).parse


async def test_local_skill_call_is_logged(tmp_path):
    """Вызов локального skill analyze_restaurant_photo должен попасть в
    возвращаемый call_log так же, как MCP-вызовы."""
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0test")
    verdict = skills.RestaurantVerdict(
        level="casual", status="семейный", description="ок", confidence=0.5
    )
    toolset = FakeToolset()
    client = FakeClientWithVision(
        [
            FakeMessage(
                tool_calls=[
                    FakeToolCall("c1", "analyze_restaurant_photo", {"image_path": str(image)})
                ]
            ),
            FakeMessage(content="Похоже на casual"),
        ],
        verdict,
    )
    _, _, log = await llm.run_turn(
        client, toolset, [], llm.build_user_message("что скажешь по фото", str(image))
    )
    assert any(entry["name"] == "analyze_restaurant_photo" for entry in log)


def test_trim_history_keeps_last_messages():
    messages = [{"role": "user", "content": str(i)} for i in range(30)]
    trimmed = llm.trim_history(messages, limit=10)
    assert len(trimmed) == 10
    assert trimmed[-1]["content"] == "29"


def _assert_pairing_invariant(history):
    """Для каждого assistant-сообщения с tool_calls в history все его
    call_id должны быть отвечены, и у каждого tool-сообщения должен быть
    его assistant-родитель в history."""
    answered_ids = {
        m["tool_call_id"] for m in history if isinstance(m, dict) and m.get("role") == "tool"
    }
    parent_ids = set()
    for message in history:
        tool_calls = message.get("tool_calls") if isinstance(message, dict) else getattr(message, "tool_calls", None)
        if not tool_calls:
            continue
        for call in tool_calls:
            call_id = call["id"] if isinstance(call, dict) else call.id
            parent_ids.add(call_id)
            assert call_id in answered_ids, f"tool_call {call_id} остался без ответа"
    for message in history:
        if isinstance(message, dict) and message.get("role") == "tool":
            assert message["tool_call_id"] in parent_ids, (
                f"tool-сообщение {message['tool_call_id']} осиротело: assistant-родитель обрезан"
            )


def test_trim_history_never_severs_tool_call_pairing():
    """Дефект 1 (round 2): если обрезка по лимиту падает ровно между
    assistant-сообщением с tool_calls и его ответами, история после
    trim_history не должна начинаться с осиротевших tool-сообщений. Против
    старого блочного среза messages[-limit:] этот тест падает: первым
    сообщением среза оказывается tool-ответ "a", чей assistant-родитель
    отрезан."""
    messages = [{"role": "user", "content": f"filler-{i}"} for i in range(5)]
    messages.append(
        FakeMessage(
            tool_calls=[
                FakeToolCall("a", "twogis__search_restaurants", {"query": "1"}),
                FakeToolCall("b", "twogis__search_restaurants", {"query": "2"}),
            ]
        )
    )
    messages.append({"role": "tool", "tool_call_id": "a", "content": "{}"})
    messages.append({"role": "tool", "tool_call_id": "b", "content": "{}"})
    messages += [{"role": "user", "content": f"tail-{i}"} for i in range(12)]
    assert len(messages) == 20

    # limit=14 => блочный срез начинается ровно с tool-сообщения "a"
    # (индекс 6), отрезая его assistant-родителя на индексе 5.
    trimmed = llm.trim_history(messages, limit=14)

    blind_slice = messages[-14:]
    assert isinstance(blind_slice[0], dict) and blind_slice[0].get("role") == "tool"

    _assert_pairing_invariant(trimmed)
    assert trimmed[0] != blind_slice[0] or trimmed[0].get("role") != "tool"


def test_trim_history_drops_leading_orphaned_tool_message():
    """Осиротевшее tool-сообщение (родитель обрезан) никогда не должно
    оказаться первым в результате trim_history."""
    messages = [{"role": "tool", "tool_call_id": "orphan", "content": "{}"}]
    messages += [{"role": "user", "content": str(i)} for i in range(9)]
    trimmed = llm.trim_history(messages, limit=10)
    assert all(
        not (isinstance(m, dict) and m.get("role") == "tool" and m.get("tool_call_id") == "orphan")
        for m in trimmed
    )


def test_build_user_message_with_image(tmp_path):
    image = tmp_path / "p.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0")
    message = llm.build_user_message("что это", str(image))
    kinds = [part["type"] for part in message["content"]]
    assert "image_url" in kinds


def test_build_user_message_missing_image_degrades_to_text():
    """Дефект 2 (round 2): пропавший файл фото не должен ронять
    build_user_message — сообщение должно деградировать до текстового с
    честной припиской, аналогично analyze_restaurant_photo в skills.py."""
    message = llm.build_user_message("что это", "/no/such/file.jpg")
    assert isinstance(message["content"], str)
    assert "что это" in message["content"]
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_llm.py -v`
Expected: FAIL — `ImportError: cannot import name 'llm'`.

- [ ] **Step 3: Реализовать цикл**

`projects/5-ai-avatar-agent/agent/llm.py`:

```python
"""Цикл tool calling: сердце агента.

Не знает ни про Gradio, ни про fal, ни про Playwright — только про сообщения,
инструменты и модель.
"""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

from config import AGENT_MODEL, MAX_HISTORY_MESSAGES, MAX_TOOL_CALLS
from agent.skills import ANALYZE_TOOL_SPEC, analyze_restaurant_photo, encode_image

SYSTEM_PROMPT = """Ты — персональный проводник по ресторанам Алматы.

Правила:
1. Отвечай только на основе данных, полученных из инструментов. Ничего не выдумывай:
   ни названий, ни адресов, ни цен.
2. Если инструмент вернул пустой список или поле error — честно скажи, что данные
   получить не удалось, и предложи уточнить запрос.
3. Найдя подходящие заведения в 2GIS, проверь по Chocolife, нет ли на них скидок.
4. Если пользователь прислал фотографию заведения — вызови analyze_restaurant_photo
   и учти вердикт в рекомендации.
5. Ответ должен звучать 15–30 секунд вслух: три-четыре предложения, максимум три
   заведения, с адресом и одной причиной выбора для каждого. Без списков и markdown —
   текст пойдёт в озвучку.
6. Помни, о чём шла речь раньше в диалоге, и не переспрашивай уже сказанное."""

CAP_REACHED_MESSAGE = (
    "Я исчерпал лимит обращений к источникам и отвечаю по тому, что успел собрать."
)


def _msg_role(message: Any) -> str:
    """Роль сообщения независимо от формы: dict (user/tool) или raw SDK-объект
    (assistant — сырые ответы модели в истории всегда только ассистентские)."""
    if isinstance(message, dict):
        return message.get("role", "")
    return "assistant"


def _msg_tool_calls(message: Any) -> list:
    """tool_calls сообщения независимо от формы, либо пустой список."""
    if isinstance(message, dict):
        return message.get("tool_calls") or []
    return getattr(message, "tool_calls", None) or []


def _call_id(call: Any) -> str:
    return call["id"] if isinstance(call, dict) else call.id


def _msg_tool_call_id(message: Any) -> str | None:
    if isinstance(message, dict):
        return message.get("tool_call_id")
    return getattr(message, "tool_call_id", None)


def trim_history(messages: list, limit: int = MAX_HISTORY_MESSAGES) -> list:
    """Оставляет последние сообщения, но не в ущерб парности tool-вызовов.

    Инвариант, который обязан выполняться на выходе: для каждого assistant-
    сообщения с tool_calls в результате присутствуют tool-сообщения на ВСЕ его
    call_id, и у каждого tool-сообщения в результате есть его assistant-
    родитель. Простая обрезка messages[-limit:] ничего не знает про роли и
    может отрезать историю ровно между assistant-сообщением с tool_calls и
    его ответами (или оставить только хвост таких ответов) — тогда в начале
    среза окажется "осиротевшее" tool-сообщение или assistant с недоответившим
    tool_calls, и следующий вызов API с такой историей будет отклонён.

    Поэтому после обрезки по количеству мы проходим от начала среза и убираем
    подряд: (а) tool-сообщения, чей assistant-родитель уже не попал в срез,
    и (б) assistant-сообщения с tool_calls, не все call_id которых нашли
    ответ внутри среза (вместе с теми их ответами, что всё-таки попали —
    иначе они сами станут осиротевшими). Хвост среза трогать не нужно: он
    всегда заканчивается на завершённом обмене (см. run_turn).
    """
    sliced = messages[-limit:] if len(messages) > limit else list(messages)

    result = list(sliced)
    changed = True
    while changed and result:
        changed = False
        head = result[0]
        if _msg_role(head) == "tool":
            result.pop(0)
            changed = True
            continue
        calls = _msg_tool_calls(head)
        if calls:
            ids = {_call_id(c) for c in calls}
            present_ids = {
                _msg_tool_call_id(m) for m in result if _msg_role(m) == "tool"
            }
            if not ids.issubset(present_ids):
                result.pop(0)
                result = [
                    m
                    for m in result
                    if not (_msg_role(m) == "tool" and _msg_tool_call_id(m) in ids)
                ]
                changed = True
    return result


def build_user_message(text: str, image_path: str | None) -> dict:
    """Собирает сообщение пользователя, при наличии фото — мультимодальное.

    Если файл фото пропал или не читается, не роняем ход исключением (как и
    analyze_restaurant_photo в agent/skills.py) — деградируем до текстового
    сообщения с честной припиской, что фото прочитать не удалось.
    """
    if not image_path:
        return {"role": "user", "content": text}
    try:
        mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        data_url = f"data:{mime};base64,{encode_image(image_path)}"
    except OSError as error:
        return {
            "role": "user",
            "content": f"{text}\n\n(Не удалось прочитать присланное фото: {error})",
        }
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": f"{text}\n\n(Путь к присланному фото: {image_path})"},
            {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
        ],
    }


async def _dispatch(
    name: str, arguments: dict, toolset: Any, client: Any, call_log: list
) -> str:
    """Направляет вызов в MCP или в локальный skill.

    MCP-вызовы toolset регистрирует в собственном call_log сам — этот кусок
    журнала run_turn считывает отдельно (см. срез toolset.call_log ниже).
    Локальные skill-вызовы toolset не видит вообще, поэтому здесь они
    записываются в call_log, принадлежащий run_turn — в той же форме
    (name, arguments, result_size/error), чтобы UI показывал их наравне с
    MCP-вызовами и не выглядело так, будто инструмент не вызывался.
    """
    if toolset.handles(name):
        return await toolset.call(name, arguments)
    if name == "analyze_restaurant_photo":
        result = await analyze_restaurant_photo(arguments.get("image_path", ""), client)
        payload = json.dumps(result, ensure_ascii=False)
        if isinstance(result, dict) and "error" in result:
            call_log.append({"name": name, "arguments": arguments, "error": result["error"]})
        else:
            call_log.append(
                {"name": name, "arguments": arguments, "result_size": len(payload)}
            )
        return payload
    return json.dumps({"error": f"Неизвестный инструмент: {name}"}, ensure_ascii=False)


async def run_turn(
    client: Any,
    toolset: Any,
    history: list,
    user_message: dict,
) -> tuple[str, list, list]:
    """Прогоняет один ход диалога.

    Возвращает текст ответа, обновлённую историю и лог вызовов инструментов
    за этот ход.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + trim_history(history)
    messages.append(user_message)

    tools = toolset.specs() + [ANALYZE_TOOL_SPEC]
    log_start = len(getattr(toolset, "call_log", []))
    local_log: list = []
    calls_made = 0
    answer = ""

    while True:
        completion = await client.chat.completions.create(
            model=AGENT_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        message = completion.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            answer = message.content or ""
            break

        if calls_made >= MAX_TOOL_CALLS:
            # Лимит достигнут: assistant-сообщение с tool_calls уже добавлено в
            # messages, а ни один из этих вызовов ещё не обработан. Оставить их
            # без ответа нельзя — OpenAI-совместимое API требует ровно одно
            # tool-сообщение на каждый tool_call, иначе следующий run_turn,
            # получив эту историю на вход, немедленно упадёт с ошибкой формата.
            # Вырезать assistant-сообщение из истории было бы проще, но тогда
            # стёрлось бы честное свидетельство того, что модель пыталась звать
            # инструменты — а UI и следующий ход должны видеть, что попытка
            # была, просто бюджет закончился. Поэтому отвечаем каждому
            # незакрытому вызову короткой tool-заглушкой и только потом рвём цикл.
            for call in message.tool_calls:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {"error": "лимит вызовов инструментов исчерпан"},
                            ensure_ascii=False,
                        ),
                    }
                )
            answer = CAP_REACHED_MESSAGE
            break

        for call in message.tool_calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                payload = json.dumps(
                    {"error": "аргументы пришли не в формате JSON"}, ensure_ascii=False
                )
            else:
                payload = await _dispatch(call.function.name, arguments, toolset, client, local_log)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": payload}
            )
            calls_made += 1

    new_history = trim_history([m for m in messages if _is_history_message(m)])
    # Лог за этот ход = MCP-вызовы (их регистрирует toolset.call_log — берём
    # только то, что появилось начиная с log_start) + локальные skill-вызовы
    # (analyze_restaurant_photo), которые toolset не видит и не пишет к себе.
    # toolset.call_log при этом не трогаем — это его собственный список.
    call_log = list(getattr(toolset, "call_log", [])[log_start:]) + local_log
    return answer, new_history, call_log


def _is_history_message(message: Any) -> bool:
    """Системный промпт в историю не кладём — он добавляется на каждом ходу."""
    if isinstance(message, dict):
        return message.get("role") != "system"
    return True
```

- [ ] **Step 4: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_llm.py -v`
Expected: PASS, 12 passed.

- [ ] **Step 5: Коммит**

```bash
git add projects/5-ai-avatar-agent/agent/llm.py projects/5-ai-avatar-agent/tests/test_llm.py
git commit -m "feat(project-5): цикл tool calling с памятью и потолком вызовов"
```

---

### Task 10: Обёртка над fal — mock-режим, ретраи, учёт расходов

**Files:**
- Create: `projects/5-ai-avatar-agent/falcost.py`
- Test: `projects/5-ai-avatar-agent/tests/test_falcost.py`

**Interfaces:**
- Consumes: `config.FAL_MOCK`, `config.CACHE_DIR`, `config.OUTPUT_DIR`.
- Produces: `falcost.PRICES: dict[str, float]`, `async falcost.run_model(model: str, arguments: dict, mock_result: dict, attempts: int = 2) -> dict`, `async falcost.upload(path: str) -> str`, `falcost.record_cost(model: str) -> None`, `falcost.total_spent() -> float`, `falcost.download(url: str, target: Path) -> Path`.

- [ ] **Step 1: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_falcost.py`:

```python
import json

import falcost


async def test_mock_mode_returns_mock_and_skips_network(monkeypatch, tmp_path):
    monkeypatch.setattr(falcost, "FAL_MOCK", True)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")

    async def explode(*args, **kwargs):
        raise AssertionError("в mock-режиме сеть трогать нельзя")

    monkeypatch.setattr(falcost.fal_client, "subscribe_async", explode)
    result = await falcost.run_model("fal-ai/whisper", {"a": 1}, {"text": "заглушка"})
    assert result == {"text": "заглушка"}


async def test_real_mode_calls_fal_and_records_cost(monkeypatch, tmp_path):
    monkeypatch.setattr(falcost, "FAL_MOCK", False)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")
    seen = {}

    async def fake_subscribe(model, arguments=None, **kwargs):
        seen["model"] = model
        seen["arguments"] = arguments
        return {"ok": True}

    monkeypatch.setattr(falcost.fal_client, "subscribe_async", fake_subscribe)
    result = await falcost.run_model("fal-ai/whisper", {"a": 1}, {"text": "заглушка"})
    assert result == {"ok": True}
    assert seen["model"] == "fal-ai/whisper"
    entries = [json.loads(line) for line in (tmp_path / "costs.jsonl").read_text().splitlines()]
    assert entries[0]["model"] == "fal-ai/whisper"


async def test_failure_retries_then_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(falcost, "FAL_MOCK", False)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")
    attempts = []

    async def flaky(model, arguments=None, **kwargs):
        attempts.append(1)
        raise RuntimeError("fal недоступен")

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(falcost.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(falcost.fal_client, "subscribe_async", flaky)
    try:
        await falcost.run_model("fal-ai/whisper", {}, {"text": "x"})
    except RuntimeError:
        pass
    else:
        raise AssertionError("должно было упасть")
    assert len(attempts) == 2


async def test_attempts_one_makes_single_attempt_then_raises(monkeypatch, tmp_path):
    """Дорогие модели (видео) не должны платить за штатный retry."""
    monkeypatch.setattr(falcost, "FAL_MOCK", False)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")
    attempts = []

    async def flaky(model, arguments=None, **kwargs):
        attempts.append(1)
        raise RuntimeError("fal недоступен")

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(falcost.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(falcost.fal_client, "subscribe_async", flaky)
    try:
        await falcost.run_model("fal-ai/creatify/aurora", {}, {"video": "x"}, attempts=1)
    except RuntimeError:
        pass
    else:
        raise AssertionError("должно было упасть")
    assert len(attempts) == 1


async def test_attempts_default_still_makes_two(monkeypatch, tmp_path):
    monkeypatch.setattr(falcost, "FAL_MOCK", False)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")
    attempts = []

    async def flaky(model, arguments=None, **kwargs):
        attempts.append(1)
        raise RuntimeError("fal недоступен")

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(falcost.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(falcost.fal_client, "subscribe_async", flaky)
    try:
        await falcost.run_model("fal-ai/whisper", {}, {"text": "x"})
    except RuntimeError:
        pass
    else:
        raise AssertionError("должно было упасть")
    assert len(attempts) == 2


async def test_attempts_zero_or_negative_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(falcost, "FAL_MOCK", False)
    monkeypatch.setattr(falcost, "COST_LOG", tmp_path / "costs.jsonl")

    async def explode(*args, **kwargs):
        raise AssertionError("attempts<1 должен быть отклонён раньше сетевого вызова")

    monkeypatch.setattr(falcost.fal_client, "subscribe_async", explode)

    for bad_value in (0, -1):
        try:
            await falcost.run_model("fal-ai/whisper", {}, {"text": "x"}, attempts=bad_value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"attempts={bad_value} должен был быть отклонён")


def test_total_spent_sums_log(monkeypatch, tmp_path):
    log = tmp_path / "costs.jsonl"
    monkeypatch.setattr(falcost, "COST_LOG", log)
    falcost.record_cost("fal-ai/minimax/voice-clone")
    falcost.record_cost("fal-ai/minimax/voice-clone")
    assert falcost.total_spent() == falcost.PRICES["fal-ai/minimax/voice-clone"] * 2


def test_download_in_mock_mode_never_hits_network_even_with_realistic_url(monkeypatch, tmp_path):
    """download() должен смотреть на FAL_MOCK, а не угадывать mock по виду URL.

    Правдоподобный fal-URL (как в реальном ответе fal.media) не должен
    приводить к сетевому запросу, если включён mock-режим.
    """
    monkeypatch.setattr(falcost, "FAL_MOCK", True)

    def explode(*args, **kwargs):
        raise AssertionError("в mock-режиме download не должен трогать сеть")

    monkeypatch.setattr(falcost.urllib.request, "urlretrieve", explode)
    target = tmp_path / "out" / "result.mp4"
    result = falcost.download("https://v3.fal.media/files/tiger/abc123_output.mp4", target)
    assert result == target
    assert result.exists()


def test_unknown_model_records_flagged_entry_and_warns(monkeypatch, tmp_path, capsys):
    log = tmp_path / "costs.jsonl"
    monkeypatch.setattr(falcost, "COST_LOG", log)
    falcost.record_cost("fal-ai/some-new-model-nobody-priced-yet")
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert entries[0]["model"] == "fal-ai/some-new-model-nobody-priced-yet"
    assert entries[0]["unknown_price"] is True
    assert entries[0]["usd"] == 0.0
    captured = capsys.readouterr()
    assert "fal-ai/some-new-model-nobody-priced-yet" in captured.err


def test_total_spent_survives_corrupted_log_lines(monkeypatch, tmp_path):
    log = tmp_path / "costs.jsonl"
    monkeypatch.setattr(falcost, "COST_LOG", log)
    lines = [
        json.dumps({"at": 1.0, "model": "fal-ai/whisper", "usd": 0.01}),
        "42",  # валидный JSON, но не объект (например, оборванная запись)
        '{"at": 2.0, "model": "fal-ai/whisper", "usd"',  # truncated / невалидный JSON
        json.dumps({"at": 3.0, "model": "fal-ai/whisper", "usd": 0.01}),
    ]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert falcost.total_spent() == 0.02


def test_download_in_mock_mode_preserves_existing_real_file(monkeypatch, tmp_path):
    """Mock-режим не должен затирать уже скачанный настоящий файл.

    Сценарий из задания: дорогое видео генерируют последним, поэтому
    разработчик мог получить реальный файл, а затем перезапустить пайплайн
    в mock-режиме для отладки остального кода. Существующий непустой
    target — это тот самый результат, его нужно оставить нетронутым.
    """
    monkeypatch.setattr(falcost, "FAL_MOCK", True)
    target = tmp_path / "out" / "result.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"real video bytes")

    result = falcost.download("https://v3.fal.media/files/tiger/abc123_output.mp4", target)

    assert result == target
    assert target.read_bytes() == b"real video bytes"


def test_download_in_mock_mode_creates_placeholder_when_no_target(monkeypatch, tmp_path):
    """А если сохранять нечего — заглушка по-прежнему создаётся как раньше."""
    monkeypatch.setattr(falcost, "FAL_MOCK", True)
    target = tmp_path / "out" / "result.mp4"

    result = falcost.download("https://v3.fal.media/files/tiger/abc123_output.mp4", target)

    assert result == target
    assert target.exists()
    assert target.read_bytes() == b""


def test_total_spent_warns_on_bad_amount_but_sums_valid_entries(monkeypatch, tmp_path, capsys):
    """Запись с некорректным usd не должна исчезать без следа.

    TypeError при сложении числа со строкой перехватывается (падать нельзя),
    но потеря записи из суммы должна быть видна в stderr — так же, как для
    неизвестных моделей.
    """
    log = tmp_path / "costs.jsonl"
    monkeypatch.setattr(falcost, "COST_LOG", log)
    lines = [
        json.dumps({"at": 1.0, "model": "fal-ai/whisper", "usd": 0.01}),
        json.dumps({"at": 2.0, "model": "fal-ai/whisper", "usd": "n/a"}),
        json.dumps({"at": 3.0, "model": "fal-ai/whisper", "usd": 0.01}),
    ]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    total = falcost.total_spent()

    assert total == 0.02
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_falcost.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'falcost'`.

- [ ] **Step 3: Реализовать обёртку**

`projects/5-ai-avatar-agent/falcost.py`:

```python
"""Единственная точка входа во все платные вызовы fal.ai.

Здесь живут три вещи, которые нельзя размазывать по коду: mock-режим (чтобы
отладка не стоила денег), ретраи и учёт расходов для README.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import urllib.request
from pathlib import Path

import fal_client

from config import CACHE_DIR, FAL_MOCK

COST_LOG = Path(CACHE_DIR) / "costs.jsonl"

# Оценка стоимости одного вызова в долларах. Точные суммы смотрим в кабинете fal,
# эти нужны, чтобы в README была правдоподобная цифра по ходу разработки.
PRICES: dict[str, float] = {
    "fal-ai/whisper": 0.01,
    "fal-ai/minimax/voice-clone": 0.50,
    "fal-ai/minimax/speech-02-hd": 0.02,
    "fal-ai/creatify/aurora": 1.00,
    "fal-ai/kling-video/ai-avatar/v2/standard": 0.60,
}


def record_cost(model: str) -> None:
    """Дописывает строку в журнал расходов.

    Если модели нет в PRICES (опечатка, новая модель из будущей задачи,
    AVATAR_MODEL переопределён через окружение), запись всё равно пишется —
    реальный платный вызов нельзя тихо занулять. Такая запись помечается
    флагом ``unknown_price: True`` и оценка ставится в 0.0 (мы её просто не
    знаем), а в stderr печатается предупреждение с именем модели, чтобы
    аномалия не прошла незамеченной.
    """
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    known = model in PRICES
    if not known:
        print(
            f"⚠️  falcost: неизвестная модель '{model}' не найдена в PRICES — "
            "возможен реальный расход, который не попадёт в сумму total_spent()",
            file=sys.stderr,
        )
    entry = {
        "at": time.time(),
        "model": model,
        "usd": PRICES.get(model, 0.0),
        "unknown_price": not known,
    }
    with COST_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def total_spent() -> float:
    """Сумма по журналу расходов.

    Записи с ``unknown_price: True`` (модель отсутствовала в PRICES на
    момент вызова) вносят в сумму 0.0, а не реальную стоимость — она
    неизвестна. Такие записи остаются в логе с этим флагом, поэтому их
    легко отличить от честного нуля и досчитать вручную по кабинету fal.
    Любая строка, которая не парсится в JSON-объект, или в которой поле
    usd — не число (битая/оборванная запись), пропускается, чтобы не
    падать, но не молча: в stderr печатается предупреждение, иначе
    реальный расход тихо исчезнет из суммы без следа.
    """
    if not COST_LOG.exists():
        return 0.0
    total = 0.0
    for line in COST_LOG.read_text(encoding="utf-8").splitlines():
        try:
            total += json.loads(line).get("usd", 0.0)
        except (json.JSONDecodeError, AttributeError, TypeError) as error:
            print(
                f"⚠️  falcost: пропущена повреждённая строка в {COST_LOG}: {error}",
                file=sys.stderr,
            )
            continue
    return round(total, 2)


async def run_model(model: str, arguments: dict, mock_result: dict, attempts: int = 2) -> dict:
    """Вызывает модель fal или возвращает заглушку, если включён mock-режим.

    ``attempts`` — сколько раз пробовать до того, как поднять исключение.
    По умолчанию 2 (одна повторная попытка), чтобы поведение всех
    существующих вызовов не изменилось. Для дорогих моделей (например,
    генерация видео, ~$1 за прогон) имеет смысл передавать ``attempts=1``:
    повторная попытка там стоит дороже, чем экономит — при отказе дешевле
    один раз упасть и разобраться руками, чем молча заплатить ещё раз.
    """
    if attempts < 1:
        raise ValueError(f"attempts должен быть не меньше 1, получено {attempts}")

    if FAL_MOCK:
        print(f"🧪 mock: {model} (реальный вызов не выполнен)")
        return mock_result

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            result = await fal_client.subscribe_async(model, arguments=arguments)
            record_cost(model)
            return result
        except Exception as error:  # noqa: BLE001
            last_error = error
            if attempt < attempts - 1:
                await asyncio.sleep(2)
    raise RuntimeError(f"fal не ответил ({model}): {last_error}")


async def upload(path: str) -> str:
    """Загружает файл в fal и возвращает публичный URL."""
    if FAL_MOCK:
        return f"https://mock.local/{Path(path).name}"
    return await fal_client.upload_file_async(path)


def download(url: str, target: Path) -> Path:
    """Скачивает результат на диск.

    Решение о сети принимается по FAL_MOCK, а не по виду URL: в mock-режиме
    run_model может вернуть правдоподобный fal-URL (например,
    https://v3.fal.media/files/...), и string-matching по префиксу
    https://mock.local/ такой случай бы пропустил в реальную сеть. Префикс
    mock.local всё же распознаём отдельно — на случай, если такой URL
    придёт при выключенном FAL_MOCK.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    if FAL_MOCK or url.startswith("https://mock.local/"):
        # По заданию дорогое видео генерируют последним: разработчик мог
        # уже получить настоящий файл, а затем перезапустить пайплайн в
        # mock-режиме, чтобы отладить код дальше по цепочке без повторной
        # оплаты. Если target уже существует и не пуст — это тот самый
        # настоящий результат, и его нельзя молча затирать нулевым файлом.
        # Пустышку создаём только тогда, когда сохранять нечего.
        if target.exists() and target.stat().st_size > 0:
            return target
        target.write_bytes(b"")
        return target
    urllib.request.urlretrieve(url, target)
    return target
```

- [ ] **Step 4: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_falcost.py -v`
Expected: PASS, 13 passed.

- [ ] **Step 5: Коммит**

```bash
git add projects/5-ai-avatar-agent/falcost.py projects/5-ai-avatar-agent/tests/test_falcost.py
git commit -m "feat(project-5): обёртка fal с mock-режимом и учётом расходов"
```

---

### Task 11: ASR, клон голоса, TTS

**Files:**
- Create: `projects/5-ai-avatar-agent/voice/__init__.py`
- Create: `projects/5-ai-avatar-agent/voice/asr.py`
- Create: `projects/5-ai-avatar-agent/voice/clone.py`
- Create: `projects/5-ai-avatar-agent/voice/tts.py`
- Test: `projects/5-ai-avatar-agent/tests/test_voice.py`

**Interfaces:**
- Consumes: `falcost.run_model`, `falcost.upload`, `falcost.download`, `config.ASR_MODEL`, `config.VOICE_CLONE_MODEL`, `config.TTS_MODEL`, `config.CACHE_DIR`, `config.OUTPUT_DIR`, `config.ASSETS_PRIVATE_DIR`.
- Produces: `async asr.transcribe(audio_path: str) -> str`; `async clone.get_voice_id(sample_path: str | None = None) -> str`, `clone.VOICE_ID_FILE: Path`; `async tts.synthesize(text: str, voice_id: str) -> Path`.

- [ ] **Step 1: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_voice.py`:

```python
from pathlib import Path

import pytest

from voice import asr, clone, tts


async def test_transcribe_returns_stripped_text(monkeypatch):
    async def fake_upload(path):
        return "https://mock/audio.m4a"

    async def fake_run(model, arguments, mock_result):
        assert model == "fal-ai/whisper"
        assert arguments["audio_url"] == "https://mock/audio.m4a"
        return {"text": "  где поужинать  "}

    monkeypatch.setattr(asr.falcost, "upload", fake_upload)
    monkeypatch.setattr(asr.falcost, "run_model", fake_run)
    assert await asr.transcribe("/tmp/q.m4a") == "где поужинать"


async def test_voice_id_is_read_from_cache_without_calling_fal(tmp_path, monkeypatch):
    cache_file = tmp_path / "voice_id.txt"
    cache_file.write_text("voice-123", encoding="utf-8")
    monkeypatch.setattr(clone, "VOICE_ID_FILE", cache_file)

    async def explode(*args, **kwargs):
        raise AssertionError("клонировать повторно нельзя — это деньги")

    monkeypatch.setattr(clone.falcost, "run_model", explode)
    assert await clone.get_voice_id() == "voice-123"


async def test_clone_saves_custom_voice_id(tmp_path, monkeypatch):
    cache_file = tmp_path / "voice_id.txt"
    monkeypatch.setattr(clone, "VOICE_ID_FILE", cache_file)
    sample = tmp_path / "sample.m4a"
    sample.write_bytes(b"audio")

    async def fake_upload(path):
        return "https://mock/sample.m4a"

    async def fake_run(model, arguments, mock_result):
        assert model == "fal-ai/minimax/voice-clone"
        return {"custom_voice_id": "voice-999"}

    monkeypatch.setattr(clone.falcost, "upload", fake_upload)
    monkeypatch.setattr(clone.falcost, "run_model", fake_run)
    assert await clone.get_voice_id(str(sample)) == "voice-999"
    assert cache_file.read_text(encoding="utf-8").strip() == "voice-999"


async def test_clone_without_sample_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(clone, "VOICE_ID_FILE", tmp_path / "нет.txt")
    with pytest.raises(FileNotFoundError):
        await clone.get_voice_id(str(tmp_path / "нет.m4a"))


async def test_tts_uses_nested_voice_setting(tmp_path, monkeypatch):
    seen = {}

    async def fake_run(model, arguments, mock_result):
        seen.update(arguments)
        return {"audio": {"url": "https://mock/answer.mp3"}}

    def fake_download(url, target):
        Path(target).write_bytes(b"mp3")
        return Path(target)

    monkeypatch.setattr(tts.falcost, "run_model", fake_run)
    monkeypatch.setattr(tts.falcost, "download", fake_download)
    monkeypatch.setattr(tts, "OUTPUT_DIR", tmp_path)
    path = await tts.synthesize("Привет", "voice-1")
    assert seen["voice_setting"]["voice_id"] == "voice-1"
    assert path.exists()
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_voice.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'voice'`.

- [ ] **Step 3: Реализовать три модуля**

`projects/5-ai-avatar-agent/voice/__init__.py` — пустой файл.

`projects/5-ai-avatar-agent/voice/asr.py`:

```python
"""Распознавание речи через fal-hosted Whisper."""

from __future__ import annotations

import falcost
from config import ASR_MODEL


async def transcribe(audio_path: str) -> str:
    """Превращает аудиофайл в текст вопроса."""
    audio_url = await falcost.upload(audio_path)
    result = await falcost.run_model(
        ASR_MODEL,
        {"audio_url": audio_url, "task": "transcribe"},
        mock_result={"text": "Где поужинать в центре Алматы на двоих?"},
    )
    return (result.get("text") or "").strip()
```

`projects/5-ai-avatar-agent/voice/clone.py`:

```python
"""Клонирование голоса. Выполняется один раз за проект — это платно.

voice_id кэшируется в файл по абсолютному пути: иначе запуск из другого каталога
склонирует голос заново и потратит деньги повторно.
"""

from __future__ import annotations

from pathlib import Path

import falcost
from config import ASSETS_PRIVATE_DIR, CACHE_DIR, VOICE_CLONE_MODEL

VOICE_ID_FILE = Path(CACHE_DIR) / "voice_id.txt"
DEFAULT_SAMPLE = Path(ASSETS_PRIVATE_DIR) / "voice_sample.m4a"


async def get_voice_id(sample_path: str | None = None) -> str:
    """Возвращает id клонированного голоса, клонируя его при первом обращении."""
    if VOICE_ID_FILE.exists():
        cached = VOICE_ID_FILE.read_text(encoding="utf-8").strip()
        if cached:
            return cached

    sample = Path(sample_path) if sample_path else DEFAULT_SAMPLE
    if not sample.exists():
        raise FileNotFoundError(
            f"Нет аудиосэмпла для клонирования голоса: {sample}. "
            "Положи запись своего голоса (10+ секунд) в assets-private/voice_sample.m4a"
        )

    audio_url = await falcost.upload(str(sample))
    result = await falcost.run_model(
        VOICE_CLONE_MODEL,
        {
            "audio_url": audio_url,
            "noise_reduction": True,
            "need_volume_normalization": True,
        },
        mock_result={"custom_voice_id": "mock-voice-id"},
    )
    # Внимание: модель возвращает custom_voice_id, а не voice_id, как написано
    # в задании. Проверено на рабочем коде семинара 19.
    voice_id = result["custom_voice_id"]
    VOICE_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    VOICE_ID_FILE.write_text(voice_id, encoding="utf-8")
    return voice_id
```

`projects/5-ai-avatar-agent/voice/tts.py`:

```python
"""Синтез речи клонированным голосом."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import falcost
from config import OUTPUT_DIR, TTS_MODEL


async def synthesize(text: str, voice_id: str) -> Path:
    """Озвучивает текст и возвращает путь к mp3."""
    result = await falcost.run_model(
        TTS_MODEL,
        {
            "text": text,
            # Голос передаётся вложенным объектом — плоское поле voice_id,
            # как в задании, модель игнорирует.
            "voice_setting": {"voice_id": voice_id, "speed": 1, "vol": 1, "pitch": 0},
            "output_format": "url",
        },
        mock_result={"audio": {"url": "https://mock.local/answer.mp3"}},
    )
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = Path(OUTPUT_DIR) / f"answer_{stamp}.mp3"
    return falcost.download(result["audio"]["url"], target)
```

- [ ] **Step 4: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_voice.py -v`
Expected: PASS, 5 passed.

- [ ] **Step 5: Коммит**

```bash
git add projects/5-ai-avatar-agent/voice projects/5-ai-avatar-agent/tests/test_voice.py
git commit -m "feat(project-5): ASR, клон голоса и TTS через fal"
```

---

### Task 12: Генерация видео с аватаром

**Files:**
- Create: `projects/5-ai-avatar-agent/avatar/__init__.py`
- Create: `projects/5-ai-avatar-agent/avatar/generate.py`
- Test: `projects/5-ai-avatar-agent/tests/test_avatar.py`

**Interfaces:**
- Consumes: `falcost`, `config.AVATAR_MODEL`, `config.AVATAR_FALLBACK_MODEL`, `config.ASSETS_PRIVATE_DIR`, `config.OUTPUT_DIR`.
- Produces: `avatar.AURORA_PROMPT: str`, `avatar.DEFAULT_PHOTO: Path`, `async avatar.generate_video(audio_path: str, photo_path: str | None = None) -> Path`.

- [ ] **Step 1: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_avatar.py`:

```python
from pathlib import Path

import pytest

from avatar import generate


async def test_uses_aurora_with_spec_parameters(tmp_path, monkeypatch):
    photo = tmp_path / "me.jpg"
    photo.write_bytes(b"jpg")
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"mp3")
    seen = {}

    async def fake_upload(path):
        return f"https://mock/{Path(path).name}"

    async def fake_run(model, arguments, mock_result, attempts=2):
        seen["model"] = model
        seen["arguments"] = arguments
        seen["attempts"] = attempts
        return {"video": {"url": "https://mock/v.mp4"}}

    monkeypatch.setattr(generate.falcost, "upload", fake_upload)
    monkeypatch.setattr(generate.falcost, "run_model", fake_run)
    monkeypatch.setattr(generate.falcost, "download", lambda url, target: Path(target))
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)

    await generate.generate_video(str(audio), str(photo))
    assert seen["model"] == "fal-ai/creatify/aurora"
    assert seen["arguments"]["guidance_scale"] == 1
    assert seen["arguments"]["audio_guidance_scale"] == 2
    assert seen["arguments"]["resolution"] == "720p"
    assert seen["attempts"] == 1


async def test_falls_back_to_kling_when_aurora_fails(tmp_path, monkeypatch):
    photo = tmp_path / "me.jpg"
    photo.write_bytes(b"jpg")
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"mp3")
    models = []
    attempts_seen = []

    async def fake_upload(path):
        return "https://mock/file"

    async def fake_run(model, arguments, mock_result, attempts=2):
        models.append(model)
        attempts_seen.append(attempts)
        if model == "fal-ai/creatify/aurora":
            raise RuntimeError("aurora недоступна")
        return {"video": {"url": "https://mock/v.mp4"}}

    monkeypatch.setattr(generate.falcost, "upload", fake_upload)
    monkeypatch.setattr(generate.falcost, "run_model", fake_run)
    monkeypatch.setattr(generate.falcost, "download", lambda url, target: Path(target))
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)

    await generate.generate_video(str(audio), str(photo))
    assert models == ["fal-ai/creatify/aurora", "fal-ai/kling-video/ai-avatar/v2/standard"]
    assert attempts_seen == [1, 1]


async def test_both_models_failing_costs_exactly_two_paid_invocations(tmp_path, monkeypatch):
    """Бюджетная гарантия: худший случай generate_video() — 2 платных вызова.

    Даже если и основная модель, и fallback падают, каждая должна быть
    вызвана ровно один раз (attempts=1), а не по два раза каждая (как было
    бы со штатным retry falcost.run_model). Иначе один неудачный прогон мог
    бы стоить до 4 платных попыток при бюджете проекта ~$15-20.
    """
    photo = tmp_path / "me.jpg"
    photo.write_bytes(b"jpg")
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"mp3")
    invocations = []

    async def fake_upload(path):
        return "https://mock/file"

    async def fake_run(model, arguments, mock_result, attempts=2):
        invocations.append((model, attempts))
        raise RuntimeError(f"{model} недоступна")

    monkeypatch.setattr(generate.falcost, "upload", fake_upload)
    monkeypatch.setattr(generate.falcost, "run_model", fake_run)
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)

    with pytest.raises(RuntimeError):
        await generate.generate_video(str(audio), str(photo))

    assert len(invocations) == 2
    assert invocations == [
        ("fal-ai/creatify/aurora", 1),
        ("fal-ai/kling-video/ai-avatar/v2/standard", 1),
    ]


async def test_missing_photo_raises_with_helpful_message(tmp_path, monkeypatch):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"mp3")
    monkeypatch.setattr(generate, "DEFAULT_PHOTO", tmp_path / "нет.jpg")
    with pytest.raises(FileNotFoundError, match="assets-private"):
        await generate.generate_video(str(audio))
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_avatar.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'avatar'`.

- [ ] **Step 3: Реализовать генерацию**

`projects/5-ai-avatar-agent/avatar/__init__.py` — пустой файл.

`projects/5-ai-avatar-agent/avatar/generate.py`:

```python
"""Генерация видео с говорящим аватаром.

Самый дорогой шаг пайплайна. Запускать только после того, как всё остальное
работает стабильно.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import falcost
from config import ASSETS_PRIVATE_DIR, AVATAR_FALLBACK_MODEL, AVATAR_MODEL, OUTPUT_DIR

DEFAULT_PHOTO = Path(ASSETS_PRIVATE_DIR) / "photo.jpg"

AURORA_PROMPT = (
    "4K studio interview, medium close-up. "
    "Soft key-light, light-grey backdrop. "
    "Presenter faces lens, steady eye-contact. Ultra-sharp."
)


async def generate_video(audio_path: str, photo_path: str | None = None) -> Path:
    """Собирает видео из фотографии и озвученного ответа."""
    photo = Path(photo_path) if photo_path else DEFAULT_PHOTO
    if not photo.exists():
        raise FileNotFoundError(
            f"Нет фотографии для аватара: {photo}. "
            "Положи фронтальный портрет 512×512+ в assets-private/photo.jpg"
        )

    image_url = await falcost.upload(str(photo))
    audio_url = await falcost.upload(audio_path)
    mock = {"video": {"url": "https://mock.local/avatar.mp4"}}

    # attempts=1 для обеих моделей: видео — самая дорогая операция в проекте
    # (~$1 за прогон при бюджете ~$15-20), а на этот вызов уже есть свой
    # fallback на вторую модель. Штатный retry falcost.run_model (attempts=2)
    # умножил бы худший случай до 4 платных попыток за один generate_video();
    # с attempts=1 на каждом шаге худший случай — 2 (по одной на модель). Не
    # "чинить" это обратно на attempts=2 — тут это осознанный анти-ретрай.
    try:
        result = await falcost.run_model(
            AVATAR_MODEL,
            {
                "image_url": image_url,
                "audio_url": audio_url,
                "prompt": AURORA_PROMPT,
                "guidance_scale": 1,
                "audio_guidance_scale": 2,
                "resolution": "720p",
            },
            mock_result=mock,
            attempts=1,
        )
    except Exception as error:  # noqa: BLE001 — падение Aurora не должно стоить нам демо
        print(f"⚠️  {AVATAR_MODEL} не отработала ({error}), пробую {AVATAR_FALLBACK_MODEL}")
        result = await falcost.run_model(
            AVATAR_FALLBACK_MODEL,
            {"image_url": image_url, "audio_url": audio_url},
            mock_result=mock,
            attempts=1,
        )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = Path(OUTPUT_DIR) / f"avatar_{stamp}.mp4"
    return falcost.download(result["video"]["url"], target)
```

- [ ] **Step 4: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_avatar.py -v`
Expected: PASS, 4 passed.

- [ ] **Step 5: Коммит**

```bash
git add projects/5-ai-avatar-agent/avatar projects/5-ai-avatar-agent/tests/test_avatar.py
git commit -m "feat(project-5): генерация видео-аватара через Creatify Aurora"
```

---

### Task 13: Оркестратор пайплайна

**Files:**
- Create: `projects/5-ai-avatar-agent/agent/pipeline.py`
- Test: `projects/5-ai-avatar-agent/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `llm.run_turn`, `llm.build_user_message`, `mcp_bridge.McpToolset`, `voice.asr.transcribe`, `voice.clone.get_voice_id`, `voice.tts.synthesize`, `avatar.generate.generate_video`, `config`.
- Produces: `pipeline.Agent` с `async start()`, `async stop()`, `async ask(text: str, audio_path: str | None, image_path: str | None, history: list) -> dict`, `async speak(text: str) -> Path`, `async make_video(audio_path: str) -> Path`; `pipeline.SERVER_PATHS: dict[str, str]`.

- [ ] **Step 1: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_pipeline.py`:

```python
from pathlib import Path

from agent import pipeline


class FakeToolset:
    def __init__(self, *args, **kwargs):
        self.call_log = []
        self.opened = False

    async def open(self):
        self.opened = True

    async def close(self):
        self.opened = False

    def specs(self):
        return []

    def handles(self, name):
        return False


async def test_ask_transcribes_audio_when_no_text(monkeypatch):
    agent = pipeline.Agent()
    agent._toolset = FakeToolset()

    async def fake_transcribe(path):
        return "распознанный вопрос"

    async def fake_run_turn(client, toolset, history, user_message):
        return f"ответ на: {user_message['content']}", history + [user_message], []

    monkeypatch.setattr(pipeline, "transcribe", fake_transcribe)
    monkeypatch.setattr(pipeline, "run_turn", fake_run_turn)

    result = await agent.ask("", "/tmp/a.m4a", None, [])
    assert result["question"] == "распознанный вопрос"
    assert "распознанный вопрос" in result["answer"]


async def test_ask_returns_tool_log(monkeypatch):
    agent = pipeline.Agent()
    agent._toolset = FakeToolset()

    async def fake_run_turn(client, toolset, history, user_message):
        return "готово", history, [{"name": "twogis__search_restaurants", "result_size": 3}]

    monkeypatch.setattr(pipeline, "run_turn", fake_run_turn)
    result = await agent.ask("вопрос", None, None, [])
    assert result["tool_log"][0]["name"] == "twogis__search_restaurants"


async def test_start_is_lazy_and_idempotent(monkeypatch):
    created = []

    class TrackingToolset(FakeToolset):
        def __init__(self, servers):
            super().__init__()
            created.append(servers)

    monkeypatch.setattr(pipeline, "McpToolset", TrackingToolset)
    agent = pipeline.Agent()
    await agent.start()
    await agent.start()
    assert len(created) == 1


async def test_speak_uses_cached_voice(monkeypatch, tmp_path):
    agent = pipeline.Agent()
    calls = []

    async def fake_voice_id(sample_path=None):
        calls.append("voice")
        return "voice-1"

    async def fake_synthesize(text, voice_id):
        calls.append(f"tts:{voice_id}")
        return tmp_path / "a.mp3"

    monkeypatch.setattr(pipeline, "get_voice_id", fake_voice_id)
    monkeypatch.setattr(pipeline, "synthesize", fake_synthesize)
    path = await agent.speak("Привет")
    assert calls == ["voice", "tts:voice-1"]
    assert path == tmp_path / "a.mp3"


async def test_make_video_delegates(monkeypatch, tmp_path):
    agent = pipeline.Agent()

    async def fake_generate(audio_path, photo_path=None):
        return tmp_path / "v.mp4"

    monkeypatch.setattr(pipeline, "generate_video", fake_generate)
    assert await agent.make_video("/tmp/a.mp3") == tmp_path / "v.mp4"


def test_server_paths_point_to_existing_files():
    for path in pipeline.SERVER_PATHS.values():
        assert Path(path).exists()
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_pipeline.py -v`
Expected: FAIL — `ImportError: cannot import name 'pipeline'`.

- [ ] **Step 3: Реализовать оркестратор**

`projects/5-ai-avatar-agent/agent/pipeline.py`:

```python
"""Оркестратор: единственное место, знающее полный порядок шагов.

ASR → агент с инструментами → (по требованию) TTS → (по требованию) видео.
"""

from __future__ import annotations

from pathlib import Path

from openai import AsyncOpenAI

import config
from agent.llm import build_user_message, run_turn
from agent.mcp_bridge import McpToolset
from avatar.generate import generate_video
from voice.asr import transcribe
from voice.clone import get_voice_id
from voice.tts import synthesize

SERVER_PATHS: dict[str, str] = {
    "twogis": str(config.BASE_DIR / "mcp_servers" / "twogis" / "server.py"),
    "chocolife": str(config.BASE_DIR / "mcp_servers" / "chocolife" / "server.py"),
}


class Agent:
    """Живёт всё время работы приложения: держит MCP-серверы поднятыми."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI()
        self._toolset: McpToolset | None = None

    async def start(self) -> None:
        """Поднимает MCP-серверы.

        Вызывается лениво, из первого же обработчика: клиенты fastmcp привязаны
        к событийному циклу, в котором были созданы, а Gradio крутит свой
        собственный. Поднимать их заранее в другом цикле — гарантированная
        поломка при первом же вызове инструмента.
        """
        if self._toolset is not None:
            return
        toolset = McpToolset(SERVER_PATHS)
        await toolset.open()
        self._toolset = toolset
        print(f"✅ Подняты MCP-серверы: {', '.join(SERVER_PATHS)}")

    async def stop(self) -> None:
        if self._toolset is not None:
            await self._toolset.close()
            self._toolset = None

    async def ask(
        self,
        text: str,
        audio_path: str | None,
        image_path: str | None,
        history: list,
    ) -> dict:
        """Один ход диалога. Возвращает вопрос, ответ, историю и лог инструментов."""
        await self.start()
        question = text.strip()
        if not question and audio_path:
            question = await transcribe(audio_path)
        if not question and not image_path:
            return {
                "question": "",
                "answer": "Напиши вопрос, запиши голос или пришли фото.",
                "history": history,
                "tool_log": [],
            }
        if not question:
            question = "Что это за заведение и стоит ли туда идти?"

        user_message = build_user_message(question, image_path)
        answer, new_history, tool_log = await run_turn(
            self._client, self._toolset, history, user_message
        )
        return {
            "question": question,
            "answer": answer,
            "history": new_history,
            "tool_log": tool_log,
        }

    async def speak(self, text: str) -> Path:
        """Озвучивает текст клонированным голосом."""
        voice_id = await get_voice_id()
        return await synthesize(text, voice_id)

    async def make_video(self, audio_path: str) -> Path:
        """Собирает видео с аватаром по готовому аудио."""
        return await generate_video(audio_path)
```

- [ ] **Step 4: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_pipeline.py -v`
Expected: PASS, 5 passed.

- [ ] **Step 5: Прогнать весь набор тестов**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest -v`
Expected: все тесты зелёные.

- [ ] **Step 6: Коммит**

```bash
git add projects/5-ai-avatar-agent/agent/pipeline.py projects/5-ai-avatar-agent/tests/test_pipeline.py
git commit -m "feat(project-5): оркестратор пайплайна ASR → агент → TTS → аватар"
```

---

### Task 14: Интерфейс Gradio

**Files:**
- Create: `projects/5-ai-avatar-agent/app.py`
- Test: `projects/5-ai-avatar-agent/tests/test_app.py`

**Interfaces:**
- Consumes: `pipeline.Agent`.
- Produces: `app.format_tool_log(entries: list[dict]) -> str`, `async app.on_send(text, audio, image, history, agent_state) -> tuple`, `async app.on_speak(answer, make_video, agent_state) -> tuple`, `app.build_ui() -> gr.Blocks`.

- [ ] **Step 1: Написать падающий тест**

`projects/5-ai-avatar-agent/tests/test_app.py`:

```python
import app


class FakeAgent:
    def __init__(self, answer="ответ"):
        self.answer = answer
        self.spoken = []
        self.videos = []

    async def ask(self, text, audio_path, image_path, history):
        return {
            "question": text or "распознано",
            "answer": self.answer,
            "history": history + [{"role": "assistant", "content": self.answer}],
            "tool_log": [{"name": "twogis__search_restaurants",
                          "arguments": {"query": "суши"}, "result_size": 2}],
        }

    async def speak(self, text):
        self.spoken.append(text)
        return "/tmp/a.mp3"

    async def make_video(self, audio_path):
        self.videos.append(audio_path)
        return "/tmp/v.mp4"


def test_format_tool_log_is_readable():
    text = app.format_tool_log(
        [{"name": "twogis__search_restaurants", "arguments": {"query": "суши"}, "result_size": 2}]
    )
    assert "twogis__search_restaurants" in text
    assert "суши" in text


def test_format_tool_log_empty():
    assert "не вызывались" in app.format_tool_log([])


async def test_on_send_appends_both_messages():
    agent = FakeAgent()
    textbox, chat, history, log = await app.on_send("привет", None, None, [], agent)
    assert textbox == ""
    assert chat[-2]["role"] == "user"
    assert chat[-1]["role"] == "assistant"
    assert "twogis" in log


async def test_on_speak_without_video_returns_audio_only():
    agent = FakeAgent()
    audio, video, status = await app.on_speak("текст ответа", False, agent)
    assert audio == "/tmp/a.mp3"
    assert video is None
    assert agent.videos == []


async def test_on_speak_with_video_calls_generator():
    agent = FakeAgent()
    audio, video, status = await app.on_speak("текст ответа", True, agent)
    assert video == "/tmp/v.mp4"
    assert agent.videos == ["/tmp/a.mp3"]


async def test_on_speak_reports_failure_without_crashing():
    class BrokenAgent(FakeAgent):
        async def speak(self, text):
            raise RuntimeError("fal недоступен")

    audio, video, status = await app.on_speak("текст", True, BrokenAgent())
    assert audio is None
    assert "недоступен" in status
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 3: Реализовать приложение**

`projects/5-ai-avatar-agent/app.py`:

```python
"""Gradio-интерфейс агента.

Текстовый ответ приходит всегда и сразу. Озвучка и видео — только по кнопке:
это самые дорогие шаги, автоматически их запускать нельзя.
"""

from __future__ import annotations

import json

import gradio as gr

import config
from agent.pipeline import Agent


def format_tool_log(entries: list[dict]) -> str:
    """Готовит лог вызовов инструментов для показа в интерфейсе."""
    if not entries:
        return "Инструменты не вызывались."
    lines = []
    for entry in entries:
        arguments = json.dumps(entry.get("arguments", {}), ensure_ascii=False)
        if entry.get("error"):
            lines.append(f"❌ {entry['name']}({arguments}) → ошибка: {entry['error']}")
        else:
            lines.append(f"🛠 {entry['name']}({arguments}) → записей: {entry.get('result_size', 0)}")
    return "\n".join(lines)


async def on_send(text, audio, image, history, agent):
    """Обрабатывает отправку сообщения: возвращает очищенное поле, чат, историю и лог."""
    try:
        result = await agent.ask(text or "", audio, image, history)
    except Exception as error:  # noqa: BLE001
        raise gr.Error(f"Агент не смог ответить: {error}") from error

    chat = result["history"]
    display = [
        message for message in _as_display_messages(chat)
    ]
    return "", display, chat, format_tool_log(result["tool_log"])


def _as_display_messages(history: list) -> list[dict]:
    """Оставляет для чата только реплики пользователя и ассистента."""
    display: list[dict] = []
    for message in history:
        role = message.get("role") if isinstance(message, dict) else getattr(message, "role", None)
        if role not in ("user", "assistant"):
            continue
        content = message.get("content") if isinstance(message, dict) else message.content
        if isinstance(content, list):
            content = " ".join(part.get("text", "") for part in content if part.get("type") == "text")
        if not content:
            continue
        display.append({"role": role, "content": content})
    return display


async def on_speak(answer: str, make_video: bool, agent):
    """Озвучивает последний ответ и, если попросили, снимает видео."""
    if not answer.strip():
        return None, None, "Сначала получи текстовый ответ."
    try:
        audio_path = await agent.speak(answer)
    except Exception as error:  # noqa: BLE001
        return None, None, f"Озвучка не удалась: {error}"

    if not make_video:
        return str(audio_path), None, "Готово: аудио."

    try:
        video_path = await agent.make_video(str(audio_path))
    except Exception as error:  # noqa: BLE001
        return str(audio_path), None, f"Аудио готово, видео не собралось: {error}"
    return str(audio_path), str(video_path), "Готово: аудио и видео."


def build_ui(agent: Agent) -> gr.Blocks:
    """Собирает интерфейс. agent передаётся снаружи, чтобы его можно было подменить."""
    with gr.Blocks(title="AI Avatar Agent — рестораны Алматы") as demo:
        gr.Markdown(
            "# 🍽️ Проводник по ресторанам Алматы\n"
            "Спроси текстом, голосом или пришли фото заведения."
        )
        history_state = gr.State([])
        last_answer = gr.State("")

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(type="messages", height=420, label="Диалог")
                textbox = gr.Textbox(
                    placeholder="Где поужинать в центре на двоих, бюджет 15 000 тенге?",
                    label="Вопрос",
                )
                with gr.Row():
                    audio_in = gr.Audio(
                        sources=["microphone", "upload"], type="filepath", label="Голос"
                    )
                    image_in = gr.Image(type="filepath", label="Фото заведения или блюда")
                send = gr.Button("Спросить", variant="primary")

            with gr.Column(scale=2):
                make_video = gr.Checkbox(label="Сгенерировать видео с аватаром", value=False)
                speak = gr.Button("🎙️ Озвучить последний ответ")
                status = gr.Markdown("")
                audio_out = gr.Audio(label="Ответ голосом", interactive=False)
                video_out = gr.Video(label="Видео с аватаром", interactive=False)
                with gr.Accordion("Лог вызовов инструментов", open=True):
                    tool_log = gr.Textbox(label="", lines=8, interactive=False)

        async def _send(text, audio, image, history):
            textbox_value, display, new_history, log = await on_send(
                text, audio, image, history, agent
            )
            answer = display[-1]["content"] if display else ""
            return textbox_value, display, new_history, log, answer

        send.click(
            _send,
            [textbox, audio_in, image_in, history_state],
            [textbox, chatbot, history_state, tool_log, last_answer],
        )
        textbox.submit(
            _send,
            [textbox, audio_in, image_in, history_state],
            [textbox, chatbot, history_state, tool_log, last_answer],
        )

        async def _speak(answer, video_wanted):
            return await on_speak(answer, video_wanted, agent)

        speak.click(_speak, [last_answer, make_video], [audio_out, video_out, status])

    return demo


def main() -> None:
    # Ключи проверяем синхронно, до старта интерфейса. MCP-серверы поднимутся
    # лениво внутри событийного цикла Gradio — см. комментарий в Agent.start().
    config.load_environment()
    config.require_keys(need_fal=not config.FAL_MOCK)
    build_ui(Agent()).launch()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Запустить тесты**

Run: `cd projects/5-ai-avatar-agent && .venv/bin/pytest tests/test_app.py -v`
Expected: PASS, 6 passed.

- [ ] **Step 5: Запустить приложение вживую в офлайн-режиме**

```bash
cd projects/5-ai-avatar-agent
AVATAR_AGENT_OFFLINE=1 FAL_MOCK=1 .venv/bin/python app.py
```

Открыть http://127.0.0.1:7860, спросить «где поесть суши», убедиться: приходит текстовый ответ, в логе видны вызовы `twogis__search_restaurants`, история помнит предыдущий вопрос.

- [ ] **Step 6: Коммит**

```bash
git add projects/5-ai-avatar-agent/app.py projects/5-ai-avatar-agent/tests/test_app.py
git commit -m "feat(project-5): Gradio-интерфейс с логом вызовов инструментов"
```

---

### Task 15: Живая проверка бесплатных шагов

**Files:**
- Modify: `projects/5-ai-avatar-agent/mcp_servers/twogis/parser.py` (правка селекторов по факту)
- Modify: `projects/5-ai-avatar-agent/mcp_servers/chocolife/parser.py` (правка селекторов по факту)

**Interfaces:**
- Consumes: всё, собранное в задачах 1–14.
- Produces: подтверждение, что парсинг и агент работают на живых данных.

- [ ] **Step 1: Проверить парсинг вживую**

```bash
cd projects/5-ai-avatar-agent
.venv/bin/python -c "
import asyncio
from fastmcp import Client

async def main():
    async with Client('mcp_servers/twogis/server.py') as client:
        result = await client.call_tool('search_restaurants', {'query': 'итальянский ресторан'})
        data = result.data
        print('ошибка:', data['error'] or 'нет')
        for item in data['results'][:3]:
            print('-', item['name'], '|', item['address'], '|', item['rating'])

asyncio.run(main())
"
```

Expected: три реальных заведения с названиями и адресами. Если пусто — снять свежую фикстуру и поправить селекторы, затем прогнать `pytest tests/test_twogis_parser.py`.

- [ ] **Step 2: Проверить Chocolife вживую**

```bash
cd projects/5-ai-avatar-agent
.venv/bin/python -c "
import asyncio
from fastmcp import Client

async def main():
    async with Client('mcp_servers/chocolife/server.py') as client:
        result = await client.call_tool('search_deals', {'category': 'рестораны'})
        data = result.data
        print('ошибка:', data['error'] or 'нет')
        for item in data['results'][:3]:
            print('-', item['title'], '|', item['discount_price'])

asyncio.run(main())
"
```

Expected: три реальные акции. При пустом результате — та же процедура с фикстурой.

- [ ] **Step 3: Прогнать агента на живых данных**

```bash
cd projects/5-ai-avatar-agent
FAL_MOCK=1 .venv/bin/python app.py
```

Спросить: «Где поужинать в центре Алматы на двоих, бюджет 15 000 тенге?». Проверить по логу, что вызваны оба сервера, а в ответе фигурируют названия из выдачи. Затем спросить «а какое из них дешевле?» — убедиться, что агент помнит контекст.

- [ ] **Step 4: Проверить vision и custom skill**

Прислать фото ресторана с вопросом «стоит ли сюда идти?». В логе должен появиться `analyze_restaurant_photo`, а в ответе — оценка уровня заведения.

- [ ] **Step 5: Коммит правок селекторов**

```bash
git add projects/5-ai-avatar-agent/mcp_servers projects/5-ai-avatar-agent/tests/fixtures
git commit -m "fix(project-5): селекторы парсеров по живым страницам"
```

---

### Task 16: Платные шаги — голос, речь, видео

**Files:**
- Create: `projects/5-ai-avatar-agent/assets-private/voice_sample.m4a` (кладёт владелец)
- Create: `projects/5-ai-avatar-agent/assets-private/photo.jpg` (кладёт владелец)

**Interfaces:**
- Consumes: `voice.clone.get_voice_id`, `voice.tts.synthesize`, `avatar.generate.generate_video`, `falcost.total_spent`.
- Produces: `cache/voice_id.txt`, файлы в `output/`, заполненный `cache/costs.jsonl`.

**⚠️ Каждый шаг этой задачи тратит реальные деньги. Перед каждым — спросить владельца проекта.**

- [ ] **Step 1: Положить исходники**

Владелец кладёт запись голоса (10+ секунд, чистый звук) в
`projects/5-ai-avatar-agent/assets-private/voice_sample.m4a` и фронтальный портрет
(512×512 и больше, без очков, нейтральный фон) в
`projects/5-ai-avatar-agent/assets-private/photo.jpg`.

Проверка: `ls -la projects/5-ai-avatar-agent/assets-private/` — оба файла на месте.

- [ ] **Step 2: Клонировать голос (~$0.50, один раз)**

Спросить подтверждение, затем:

```bash
cd projects/5-ai-avatar-agent
FAL_MOCK=0 .venv/bin/python -c "
import asyncio, config
from voice.clone import get_voice_id
config.load_environment()
print('voice_id:', asyncio.run(get_voice_id()))
"
```

Expected: печатается id, файл `cache/voice_id.txt` создан. Повторный запуск команды
**не должен** тратить деньги — он читает кэш.

- [ ] **Step 3: Синтезировать короткую фразу (копейки)**

Спросить подтверждение, затем:

```bash
cd projects/5-ai-avatar-agent
FAL_MOCK=0 .venv/bin/python -c "
import asyncio, config
from voice.clone import get_voice_id
from voice.tts import synthesize
config.load_environment()

async def main():
    voice_id = await get_voice_id()
    path = await synthesize('Рекомендую ресторан Дель Папа на Достык 85.', voice_id)
    print('аудио:', path)

asyncio.run(main())
"
```

Expected: mp3 в `output/`, голос узнаваемо твой.

- [ ] **Step 4: Собрать видео с аватаром (самое дорогое)**

Спросить подтверждение, затем — на аудио из предыдущего шага:

```bash
cd projects/5-ai-avatar-agent
FAL_MOCK=0 .venv/bin/python -c "
import asyncio, glob, config
from avatar.generate import generate_video
config.load_environment()
audio = sorted(glob.glob('output/answer_*.mp3'))[-1]
print('видео:', asyncio.run(generate_video(audio)))
"
```

Expected: mp4 в `output/`, губы синхронны речи. Если Aurora упала — в выводе видно
переключение на Kling, видео всё равно получено.

- [ ] **Step 5: Полный прогон через интерфейс**

```bash
cd projects/5-ai-avatar-agent
FAL_MOCK=0 .venv/bin/python app.py
```

Задать вопрос голосом, получить текст, нажать «Озвучить» с включённой галочкой видео.
Проверить: аудио и видео появились в панели справа.

- [ ] **Step 6: Зафиксировать расходы**

```bash
cd projects/5-ai-avatar-agent
.venv/bin/python -c "import falcost; print('потрачено, оценка: $', falcost.total_spent())"
```

Записать число — оно пойдёт в README. Сверить с кабинетом fal.ai и использовать
фактическую цифру, если она отличается.

- [ ] **Step 7: Коммит**

```bash
git add projects/5-ai-avatar-agent/.gitignore
git commit -m "chore(project-5): проверены платные шаги пайплайна"
```

---

### Task 17: README, демо и сборка архива

**Files:**
- Create: `projects/5-ai-avatar-agent/README.md`
- Create: `projects/5-ai-avatar-agent/tools/make_zip.sh`
- Create: `projects/5-ai-avatar-agent/assets/` (скриншоты, demo.mp4 — кладёт владелец)

**Interfaces:**
- Consumes: всё готовое приложение, `falcost.total_spent()`.
- Produces: `README.md` со всеми семью разделами, `Имя_Фамилия.zip`.

- [ ] **Step 1: Сделать скриншоты**

Запустить приложение, снять два скриншота: диалог с текстовым ответом и раскрытым
логом инструментов, и панель с готовым видео. Положить в
`projects/5-ai-avatar-agent/assets/screenshot-chat.png` и `assets/screenshot-video.png`.

- [ ] **Step 2: Написать README**

`projects/5-ai-avatar-agent/README.md` — все семь разделов, требуемых заданием.
Числа в разделе «Стоимость» брать фактические, из `falcost.total_spent()` и кабинета fal.

```markdown
# 🍽️ AI Avatar Agent — проводник по ресторанам Алматы

Мультимодальный агент: принимает вопрос текстом, голосом или фотографией, ищет
заведения и скидки через два собственных MCP-сервера и отвечает текстом, а по
запросу — голосом студента и видео с говорящим аватаром.

## Архитектура

    вход: текст | аудио | фото
       ├─ аудио → fal-ai/whisper ────────► текст вопроса
       ├─ фото  → в сообщение как image-контент (detail: low)
       ▼
    агент (openai SDK, gpt-5.4-mini, function calling)
       ├─ MCP twogis     → search_restaurants   (Playwright → 2gis.kz)
       ├─ MCP chocolife  → search_deals         (Playwright → chocolife.me)
       └─ analyze_restaurant_photo              (собственный skill, vision)
       ▼
    текстовый ответ → [кнопка] TTS клонированным голосом → [галочка] видео-аватар

MCP-серверы — отдельные процессы, поднимаются приложением через stdio.

## Использованные модели

| Роль | Модель | Почему |
|---|---|---|
| Агент и vision | `gpt-5.4-mini` | Дёшево, быстро, надёжный tool calling, умеет картинки |
| ASR | `fal-ai/whisper` | Тот же ключ, что у остального fal, хорошо понимает русский |
| Клон голоса | `fal-ai/minimax/voice-clone` | Нужно 10 секунд записи, одна операция на проект |
| Синтез речи | `fal-ai/minimax/speech-02-hd` | Поддерживает клонированный голос, естественная интонация |
| Видео-аватар | `fal-ai/creatify/aurora` | Рекомендация задания; при сбое автоматический откат на Kling v2 |

## Запуск

1. Зависимости:

       python3.12 -m venv .venv
       .venv/bin/pip install -r requirements.txt
       .venv/bin/playwright install chromium

2. Ключи: скопировать `.env.example` в `.env` в корне репозитория и заполнить
   `OPENAI_API_KEY` и `FALAI_API_KEY`.

3. MCP-серверы запускать вручную не нужно — приложение поднимает их само.
   Для отладки по отдельности:

       .venv/bin/python mcp_servers/twogis/server.py
       .venv/bin/python mcp_servers/chocolife/server.py

4. Приложение:

       FAL_MOCK=0 .venv/bin/python app.py

   Открыть http://127.0.0.1:7860.

   Режимы для отладки без расходов: `FAL_MOCK=1` (заглушки вместо платных вызовов),
   `AVATAR_AGENT_OFFLINE=1` (сохранённые страницы вместо браузера).

## Скриншоты

![Диалог](assets/screenshot-chat.png)
![Видео](assets/screenshot-video.png)

## Тесты

    .venv/bin/pytest

Ни один тест не ходит в сеть и не тратит деньги.

## Про Playwright и MCP

Задание предлагает использовать `@playwright/mcp`. Здесь браузерная автоматизация
живёт **внутри** наших MCP-серверов: `playwright` вызывается как библиотека, а сервер
остаётся отдельным процессом, к которому агент подключается по MCP-протоколу и
инструменты которого LLM вызывает через function calling. Это даёт детерминированный
парсинг и тесты без LLM, не меняя роли MCP в архитектуре.

## Стоимость

| Статья | Сумма |
|---|---|
| OpenAI (разработка и демо) | $X.XX |
| fal: клон голоса | $0.50 |
| fal: синтез речи | $X.XX |
| fal: видео-аватар | $X.XX |
| **Итого** | **$X.XX** |

## Что бы улучшил

- Третий MCP-сервер по сети ABR Group.
- Потоковый ответ и потоковый TTS, чтобы не ждать генерацию целиком.
- Постоянное хранилище диалогов вместо памяти в рамках сессии.
- Автотесты парсеров против живых страниц по расписанию — селекторы неизбежно ломаются.
```

- [ ] **Step 3: Написать скрипт сборки архива**

`projects/5-ai-avatar-agent/tools/make_zip.sh`:

```bash
#!/usr/bin/env bash
# Собирает архив для сдачи: только код, без окружения, ключей и тяжёлых файлов.
set -euo pipefail

NAME="${1:?Использование: make_zip.sh Имя_Фамилия}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STAGING="$(mktemp -d)/${NAME}"

mkdir -p "${STAGING}"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
      --exclude 'cache' --exclude 'output' --exclude 'assets-private' \
      --exclude '.env' --exclude '*.pt' --exclude '*.bin' --exclude '*.ckpt' \
      "${PROJECT_DIR}/" "${STAGING}/"

cd "$(dirname "${STAGING}")"
zip -rq "${PROJECT_DIR}/${NAME}.zip" "${NAME}"
echo "Готово: ${PROJECT_DIR}/${NAME}.zip"
unzip -l "${PROJECT_DIR}/${NAME}.zip" | tail -5
```

```bash
chmod +x projects/5-ai-avatar-agent/tools/make_zip.sh
```

- [ ] **Step 4: Записать демо-видео**

Владелец записывает 2–3 минуты: постановка вопроса голосом, работа агента с видимым
логом инструментов, фото заведения, финальное видео с аватаром. Файл кладётся в
`projects/5-ai-avatar-agent/assets/demo.mp4`.

- [ ] **Step 5: Собрать и проверить архив**

```bash
cd projects/5-ai-avatar-agent
./tools/make_zip.sh Gizzat_Tazabekov
unzip -l Gizzat_Tazabekov.zip | grep -E "\.venv|\.env$|__pycache__|assets-private" || echo "чисто"
```

Expected: `чисто` — ничего запретного в архив не попало.

- [ ] **Step 6: Финальный прогон тестов и коммит**

```bash
cd projects/5-ai-avatar-agent && .venv/bin/pytest
cd ../.. && git add projects/5-ai-avatar-agent
git commit -m "docs(project-5): README, скрипт сборки архива и демо-материалы"
```

---

## Проверка по рубрике задания

Пройти перед сдачей, каждый пункт — своими глазами:

- [ ] Оба MCP-сервера поднимаются как отдельные процессы, лог в интерфейсе показывает реальные вызовы (25 баллов)
- [ ] Агент сам выбирает инструменты и помнит контекст диалога — проверено уточняющим вопросом (20 баллов)
- [ ] Видео с аватаром получено, губы синхронны (20 баллов)
- [ ] Фото заведения влияет на ответ (10 баллов)
- [ ] Голос в ответе — клонированный голос владельца (10 баллов)
- [ ] README со всеми семью разделами и demo.mp4 на месте (10 баллов)
- [ ] `analyze_restaurant_photo` вызывается самим агентом, а не интерфейсом (5 баллов)
- [ ] `detail: low`, кэш парсинга, кэш voice_id, медиа по кнопке — всё на месте (+10 баллов)
