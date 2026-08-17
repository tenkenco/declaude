"""OpenAI-compatible /v1/chat/completions.

Exists so clients can authenticate with a header instead of stuffing the token into a URL.
The Ollama-compatible surface has no auth header, which forced `https://x:$TOKEN@host` basic
auth — and a URL carrying a credential leaks the moment anything prints it (found in
gvzdv/claudish-to-english, where the unreachable-host notice interpolates the endpoint).
"""
from conftest import AUTH


def body(text="Great question! It is worth noting that this works.", **kw):
    return {"model": "declaude", "messages": [{"role": "user", "content": text}], **kw}


def test_returns_openai_shaped_response(client, model):
    r = client.post("/v1/chat/completions", json=body(), headers=AUTH)
    assert r.status_code == 200
    d = r.json()
    assert d["object"] == "chat.completion"
    assert d["choices"][0]["message"]["role"] == "assistant"
    assert d["choices"][0]["message"]["content"].startswith("PLAIN::")
    assert d["choices"][0]["finish_reason"] == "stop", "clients discard rewrites cut short by a cap"
    assert d["choices"][0]["index"] == 0
    assert d["model"]


def test_authenticates_by_header_without_credentials_in_the_url(client, model):
    """The whole point: a Bearer header, so no token ends up in a URL that might get printed."""
    r = client.post("/v1/chat/completions", json=body(), headers={"Authorization": "Bearer valid-token"})
    assert r.status_code == 200


def test_rejects_missing_credentials(client):
    assert client.post("/v1/chat/completions", json=body()).status_code == 401


def test_uses_the_declaude_prompt_when_the_client_sends_none(client, model):
    client.post("/v1/chat/completions", json=body(), headers=AUTH)
    assert "plain, natural English" in model.calls[0]["system"]


def test_honors_a_client_supplied_system_message(client, model):
    client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "system", "content": "CUSTOM"}, {"role": "user", "content": "hi"}]},
        headers=AUTH,
    )
    assert model.calls[0]["system"] == "CUSTOM"


def test_rewrites_the_last_user_message(client, model):
    client.post(
        "/v1/chat/completions",
        json={"messages": [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ignored"},
            {"role": "user", "content": "second"},
        ]},
        headers=AUTH,
    )
    assert model.calls[0]["prompt"] == "second"


def test_rejects_a_request_with_no_user_message(client):
    r = client.post("/v1/chat/completions", json={"messages": [{"role": "system", "content": "x"}]}, headers=AUTH)
    assert r.status_code == 422


def test_rejects_oversized_input(client, settings):
    r = client.post("/v1/chat/completions", json=body("x" * 60_000), headers=AUTH)
    assert r.status_code == 422


def test_counts_against_the_same_quota(client, usage, settings):
    client.post("/v1/chat/completions", json=body(), headers=AUTH)
    assert usage.get_sync("user_123") == 1


def test_ceiling_applies(client, settings):
    for _ in range(settings.free_tier_monthly_limit):
        client.post("/v1/chat/completions", json=body(), headers=AUTH)
    assert client.post("/v1/chat/completions", json=body(), headers=AUTH).status_code == 402


def test_model_failure_is_503_not_500(client, model, monkeypatch):
    async def boom(system, prompt):
        raise RuntimeError("backend down")

    monkeypatch.setattr(model, "complete", boom)
    assert client.post("/v1/chat/completions", json=body(), headers=AUTH).status_code == 503
