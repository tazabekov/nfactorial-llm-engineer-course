"""Match staged furniture to the furniture_catalog Postgres table (Task 3).

Flow: a Gemini VL call extracts structured attributes (category/style/color)
of the main furniture item visible in the staged ("after") photo, then a SQL
query against `furniture_catalog` finds the closest matching row.
"""

import json
import os
from typing import Literal, Optional

import psycopg
from google.genai import types
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from scoring import get_client

Category = Literal["Диван", "Стол", "Стул", "Тумба", "Шкаф", "Кресло"]
Style = Literal["Modern", "Minimalist", "Classic", "Vintage", "Scandi"]


class FurnitureAttributes(BaseModel):
    category: Category = Field(description="Тип мебели, как в каталоге")
    style: Style = Field(description="Стиль мебели, как в каталоге")
    color: str = Field(description="Короткое название цвета по-русски, например 'светло-серый'")
    display_name: str = Field(description="Короткое название для отчёта, например 'Светло-серый диван'")


EXTRACTION_PROMPT = """\
Посмотри на фото интерьера после виртуального стейджинга. На фото есть новый \
или изменённый предмет мебели, добавленный по запросу: "{prompt}".

Определи этот предмет мебели и опиши его строго в JSON по схеме:
- category: тип мебели (один из: Диван, Стол, Стул, Тумба, Шкаф, Кресло)
- style: стиль (один из: Modern, Minimalist, Classic, Vintage, Scandi) — выбери \
ближайший по смыслу, даже если явно не указан на фото
- color: короткое название цвета по-русски
- display_name: короткое название для отчёта, например "Светло-серый диван"
"""


def extract_furniture_attributes(image_bytes: bytes, mime_type: str, staging_prompt: str) -> FurnitureAttributes:
    response = get_client().models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=[
            EXTRACTION_PROMPT.format(prompt=staging_prompt),
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FurnitureAttributes,
            temperature=0.1,
        ),
    )
    return FurnitureAttributes.model_validate(json.loads(response.text))


def find_matching_furniture(attrs: FurnitureAttributes) -> Optional[dict]:
    """Find the closest furniture_catalog row for the given attributes.

    Filters by category (exact match), then ranks candidates by how well
    their style and color match — a plain SQL query, no extra extensions.
    """
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT *,
                    (LOWER(style) = LOWER(%(style)s))::int AS style_match,
                    (LOWER(color) LIKE '%%' || LOWER(%(color)s) || '%%')::int AS color_match
                FROM furniture_catalog
                WHERE LOWER(category) = LOWER(%(category)s)
                ORDER BY style_match DESC, color_match DESC, rating DESC
                LIMIT 1
                """,
                {"category": attrs.category, "style": attrs.style, "color": attrs.color},
            )
            row = cur.fetchone()
            if row is not None:
                return row

            # No row in this category at all: fall back to the closest style match overall.
            cur.execute(
                """
                SELECT *, (LOWER(style) = LOWER(%(style)s))::int AS style_match
                FROM furniture_catalog
                ORDER BY style_match DESC, rating DESC
                LIMIT 1
                """,
                {"style": attrs.style},
            )
            return cur.fetchone()
