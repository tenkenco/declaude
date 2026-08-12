"""Core translation endpoint behavior."""
from conftest import AUTH


def test_translate_returns_plain_english(client, model):
    r = client.post("/v1/translate", json={"text": "You're absolutely right! Great question."}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["translation"] == "PLAIN::You're absolutely right! Great question."
    assert body["model"]  # reports which model served it


def test_translate_sends_declaudify_system_prompt(client, model):
    client.post("/v1/translate", json={"text": "hi"}, headers=AUTH)
    assert len(model.calls) == 1
    sys_prompt = model.calls[0]["system"].lower()
    # The system prompt must instruct removal of Claude-isms, not summarization.
    assert "rewrite" in sys_prompt or "translate" in sys_prompt
    assert "meaning" in sys_prompt


def test_translate_rejects_empty_text(client):
    r = client.post("/v1/translate", json={"text": "   "}, headers=AUTH)
    assert r.status_code == 422


def test_translate_rejects_oversized_text(client, settings):
    r = client.post("/v1/translate", json={"text": "x" * 60_000}, headers=AUTH)
    assert r.status_code == 422


def test_healthz_is_public(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
