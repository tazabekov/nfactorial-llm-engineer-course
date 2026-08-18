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
