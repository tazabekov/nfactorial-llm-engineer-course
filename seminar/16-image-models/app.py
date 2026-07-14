"""FastAPI backend for the AI apartment scoring & virtual staging website."""

import base64
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from furniture import extract_furniture_attributes, find_matching_furniture  # noqa: E402
from scoring import score_apartment_photo  # noqa: E402  (needs env vars loaded first)
from staging import (  # noqa: E402
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
    stage_photo,
)

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="AI Apartment Scoring")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/analyze")
async def analyze(photo: UploadFile) -> JSONResponse:
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Пожалуйста, загрузите файл изображения.")

    image_bytes = await photo.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Файл изображения пуст.")

    try:
        score = score_apartment_photo(image_bytes, photo.content_type)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Не удалось получить оценку от модели: {exc}"
        ) from exc

    return JSONResponse(content=score.model_dump())


@app.post("/stage")
async def stage(
    photo: UploadFile,
    prompt: str = Form(...),
    temperature: float = Form(DEFAULT_TEMPERATURE),
    top_p: float = Form(DEFAULT_TOP_P),
    top_k: int = Form(DEFAULT_TOP_K),
    seed: Optional[int] = Form(None),
) -> JSONResponse:
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Пожалуйста, загрузите файл изображения.")

    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Опишите, что нужно изменить на фото.")

    image_bytes = await photo.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Файл изображения пуст.")

    try:
        result_bytes, result_mime = stage_photo(
            image_bytes,
            photo.content_type,
            prompt,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            seed=seed,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Не удалось сгенерировать изображение: {exc}"
        ) from exc

    return JSONResponse(
        content={
            "image_base64": base64.b64encode(result_bytes).decode("ascii"),
            "mime_type": result_mime,
        }
    )


class ReportRequest(BaseModel):
    image_base64: str
    mime_type: str
    staging_prompt: str
    before_modernity: int


@app.post("/report")
async def report(payload: ReportRequest) -> JSONResponse:
    try:
        image_bytes = base64.b64decode(payload.image_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Некорректное изображение.") from exc

    try:
        after_score = score_apartment_photo(image_bytes, payload.mime_type)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Не удалось повторно оценить квартиру: {exc}"
        ) from exc

    try:
        attrs = extract_furniture_attributes(image_bytes, payload.mime_type, payload.staging_prompt)
        match = find_matching_furniture(attrs)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Не удалось сопоставить мебель с каталогом: {exc}"
        ) from exc

    if match is None:
        raise HTTPException(status_code=404, detail="В каталоге не нашлось подходящей мебели.")

    price = float(match["price_kzt"])
    report_text = (
        f"Квартира преобразилась! Оценка дизайна выросла с {payload.before_modernity} "
        f"до {after_score.modernity}. Добавленная мебель: {attrs.display_name} "
        f"({match['style']}). Примерная стоимость обновления: {price:,.0f} тг."
    ).replace(",", " ")

    return JSONResponse(
        content={
            "report_text": report_text,
            "before_modernity": payload.before_modernity,
            "after_modernity": after_score.modernity,
            "extracted": attrs.model_dump(),
            "matched_furniture": {
                "model_name": match["model_name"],
                "style": match["style"],
                "color": match["color"],
                "price_kzt": price,
                "description": match["description"],
            },
        }
    )
