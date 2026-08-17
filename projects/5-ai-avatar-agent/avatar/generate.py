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
        )
    except Exception as error:  # noqa: BLE001 — падение Aurora не должно стоить нам демо
        print(f"⚠️  {AVATAR_MODEL} не отработала ({error}), пробую {AVATAR_FALLBACK_MODEL}")
        result = await falcost.run_model(
            AVATAR_FALLBACK_MODEL,
            {"image_url": image_url, "audio_url": audio_url},
            mock_result=mock,
        )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = Path(OUTPUT_DIR) / f"avatar_{stamp}.mp4"
    return falcost.download(result["video"]["url"], target)
