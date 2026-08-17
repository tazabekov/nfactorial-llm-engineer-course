from fastmcp import Client

from config import FIXTURES_DIR
from mcp_servers.chocolife import parser, server


def _html() -> str:
    return (FIXTURES_DIR / "chocolife_deals.html").read_text(encoding="utf-8")


def test_parses_at_least_three_deals():
    assert len(parser.parse_deals(_html())) >= 3


def test_every_deal_has_title():
    for deal in parser.parse_deals(_html()):
        assert deal.title.strip()


def test_prices_are_integers_or_none():
    for deal in parser.parse_deals(_html()):
        assert deal.discount_price is None or isinstance(deal.discount_price, int)


def test_empty_html_gives_empty_list():
    assert parser.parse_deals("<html></html>") == []


async def test_server_exposes_search_deals():
    async with Client(server.mcp) as client:
        names = [tool.name for tool in await client.list_tools()]
    assert "search_deals" in names


async def test_offline_mode_returns_deals(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", True)
    async with Client(server.mcp) as client:
        result = await client.call_tool("search_deals", {"category": "рестораны"})
    assert result.data.error == ""
    assert len(result.data.results) >= 3


async def test_fetch_failure_yields_error(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", False)

    async def broken_fetch(url, selector):
        raise RuntimeError("chocolife лежит")

    monkeypatch.setattr(server.POOL, "fetch_html", broken_fetch)
    async with Client(server.mcp) as client:
        result = await client.call_tool("search_deals", {"category": "уникальное"})
    assert result.data.results == []
    assert "лежит" in result.data.error


async def test_offline_cache_does_not_leak_into_live_mode(monkeypatch):
    category = "уникальная-категория-неймспейс"

    # Сначала кладём результат в кэш в офлайн-режиме.
    monkeypatch.setattr(server, "OFFLINE", True)
    async with Client(server.mcp) as client:
        offline_result = await client.call_tool("search_deals", {"category": category})
    assert offline_result.data.cached is False

    # Переключаемся в боевой режим и убеждаемся, что данные из офлайн-кэша
    # не отдаются: инструмент реально идёт за данными через fetch_html.
    monkeypatch.setattr(server, "OFFLINE", False)
    calls = []

    async def fake_fetch(url, selector):
        calls.append(url)
        return _html()

    monkeypatch.setattr(server.POOL, "fetch_html", fake_fetch)
    async with Client(server.mcp) as client:
        live_result = await client.call_tool("search_deals", {"category": category})

    assert len(calls) == 1
    assert live_result.data.cached is False


async def test_parser_exception_is_caught_and_reported_as_error(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", True)

    def broken_parser(html, limit):
        raise ValueError("неожиданная разметка")

    monkeypatch.setattr(server, "parse_deals", broken_parser)
    async with Client(server.mcp) as client:
        result = await client.call_tool(
            "search_deals", {"category": "запрос-с-битым-парсером"}
        )
    assert result.data.results == []
    assert "неожиданная разметка" in result.data.error
