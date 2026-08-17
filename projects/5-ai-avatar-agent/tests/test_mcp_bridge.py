import json

import pytest
from fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from pydantic import BaseModel

from agent import mcp_bridge

echo_server = FastMCP("echo")


class Answer(BaseModel):
    text: str


@echo_server.tool
def say(word: str) -> Answer:
    """Повторяет слово.

    Args:
        word: Что повторить.
    """
    return Answer(text=word * 2)


@echo_server.tool
def boom() -> Answer:
    """Всегда падает."""
    raise ValueError("инструмент сломался")


def test_tool_spec_has_openai_shape():
    class FakeTool:
        name = "say"
        description = "Повторяет слово."
        inputSchema = {"type": "object", "properties": {"word": {"type": "string"}}}

    spec = mcp_bridge.tool_spec_from_mcp("echo", FakeTool())
    assert spec["type"] == "function"
    assert spec["function"]["name"] == "echo__say"
    assert spec["function"]["parameters"]["properties"]["word"]["type"] == "string"


async def test_specs_are_prefixed_by_server_name():
    toolset = mcp_bridge.McpToolset({"echo": echo_server})
    await toolset.open()
    try:
        names = [spec["function"]["name"] for spec in toolset.specs()]
    finally:
        await toolset.close()
    assert "echo__say" in names


async def test_call_returns_json_payload():
    toolset = mcp_bridge.McpToolset({"echo": echo_server})
    await toolset.open()
    try:
        payload = await toolset.call("echo__say", {"word": "ку"})
    finally:
        await toolset.close()
    assert json.loads(payload)["text"] == "куку"


async def test_failing_tool_returns_error_payload_not_exception():
    toolset = mcp_bridge.McpToolset({"echo": echo_server})
    await toolset.open()
    try:
        payload = await toolset.call("echo__boom", {})
    finally:
        await toolset.close()
    assert "error" in json.loads(payload)


async def test_call_log_records_every_invocation():
    toolset = mcp_bridge.McpToolset({"echo": echo_server})
    await toolset.open()
    try:
        await toolset.call("echo__say", {"word": "а"})
    finally:
        await toolset.close()
    assert toolset.call_log[0]["name"] == "echo__say"
    assert toolset.call_log[0]["arguments"] == {"word": "а"}


def test_handles_only_known_prefixes():
    toolset = mcp_bridge.McpToolset({"echo": echo_server})
    assert toolset.handles("echo__say") is True
    assert toolset.handles("analyze_restaurant_photo") is False


async def test_open_cleans_up_on_partial_failure(monkeypatch):
    """Проверяет, что open() закрывает уже открытые клиенты, если произойдёт ошибка.

    Если второй сервер не откроется или list_tools() упадёт, первый сервер должен
    быть закрыт, внутреннее состояние очищено, и можно будет вызвать open() снова.

    Чтобы тест реально доказывал закрытие клиента (а не просто проверял приватное
    состояние, которое можно случайно очистить и без вызова __aexit__), подменяем
    mcp_bridge.Client шпионом, который считает вызовы __aexit__ на каждом созданном
    экземпляре.
    """
    first_server = FastMCP("first")

    @first_server.tool
    def hello() -> Answer:
        """Greeting"""
        return Answer(text="hello")

    second_server = FastMCP("second")

    @second_server.tool
    def fail_to_list() -> Answer:
        """Нельзя даже перечислить этот инструмент."""
        return Answer(text="this tool should never be callable")

    async def failing_list_tools():
        """list_tools() падает для второго сервера."""
        raise RuntimeError(
            "Второй сервер не может предоставить список инструментов"
        )

    second_server.list_tools = failing_list_tools

    # Шпион поверх реального Client: считает, сколько раз вызвали __aexit__
    # у каждого созданного экземпляра, и регистрирует все экземпляры по порядку.
    created_clients: list[mcp_bridge.Client] = []
    real_client_cls = mcp_bridge.Client

    class SpyingClient(real_client_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.aexit_calls = 0
            created_clients.append(self)

        async def __aexit__(self, *args):
            self.aexit_calls += 1
            return await super().__aexit__(*args)

    monkeypatch.setattr(mcp_bridge, "Client", SpyingClient)

    # Создаём toolset с двумя серверами
    toolset = mcp_bridge.McpToolset({"first": first_server, "second": second_server})

    # open() должна выбросить исключение из list_tools()
    with pytest.raises(
        McpError, match="Второй сервер не может предоставить список инструментов"
    ):
        await toolset.open()

    # Оба клиента успели открыться (__aenter__ у второго тоже отрабатывает —
    # падает именно list_tools()), поэтому оба должны быть закрыты в except-блоке.
    assert len(created_clients) == 2
    first_client, second_client = created_clients
    assert first_client.aexit_calls == 1, (
        "клиент первого сервера должен быть закрыт (__aexit__ вызван), "
        "иначе его подпроцесс останется висеть"
    )
    assert second_client.aexit_calls == 1, (
        "клиент второго сервера тоже должен быть закрыт (__aenter__ у него "
        "успел отработать до падения list_tools())"
    )

    # Проверяем, что specs() пуста (нет половинчатых инструментов)
    assert toolset.specs() == [], "specs() должна быть пуста после ошибки open()"

    # Проверяем, что _clients пуста (все клиенты закрыты)
    assert len(toolset._clients) == 0, "_clients должна быть пуста после ошибки open()"

    # После ошибки должно быть безопасно вызвать open() снова без ошибок состояния
    monkeypatch.undo()
    toolset2 = mcp_bridge.McpToolset({"first": first_server})
    await toolset2.open()
    try:
        assert (
            len(toolset2.specs()) > 0
        ), "второй toolset должен иметь specs после успешного open()"
    finally:
        await toolset2.close()
