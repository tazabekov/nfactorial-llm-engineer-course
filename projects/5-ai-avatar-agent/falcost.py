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

from config import CACHE_DIR, FAL_BUDGET_CEILING_USD, FAL_MOCK

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
    Битая строка (не JSON, не объект, нечисловое поле usd) пропускается,
    чтобы подсчёт не падал, но каждый пропуск печатается в stderr —
    иначе реальный расход тихо исчезнет из суммы.
    """
    if not COST_LOG.exists():
        return 0.0
    total = 0.0
    for line in COST_LOG.read_text(encoding="utf-8").splitlines():
        try:
            total += json.loads(line).get("usd", 0.0)
        except (json.JSONDecodeError, AttributeError, TypeError) as error:
            # Строка битая целиком (не JSON, не объект) или поле usd —
            # не число (например, "n/a" после ручной правки лога).
            # Пропускаем её, чтобы не упасть, но не молча: предупреждаем
            # в stderr, иначе реальный расход тихо исчезнет из суммы.
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

    # Мягкий потолок расходов: считаем ПЕРЕД реальным платным вызовом, чтобы
    # отказ ни разу не позволил превысить бюджет — при достижении/превышении
    # платный вызов вообще не делается, только заглушка ошибки.
    spent = total_spent()
    if spent >= FAL_BUDGET_CEILING_USD:
        raise RuntimeError(
            f"Бюджет на платные вызовы fal исчерпан: потрачено ${spent:.2f} "
            f"при потолке ${FAL_BUDGET_CEILING_USD:.2f}. Чтобы продолжить, "
            "подними FAL_BUDGET_CEILING_USD в .env в корне репозитория."
        )

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
        # По заданию дорогое видео генерируют последним: разработчик мог уже
        # получить настоящий файл, а затем перезапустить пайплайн в
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
