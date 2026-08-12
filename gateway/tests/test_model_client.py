"""OpenAICompatClient request shaping: bounded generation for tail-latency control."""
import httpx
import pytest

from declaude.model import OpenAICompatClient


@pytest.fixture
def captured():
    return {}


@pytest.fixture
def client(captured, monkeypatch):
    c = OpenAICompatClient(base_url="http://model.test/v1", model="m")

    async def fake_post(url, json=None, **kw):
        captured["url"], captured["json"] = url, json
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]},
                              request=httpx.Request("POST", url))
    monkeypatch.setattr(c._client, "post", fake_post)
    return c


async def test_max_tokens_scales_with_input(client, captured):
    await client.complete("sys", "x" * 400)  # ~100 tokens of input
    mt = captured["json"]["max_tokens"]
    # translation output ~= input length; allow 2x headroom, floor of 256
    assert 256 <= mt <= 1024


async def test_max_tokens_capped_for_huge_input(client, captured):
    await client.complete("sys", "x" * 200_000)
    assert captured["json"]["max_tokens"] <= 8192


async def test_max_tokens_floor_for_tiny_input(client, captured):
    await client.complete("sys", "hi")
    assert captured["json"]["max_tokens"] >= 256
