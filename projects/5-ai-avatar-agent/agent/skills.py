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

    try:
        mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
        data_url = f"data:{mime};base64,{encode_image(str(path))}"
    except OSError as error:
        return {"error": f"Не удалось прочитать файл: {error}"}

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
