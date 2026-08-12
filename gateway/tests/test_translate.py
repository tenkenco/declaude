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


def test_health_alias_is_public(client):
    """GFE intercepts /healthz on run.app; /health must serve the same payload."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_model_backend_failure_maps_to_503(client, model, monkeypatch):
    """A dead/warming model backend must surface as 503, not a raw 500."""
    async def boom(system, prompt):
        raise RuntimeError("connection refused")
    monkeypatch.setattr(model, "complete", boom)
    r = client.post("/v1/translate", json={"text": "hi"}, headers={"Authorization": "Bearer valid-token"})
    assert r.status_code == 503
    assert r.json()["error"] == "model_unavailable"
