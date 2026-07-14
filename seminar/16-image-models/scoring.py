"""AI-scoring of apartment/room photos using a Vision-Language model (Gemini).

Casts the model as a veteran real-estate appraiser and forces a strict JSON
response scoring the photo on 5 realtor criteria (1-10 each).
"""

import json
import os
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class ApartmentScore(BaseModel):
    cleanliness: int = Field(ge=1, le=10, description="Чистота и порядок")
    repair_condition: int = Field(ge=1, le=10, description="Состояние ремонта")
    modernity: int = Field(ge=1, le=10, description="Актуальность дизайна")
    lighting: int = Field(ge=1, le=10, description="Освещенность")
    clutter: int = Field(ge=1, le=10, description="Захламленность (10 = свободно от лишних вещей)")
    summary: str = Field(description="Короткий вердикт оценщика (1-2 предложения)")


SYSTEM_PROMPT = """\
Ты — опытный оценщик недвижимости с 15-летним стажем, работающий на крупной \
платформе аренды и продажи жилья. Ты просматриваешь тысячи фотографий квартир \
и умеешь быстро и объективно оценивать состояние помещения по одному фото.

Оцени присланную фотографию комнаты по следующим шкалам от 1 до 10:

1. cleanliness (Чистота и порядок): 1 — сильный беспорядок/грязь, 10 — идеальная \
чистота ("как в отеле").
2. repair_condition (Состояние ремонта): 1 — требует капитального ремонта, 10 — \
свежий евроремонт отличного качества.
3. modernity (Актуальность дизайна): 1 — "бабушкин ремонт" / устаревшая мебель, \
10 — современный стильный дизайн (лофт, минимализм, сканди).
4. lighting (Освещенность): 1 — темное, мрачное помещение, 10 — светлая комната \
с большими окнами и хорошим светом.
5. clutter (Захламленность): 1 — много лишних личных вещей, 10 — пространство \
свободно.

Оценивай строго на основе визуальных доказательств на фото, без домыслов о том, \
чего не видно. Также напиши краткий вердикт (summary) на русском языке в стиле \
профессионального оценщика недвижимости — 1-2 предложения.

Отвечай СТРОГО в формате JSON, соответствующем заданной схеме, без какого-либо \
дополнительного текста до или после JSON.
"""

DEFAULT_MODEL = "gemini-2.5-flash"

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ["GEMINI_API_KEY"]
        _client = genai.Client(api_key=api_key)
    return _client


def score_apartment_photo(image_bytes: bytes, mime_type: str) -> ApartmentScore:
    """Send a room photo to the Gemini VL model and return the structured score."""
    model_name = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)

    response = get_client().models.generate_content(
        model=model_name,
        contents=[
            "Оцени состояние этой квартиры/комнаты по фото.",
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ApartmentScore,
            temperature=0.2,
        ),
    )

    data = json.loads(response.text)
    return ApartmentScore.model_validate(data)
