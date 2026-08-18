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
