"""Разбор страницы поиска 2GIS в список заведений.

Функция чистая: на входе HTML, на выходе модели. Это позволяет тестировать
парсер на сохранённой странице, не поднимая браузер.

Селекторы ниже не угаданы, а сняты с живой фикстуры (см.
tests/fixtures/twogis_search.html, снята tools/capture_fixture.py). Классы
2ГИС обфусцированы и генерируются сборкой, поэтому при поломке — переснять
фикстуру и обновить селекторы под неё же, не подгонять тест под старые данные.
"""

from __future__ import annotations

import re
from urllib.parse import quote

from bs4 import BeautifulSoup
from bs4.element import Tag

from mcp_servers.common.models import Restaurant

# Карточка заведения в списке результатов поиска.
CARD_SELECTOR = "div._1kf6gff"
# Запасной вариант, если структура карточки поменяется сильнее: ищем сами
# ссылки на карточки фирм и поднимаемся до ближайшего div-контейнера.
FIRM_LINK_PATTERN = re.compile(r"/firm/\d+")

# Название и ссылка на карточку заведения.
_NAME_SELECTOR = "a._1rehek"
# Рейтинг — отдельный блок с числом вида "4.9".
_RATING_SELECTOR = "div._y10azs"
# Рубрика (вид кухни/заведения), например "Ресторан", "Лаундж-бар".
_CUISINE_SELECTOR = "div._1idnaau a._1jvng3r"
# Телефон — прямая ссылка tel:, доступна не у всех карточек в выдаче.
_PHONE_SELECTOR = "a[href^='tel:']"
# Простой адрес без филиалов.
_ADDRESS_SIMPLE_SELECTOR = "span._3yxk2u"
# Адрес у заведений с несколькими филиалами: первый span внутри — сам адрес,
# второй — ссылка "N филиалов", которую в адрес включать не нужно.
_ADDRESS_MULTI_SELECTOR = "span._14quei span._sfdp8cg"

_ZERO_WIDTH_SPACE = "​"


def build_search_url(query: str, location: str = "almaty") -> str:
    """Собирает URL поиска: пробелы кодируются, иначе Playwright ругается."""
    return f"https://2gis.kz/{location}/search/{quote(query)}"


def _text(node: Tag, selector: str) -> str:
    found = node.select_one(selector)
    return found.get_text(" ", strip=True) if found else ""


def _phone(card: Tag) -> str:
    """Номер лежит в href="tel:...", а не в тексте — текст ссылки это "Позвонить"."""
    node = card.select_one(_PHONE_SELECTOR)
    if node is None:
        return ""
    return node.get("href", "").removeprefix("tel:")


def _rating(card: Tag) -> float | None:
    node = card.select_one(_RATING_SELECTOR)
    if node is None:
        return None
    match = re.search(r"([0-5][.,]\d)", node.get_text(strip=True))
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def _address_and_hours(card: Tag) -> tuple[str, str]:
    """Адрес и часы работы лежат в двух div._klarpw подряд.

    У блока с часами работы всегда проставлен inline-style (цвет текста —
    красный, если закрыто, зелёный, если открыто), у блока с адресом
    inline-style нет. Это надёжнее, чем цепляться за конкретный цвет.
    """
    address = ""
    hours = ""
    for block in card.select("div._klarpw"):
        if block.has_attr("style"):
            hours = block.get_text(" ", strip=True)
            continue
        span = block.select_one(_ADDRESS_SIMPLE_SELECTOR) or block.select_one(
            _ADDRESS_MULTI_SELECTOR
        )
        text = span.get_text(" ", strip=True) if span else block.get_text(" ", strip=True)
        address = text.replace(_ZERO_WIDTH_SPACE, "").strip()
    return address, hours


def _cards(soup: BeautifulSoup) -> list[Tag]:
    cards = soup.select(CARD_SELECTOR)
    if cards:
        return cards
    fallback: list[Tag] = []
    for link in soup.find_all("a", href=FIRM_LINK_PATTERN):
        container = link.find_parent("div")
        if container is not None:
            fallback.append(container)
    return fallback


def parse_restaurants(html: str, limit: int = 8) -> list[Restaurant]:
    """Достаёт карточки заведений со страницы поиска."""
    soup = BeautifulSoup(html, "html.parser")

    restaurants: list[Restaurant] = []
    seen: set[str] = set()
    for card in _cards(soup):
        name = _text(card, _NAME_SELECTOR).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        address, hours = _address_and_hours(card)
        restaurants.append(
            Restaurant(
                name=name,
                address=address,
                rating=_rating(card),
                cuisine=_text(card, _CUISINE_SELECTOR),
                working_hours=hours,
                phone=_phone(card),
            )
        )
        if len(restaurants) >= limit:
            break
    return restaurants
