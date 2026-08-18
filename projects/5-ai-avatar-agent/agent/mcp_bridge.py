"""Мост между MCP-серверами и function calling OpenAI.

Здесь и только здесь мы знаем, что часть инструментов живёт в чужих процессах.
Для LLM все инструменты выглядят одинаково.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

from fastmcp import Client

SEPARATOR = "__"


def tool_spec_from_mcp(server_name: str, tool: Any) -> dict:
    """Превращает описание MCP-инструмента в спецификацию функции OpenAI."""
    # Имя поля со схемой отличается между версиями MCP SDK — проверяем оба.
    schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None) or {}
    return {
        "type": "function",
        "function": {
            "name": f"{server_name}{SEPARATOR}{tool.name}",
            "description": (tool.description or "").strip(),
            "parameters": schema or {"type": "object", "properties": {}},
        },
    }


def _to_jsonable(value: Any) -> Any:
    """Приводит результат вызова инструмента к обычным dict/list/скалярам.

    ``result.data`` у fastmcp 3.4.7 — это не словарь, а «гидратированный»
    объект (динамический pydantic-dataclass, собранный из output-схемы
    инструмента), у него нет ``.get``/``.model_dump``, только доступ по
    атрибутам. Если сериализовать его как есть через ``json.dumps(...,
    default=str)``, в лог утечёт repr объекта вместо реальных полей —
    агент получит бесполезную строку вместо ресторанов/акций. Поэтому
    рекурсивно разворачиваем dataclass-подобные и pydantic-объекты в
    обычные структуры данных.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _to_jsonable(value.model_dump())
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _to_jsonable(dataclasses.asdict(value))
    return value


class McpToolset:
    """Держит клиентов к нескольким MCP-серверам и разруливает вызовы по имени.

    Ключи словаря — короткие имена серверов, значения — либо путь к server.py
    (тогда сервер поднимается отдельным процессом), либо объект FastMCP
    (тогда соединение in-memory, это используется в тестах).
    """

    def __init__(self, servers: dict[str, Any]) -> None:
        self._servers = servers
        self._clients: dict[str, Client] = {}
        self._specs: list[dict] = []
        self.call_log: list[dict] = []

    async def open(self) -> None:
        """Поднимает серверы и собирает список их инструментов.

        При частичном сбое (если один из серверов не открыть или list_tools() упадёт)
        закрывает уже открытые клиенты, очищает внутреннее состояние и пробрасывает
        исключение. После этого можно снова вызвать open().
        """
        opened_clients: dict[str, Client] = {}
        try:
            for name, target in self._servers.items():
                client = Client(target)
                await client.__aenter__()
                opened_clients[name] = client
                self._clients[name] = client
                for tool in await client.list_tools():
                    self._specs.append(tool_spec_from_mcp(name, tool))
        except Exception:
            # Закрываем все уже открытые клиенты в best-effort режиме
            for name, client in opened_clients.items():
                try:
                    await client.__aexit__(None, None, None)
                except Exception:
                    # Игнорируем ошибки при закрытии, чтобы не скрыть исходное исключение
                    pass
            # Возвращаем состояние в то же, что было до попытки открыть
            self._clients.clear()
            self._specs.clear()
            raise

    async def close(self) -> None:
        for client in self._clients.values():
            await client.__aexit__(None, None, None)
        self._clients.clear()
        self._specs.clear()

    def specs(self) -> list[dict]:
        return list(self._specs)

    def handles(self, name: str) -> bool:
        server_name = name.split(SEPARATOR)[0]
        return server_name in self._servers

    async def call(self, name: str, arguments: dict) -> str:
        """Вызывает инструмент и возвращает JSON-строку для сообщения роли tool."""
        server_name, _, tool_name = name.partition(SEPARATOR)
        client = self._clients.get(server_name)
        entry: dict[str, Any] = {"name": name, "arguments": arguments}
        if client is None:
            entry["error"] = "сервер не подключён"
            self.call_log.append(entry)
            return json.dumps({"error": f"MCP-сервер {server_name} не подключён"}, ensure_ascii=False)

        try:
            result = await client.call_tool(tool_name, arguments, raise_on_error=False)
        except Exception as error:  # noqa: BLE001 — падение сервера не должно ронять диалог
            entry["error"] = str(error)
            self.call_log.append(entry)
            return json.dumps({"error": f"Вызов {name} не удался: {error}"}, ensure_ascii=False)

        if result.is_error:
            text = result.content[0].text if result.content else "неизвестная ошибка"
            entry["error"] = text
            self.call_log.append(entry)
            return json.dumps({"error": text}, ensure_ascii=False)

        # structured_content уже приходит от fastmcp обычным словарём (он
        # строится раньше, чем .data, и именно из него .data валидируется),
        # поэтому это самый надёжный источник. .data используем только как
        # запасной вариант и прогоняем через _to_jsonable, потому что это
        # не словарь, а объект с доступом по атрибутам.
        payload = result.structured_content
        if payload is None and result.data is not None:
            payload = _to_jsonable(result.data)
        if payload is None:
            payload = {"text": result.content[0].text if result.content else ""}

        if isinstance(payload, dict) and isinstance(payload.get("results"), list):
            entry["result_size"] = len(payload["results"])
        elif isinstance(payload, list):
            entry["result_size"] = len(payload)
        else:
            entry["result_size"] = 1 if payload else 0
        self.call_log.append(entry)
        return json.dumps(payload, ensure_ascii=False, default=str)
