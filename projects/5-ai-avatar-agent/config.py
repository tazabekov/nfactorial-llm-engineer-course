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

# Загружаем .env корня репозитория ДО чтения os.getenv() ниже — иначе
# FAL_MOCK=0, AGENT_MODEL и другие переопределения из .env тихо
# игнорируются (работает только форма PREFIX=value python app.py, .env
# читается лишь позже, изнутри load_environment()). load_dotenv по
# умолчанию не перезаписывает уже установленные переменные окружения,
# поэтому shell-форма переопределения продолжает работать как раньше.
load_dotenv(REPO_ROOT / ".env")

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

# --- Бюджет ---------------------------------------------------------------
# Мягкий потолок суммарных расходов на платные вызовы fal (см. falcost.py).
# При достижении/превышении falcost.run_model отказывается делать новый
# платный вызов вместо того, чтобы тратить дальше без ограничений.
FAL_BUDGET_CEILING_USD = float(os.getenv("FAL_BUDGET_CEILING_USD", "5.00"))


def load_environment() -> None:
    """Перечитывает .env (идемпотентно — модуль уже загрузил его при импорте)
    и настраивает FAL_KEY для fal SDK.

    Оставлен для существующих вызывающих (app.main()): реального повторного
    парсинга constants не делает — они уже прочитаны при импорте модуля выше,
    — но FALAI_API_KEY → FAL_KEY переносится именно здесь, при явном вызове,
    а не при импорте, чтобы не привязывать этот побочный эффект ко времени
    импорта config.
    """
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
