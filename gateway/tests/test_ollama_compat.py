"""Ollama-compatible /api/chat + long-lived API keys, so the claudish-to-english
plugin can point CLAUDISH_OLLAMA at the hosted gateway (Basic auth via URL userinfo)."""
import base64

import pytest
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.keys import hash_key


class FakeAuth:
    async def verify(self, token: str) -> str:
        if token == "valid-token":
            return "user_123"
        raise ValueError("bad token")


@pytest.fixture
def client(model, usage, settings):
    app = create_app(model=model, auth=FakeAuth(), usage=usage, settings=settings)
    return TestClient(app)


@pytest.fixture
def api_key(usage):
    key = "dk_testkey123"
    usage.add_api_key_sync(hash_key(key), "user_777")
    return key


def basic(key):  # curl https://x:KEY@host sends this
    return {"Authorization": "Basic " + base64.b64encode(f"x:{key}".encode()).decode()}


def ollama_req(text="Great question! This is robust."):
    return {
        "model": "qwen2.5-14b-instruct", "stream": False, "think": False,
        "options": {"temperature": 0.3},
        "messages": [{"role": "system", "content": "rewrite simply"},
                     {"role": "user", "content": text}],
    }


def test_api_chat_with_api_key_basic_auth(client, api_key, model):
    r = client.post("/api/chat", json=ollama_req(), headers=basic(api_key))
    assert r.status_code == 200
    body = r.json()
    assert body["message"]["role"] == "assistant"
    assert body["message"]["content"] == "PLAIN::Great question! This is robust."
    assert body["done"] is True


def test_api_chat_uses_caller_system_prompt(client, api_key, model):
    client.post("/api/chat", json=ollama_req(), headers=basic(api_key))
    assert model.calls[-1]["system"] == "rewrite simply"


def test_api_chat_with_bearer_still_works(client):
    r = client.post("/api/chat", json=ollama_req(), headers={"Authorization": "Bearer valid-token"})
    assert r.status_code == 200


def test_api_chat_rejects_unknown_key(client):
    r = client.post("/api/chat", json=ollama_req(), headers=basic("dk_wrong"))
    assert r.status_code == 401


def test_api_chat_no_auth_gets_ollama_style_error(client):
    r = client.post("/api/chat", json=ollama_req())
    assert r.status_code == 401
    assert "error" in r.json()  # plugin fails open on .error


def test_api_chat_quota_exhaustion_is_ollama_style_error(client, api_key, usage, settings):
    for _ in range(settings.free_tier_monthly_limit):
        client.post("/api/chat", json=ollama_req(), headers=basic(api_key))
    r = client.post("/api/chat", json=ollama_req(), headers=basic(api_key))
    assert r.status_code == 402
    assert "error" in r.json()


def test_api_chat_counts_against_same_quota(client, api_key, usage):
    client.post("/api/chat", json=ollama_req(), headers=basic(api_key))
    assert usage.get_sync("user_777") == 1


def test_api_key_also_works_on_translate(client, api_key):
    r = client.post("/v1/translate", json={"text": "hello there"}, headers=basic(api_key))
    assert r.status_code == 200


def test_hash_key_is_stable_and_not_identity():
    assert hash_key("dk_x") == hash_key("dk_x")
    assert hash_key("dk_x") != "dk_x"
