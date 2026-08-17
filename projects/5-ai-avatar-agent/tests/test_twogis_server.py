from fastmcp import Client

from mcp_servers.twogis import server


async def test_tool_is_exposed_with_expected_name():
    async with Client(server.mcp) as client:
        names = [tool.name for tool in await client.list_tools()]
    assert "search_restaurants" in names


async def test_offline_mode_returns_results_from_fixture(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", True)
    async with Client(server.mcp) as client:
        result = await client.call_tool("search_restaurants", {"query": "рестораны-офлайн-тест"})
    assert result.data.error == ""
    assert len(result.data.results) >= 3


async def test_cache_prevents_second_fetch(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", False)
    calls = []

    async def fake_fetch(url, selector, cookies=None):
        calls.append(url)
        return (server.FIXTURES_DIR / "twogis_search.html").read_text(encoding="utf-8")

    monkeypatch.setattr(server.POOL, "fetch_html", fake_fetch)
    async with Client(server.mcp) as client:
        first = await client.call_tool("search_restaurants", {"query": "уник-запрос-кэш"})
        second = await client.call_tool("search_restaurants", {"query": "уник-запрос-кэш"})
    assert len(calls) == 1
    assert first.data.cached is False
    assert second.data.cached is True


async def test_parser_failure_yields_error_and_no_results(monkeypatch):
    monkeypatch.setattr(server, "OFFLINE", False)

    async def broken_fetch(url, selector, cookies=None):
        raise RuntimeError("сайт недоступен")

    monkeypatch.setattr(server.POOL, "fetch_html", broken_fetch)
    async with Client(server.mcp) as client:
        result = await client.call_tool("search_restaurants", {"query": "что-то новое"})
    assert result.data.results == []
    assert "недоступен" in result.data.error
