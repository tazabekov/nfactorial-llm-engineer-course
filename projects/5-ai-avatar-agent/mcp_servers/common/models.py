"""Модели данных, которые MCP-серверы возвращают агенту.

FastMCP выводит из них JSON-схему, поэтому описания полей видит LLM.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Restaurant(BaseModel):
    name: str = Field(description="Название заведения")
    address: str = Field(default="", description="Адрес")
    rating: float | None = Field(default=None, description="Рейтинг, если указан")
    price_range: str = Field(default="", description="Ценовая категория")
    cuisine: str = Field(default="", description="Кухня")
    working_hours: str = Field(default="", description="Часы работы")
    phone: str = Field(default="", description="Телефон")


class SearchResult(BaseModel):
    results: list[Restaurant] = Field(default_factory=list)
    source: str = Field(default="2gis.kz", description="Источник данных")
    cached: bool = Field(default=False, description="Ответ отдан из кэша")
    error: str = Field(default="", description="Причина, если данные получить не удалось")


class Deal(BaseModel):
    title: str = Field(description="Название акции")
    restaurant_name: str = Field(default="", description="Заведение")
    original_price: int | None = Field(default=None, description="Цена без скидки, тенге")
    discount_price: int | None = Field(default=None, description="Цена со скидкой, тенге")
    discount_percent: int | None = Field(default=None, description="Размер скидки, %")
    description: str = Field(default="", description="Описание предложения")
    url: str = Field(default="", description="Ссылка на предложение")


class DealsResult(BaseModel):
    results: list[Deal] = Field(default_factory=list)
    source: str = Field(default="chocolife.me")
    cached: bool = Field(default=False)
    error: str = Field(default="")
