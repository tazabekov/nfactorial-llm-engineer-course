"""Единственная точка входа во все платные вызовы fal.ai.

Здесь живут три вещи, которые нельзя размазывать по коду: mock-режим (чтобы
отладка не стоила денег), ретраи и учёт расходов для README.
"""

from __future__ import annotations

import asyncio
import json
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
    """Дописывает строку в журнал расходов."""
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {"at": time.time(), "model": model, "usd": PRICES.get(model, 0.0)}
    with COST_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def total_spent() -> float:
    """Сумма по журналу расходов."""
    if not COST_LOG.exists():
        return 0.0
    total = 0.0
    for line in COST_LOG.read_text(encoding="utf-8").splitlines():
        try:
            total += json.loads(line).get("usd", 0.0)
        except json.JSONDecodeError:
            continue
    return round(total, 2)


async def run_model(model: str, arguments: dict, mock_result: dict) -> dict:
    """Вызывает модель fal или возвращает заглушку, если включён mock-режим."""
    if FAL_MOCK:
        print(f"🧪 mock: {model} (реальный вызов не выполнен)")
        return mock_result

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            result = await fal_client.subscribe_async(model, arguments=arguments)
            record_cost(model)
            return result
        except Exception as error:  # noqa: BLE001
            last_error = error
            if attempt == 0:
                await asyncio.sleep(2)
    raise RuntimeError(f"fal не ответил ({model}): {last_error}")


async def upload(path: str) -> str:
    """Загружает файл в fal и возвращает публичный URL."""
    if FAL_MOCK:
        return f"https://mock.local/{Path(path).name}"
    return await fal_client.upload_file_async(path)


def download(url: str, target: Path) -> Path:
    """Скачивает результат на диск."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if url.startswith("https://mock.local/"):
        target.write_bytes(b"")
        return target
    urllib.request.urlretrieve(url, target)
    return target
