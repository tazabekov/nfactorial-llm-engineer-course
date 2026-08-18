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
        # Текст-заглушка НАМЕРЕННО помечен префиксом: без него пользователь
        # в mock-режиме увидит правдоподобный, но полностью выдуманный
        # вопрос вместо своего реального — и получит ответ на чужой вопрос,
        # не подозревая об этом (см. C1 финального ревью). Префикс делает
        # подмену невозможно не заметить.
        mock_result={
            "text": "[РЕЖИМ ЗАГЛУШКИ — это не настоящая расшифровка] "
            "Где поужинать в центре Алматы на двоих?"
        },
    )
    return (result.get("text") or "").strip()
