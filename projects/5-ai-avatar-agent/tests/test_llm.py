import json

from agent import llm, skills


class FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.type = "function"
        self.function = type("F", (), {"name": name, "arguments": json.dumps(arguments)})()


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self):
        return {"role": "assistant", "content": self.content}


class FakeCompletions:
    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        message = self._script.pop(0)

        class Result:
            choices = [type("C", (), {"message": message})()]

        return Result()


class FakeClient:
    def __init__(self, script):
        self.completions = FakeCompletions(script)
        self.chat = type("Chat", (), {"completions": self.completions})()


class FakeToolset:
    def __init__(self):
        self.call_log = []
        self.calls = []

    def specs(self):
        return [{"type": "function", "function": {"name": "twogis__search_restaurants",
                                                  "description": "", "parameters": {}}}]

    def handles(self, name):
        return name.startswith("twogis__")

    async def call(self, name, arguments):
        self.calls.append((name, arguments))
        self.call_log.append({"name": name, "arguments": arguments, "result_size": 1})
        return json.dumps({"results": [{"name": "Бочка"}]}, ensure_ascii=False)


async def test_plain_answer_without_tools():
    client = FakeClient([FakeMessage(content="Привет")])
    answer, history, log = await llm.run_turn(
        client, FakeToolset(), [], llm.build_user_message("привет", None)
    )
    assert answer == "Привет"
    last = history[-1]
    content = last["content"] if isinstance(last, dict) else last.content
    assert content == "Привет"
    assert log == []


async def test_tool_call_is_executed_and_answered():
    toolset = FakeToolset()
    client = FakeClient([
        FakeMessage(tool_calls=[FakeToolCall("c1", "twogis__search_restaurants", {"query": "суши"})]),
        FakeMessage(content="Рекомендую Бочку"),
    ])
    answer, history, log = await llm.run_turn(
        client, toolset, [], llm.build_user_message("где поесть", None)
    )
    assert answer == "Рекомендую Бочку"
    assert toolset.calls == [("twogis__search_restaurants", {"query": "суши"})]
    assert log[0]["name"] == "twogis__search_restaurants"
    tool_messages = [m for m in history if isinstance(m, dict) and m.get("role") == "tool"]
    assert tool_messages[0]["tool_call_id"] == "c1"


async def test_every_call_in_batch_gets_a_reply():
    toolset = FakeToolset()
    batch = [
        FakeToolCall("a", "twogis__search_restaurants", {"query": "1"}),
        FakeToolCall("b", "twogis__search_restaurants", {"query": "2"}),
    ]
    client = FakeClient([FakeMessage(tool_calls=batch), FakeMessage(content="готово")])
    _, history, _ = await llm.run_turn(
        client, toolset, [], llm.build_user_message("вопрос", None)
    )
    ids = [m["tool_call_id"] for m in history if isinstance(m, dict) and m.get("role") == "tool"]
    assert ids == ["a", "b"]


async def test_iteration_cap_stops_the_loop(monkeypatch):
    monkeypatch.setattr(llm, "MAX_TOOL_CALLS", 2)
    toolset = FakeToolset()
    endless = [
        FakeMessage(tool_calls=[FakeToolCall(str(i), "twogis__search_restaurants", {"query": "x"})])
        for i in range(5)
    ]
    client = FakeClient(endless)
    answer, _, _ = await llm.run_turn(
        client, toolset, [], llm.build_user_message("вопрос", None)
    )
    assert answer == llm.CAP_REACHED_MESSAGE
    assert len(toolset.calls) == 2


async def test_malformed_arguments_do_not_crash():
    toolset = FakeToolset()
    bad = FakeToolCall("c1", "twogis__search_restaurants", {})
    bad.function.arguments = "{не json"
    client = FakeClient([FakeMessage(tool_calls=[bad]), FakeMessage(content="ладно")])
    answer, history, _ = await llm.run_turn(
        client, toolset, [], llm.build_user_message("вопрос", None)
    )
    assert answer == "ладно"
    tool_messages = [m for m in history if isinstance(m, dict) and m.get("role") == "tool"]
    assert "error" in tool_messages[0]["content"]


async def test_cap_reached_history_has_no_dangling_tool_calls(monkeypatch):
    """Дефект 1: после срабатывания лимита в истории не должно оставаться
    assistant-сообщения с tool_calls без ответа на каждый call_id — иначе
    следующий run_turn, получив такую историю, будет отклонён API."""
    monkeypatch.setattr(llm, "MAX_TOOL_CALLS", 2)
    toolset = FakeToolset()
    endless = [
        FakeMessage(tool_calls=[FakeToolCall(str(i), "twogis__search_restaurants", {"query": "x"})])
        for i in range(5)
    ]
    client = FakeClient(endless)
    answer, history, _ = await llm.run_turn(
        client, toolset, [], llm.build_user_message("вопрос", None)
    )
    assert answer == llm.CAP_REACHED_MESSAGE

    answered_ids = {
        m["tool_call_id"] for m in history if isinstance(m, dict) and m.get("role") == "tool"
    }
    for message in history:
        tool_calls = message.get("tool_calls") if isinstance(message, dict) else message.tool_calls
        if not tool_calls:
            continue
        for call in tool_calls:
            call_id = call["id"] if isinstance(call, dict) else call.id
            assert call_id in answered_ids, (
                f"assistant tool_call {call_id} остался без ответа в истории"
            )


class FakeVisionCompletions:
    """Заглушка client.chat.completions.parse для vision-вызова skill'а."""

    def __init__(self, verdict):
        self._verdict = verdict

    async def parse(self, **kwargs):
        message = type("M", (), {"parsed": self._verdict, "refusal": None})()

        class Result:
            choices = [type("C", (), {"message": message})()]

        return Result()


class FakeClientWithVision(FakeClient):
    """FakeClient, который умеет и chat.completions.create (агентский цикл),
    и chat.completions.parse (внутри analyze_restaurant_photo)."""

    def __init__(self, script, verdict):
        super().__init__(script)
        self.completions.parse = FakeVisionCompletions(verdict).parse


async def test_local_skill_call_is_logged(tmp_path):
    """Дефект 2: вызов локального skill analyze_restaurant_photo должен
    попасть в возвращаемый call_log так же, как MCP-вызовы."""
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0test")
    verdict = skills.RestaurantVerdict(
        level="casual", status="семейный", description="ок", confidence=0.5
    )
    toolset = FakeToolset()
    client = FakeClientWithVision(
        [
            FakeMessage(
                tool_calls=[
                    FakeToolCall("c1", "analyze_restaurant_photo", {"image_path": str(image)})
                ]
            ),
            FakeMessage(content="Похоже на casual"),
        ],
        verdict,
    )
    _, _, log = await llm.run_turn(
        client, toolset, [], llm.build_user_message("что скажешь по фото", str(image))
    )
    assert any(entry["name"] == "analyze_restaurant_photo" for entry in log)


def test_trim_history_keeps_last_messages():
    messages = [{"role": "user", "content": str(i)} for i in range(30)]
    trimmed = llm.trim_history(messages, limit=10)
    assert len(trimmed) == 10
    assert trimmed[-1]["content"] == "29"


def test_build_user_message_with_image(tmp_path):
    image = tmp_path / "p.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0")
    message = llm.build_user_message("что это", str(image))
    kinds = [part["type"] for part in message["content"]]
    assert "image_url" in kinds
