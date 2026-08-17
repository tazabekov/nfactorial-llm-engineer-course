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
