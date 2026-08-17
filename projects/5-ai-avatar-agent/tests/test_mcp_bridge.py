import json

from fastmcp import FastMCP
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
