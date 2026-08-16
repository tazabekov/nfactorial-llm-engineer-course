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
