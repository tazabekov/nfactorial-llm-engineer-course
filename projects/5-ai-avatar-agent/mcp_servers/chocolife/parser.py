"""Разбор каталога акций Chocolife в список предложений.

Функция чистая: на входе HTML, на выходе модели. Это позволяет тестировать
парсер на сохранённой странице, не поднимая браузер.

Селекторы ниже не угаданы, а сняты с живой фикстуры страницы категории
"Рестораны, кафе и бары" (см. tests/fixtures/chocolife_deals.html, снята
вручную через Playwright с https://chocolife.me/restorany-kafe-i-bary/, см.
README рядом). Карточка акции — Angular-компонент <cl-deal>, внутри которого
лежит <div class="deal">; сами данные ищем именно в этом div, а не в
обёртке <cl-deal>, потому что там нет ни одного полезного класса.

Разбор идёт по отрендеренной DOM-разметке карточек (div.deal), а не по
встроенному в SSR-страницу Angular TransferState JSON: на снятой фикстуре
TransferState-блока с данными акций в HTML нет вовсе (проверено — маркер
"TransferState" в фикстуре не встречается), тогда как карточки div.deal
присутствуют и парсятся надёжно. Поэтому DOM-разметка — единственный
проверенно рабочий источник для этой страницы.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from bs4.element import Tag

from mcp_servers.common.models import Deal

# Основной селектор карточки акции в каталоге. Класс "deal" не обфусцирован
# (в отличие от 2ГИС), поэтому используем его напрямую.
CARD_SELECTOR = "div.deal"
# Запасной вариант: если разметка поменяется, ищем ссылки на страницы
# предложений (вида "/58414-coffee-house-grain/" — числовой id + слаг) и
# поднимаемся до ближайшего div-контейнера.
DEAL_LINK_PATTERN = re.compile(r"^/\d+-[\w-]+/?$")

_TITLE_SELECTOR = "h3.deal__title, [class*='deal__title']"
# У .deal__desc два span: первый — название заведения, второй — "· N покупок".
_MERCHANT_SELECTOR = "[class*='deal__desc'] span"
_PRICE_SELECTOR = "[class*='deal__price']"
_PERCENT_SELECTOR = "[class*='deal__percent']"
_LINK_SELECTOR = "a[class*='deal__inner'], a[href]"

_BASE_URL = "https://chocolife.me"


def _number(text: str) -> int | None:
    """Достаёт число из строки вида '9 900 ₸' или 'до -40%'."""
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else None


def _text(node: Tag, selector: str) -> str:
    found = node.select_one(selector)
    return found.get_text(" ", strip=True) if found else ""


def _merchant(card: Tag) -> str:
    """Название заведения — первый span внутри .deal__desc.

    Второй span (если есть) — это "· N покупок", его в название включать
    не нужно.
    """
    spans = card.select(_MERCHANT_SELECTOR)
    return spans[0].get_text(" ", strip=True) if spans else ""


def _url(card: Tag) -> str:
    link = card.select_one(_LINK_SELECTOR)
    if link is None:
        return ""
    href = link.get("href", "")
    if href.startswith("/"):
        return f"{_BASE_URL}{href}"
    return href


def _cards(soup: BeautifulSoup) -> list[Tag]:
    cards = soup.select(CARD_SELECTOR)
    if cards:
        return cards
    fallback: list[Tag] = []
    for link in soup.find_all("a", href=DEAL_LINK_PATTERN):
        container = link.find_parent("div")
        if container is not None:
            fallback.append(container)
    return fallback


def parse_deals(html: str, limit: int = 8) -> list[Deal]:
    """Достаёт карточки акций со страницы каталога Chocolife."""
    soup = BeautifulSoup(html, "html.parser")

    deals: list[Deal] = []
    seen: set[str] = set()
    for card in _cards(soup):
        title = _text(card, _TITLE_SELECTOR).strip()
        if not title or title in seen:
            continue
        seen.add(title)

        # Каталожная карточка показывает только минимальную цену со скидкой
        # ("от 500 ₸") и размер скидки в процентах — исходная цена до скидки
        # в списке не отображается вовсе, она есть только на странице самого
        # предложения. Поэтому original_price всегда None: это честное
        # отсутствие данных, а не пропуск парсинга.
        percent = _number(_text(card, _PERCENT_SELECTOR))

        deals.append(
            Deal(
                title=title,
                restaurant_name=_merchant(card),
                original_price=None,
                discount_price=_number(_text(card, _PRICE_SELECTOR)),
                discount_percent=percent if percent is not None and percent <= 100 else None,
                description="",
                url=_url(card),
            )
        )
        if len(deals) >= limit:
            break
    return deals
