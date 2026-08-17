import base64

import pytest

from agent import skills


class FakeParsed:
    def __init__(self, verdict):
        self.parsed = verdict
        self.refusal = None


class FakeCompletions:
    def __init__(self, verdict):
        self._verdict = verdict
        self.last_kwargs = None

    async def parse(self, **kwargs):
        self.last_kwargs = kwargs

        class Result:
            choices = [type("C", (), {"message": FakeParsed(self._verdict)})()]

        return Result()


class FakeClient:
    def __init__(self, verdict):
        self.chat = type("Chat", (), {"completions": FakeCompletions(verdict)})()


def test_tool_spec_declares_image_path():
    spec = skills.ANALYZE_TOOL_SPEC
    assert spec["function"]["name"] == "analyze_restaurant_photo"
    assert "image_path" in spec["function"]["parameters"]["properties"]


def test_encode_image_returns_base64(tmp_path):
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0test")
    encoded = skills.encode_image(str(image))
    assert base64.b64decode(encoded) == b"\xff\xd8\xff\xe0test"


async def test_analyze_returns_dict_with_all_fields(tmp_path):
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0test")
    verdict = skills.RestaurantVerdict(
        level="mid-range", status="романтический", description="Уютно", confidence=0.8
    )
    client = FakeClient(verdict)
    result = await skills.analyze_restaurant_photo(str(image), client)
    assert result == {
        "level": "mid-range",
        "status": "романтический",
        "description": "Уютно",
        "confidence": 0.8,
    }


async def test_analyze_uses_detail_low(tmp_path):
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0test")
    verdict = skills.RestaurantVerdict(
        level="casual", status="семейный", description="ок", confidence=0.5
    )
    client = FakeClient(verdict)
    await skills.analyze_restaurant_photo(str(image), client)
    content = client.chat.completions.last_kwargs["messages"][0]["content"]
    image_part = [part for part in content if part["type"] == "image_url"][0]
    assert image_part["image_url"]["detail"] == "low"


async def test_missing_file_returns_error_dict():
    result = await skills.analyze_restaurant_photo("/нет/такого.jpg", FakeClient(None))
    assert "error" in result
