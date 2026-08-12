"""Long-lived API keys: minted from a session, then valid on their own."""
from conftest import AUTH, FakeAuth
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.keys import (
    InMemoryApiKeyStore,
    generate_key,
    hash_key,
    looks_like_api_key,
)


def test_generated_keys_are_unique_and_prefixed():
    a, b = generate_key(), generate_key()
    assert a != b
    assert looks_like_api_key(a)
    assert len(a) > 32


def test_hash_is_stable_and_not_the_key():
    key = generate_key()
    assert hash_key(key) == hash_key(key)
    assert key not in hash_key(key)


async def test_store_roundtrip_and_revoke():
    store = InMemoryApiKeyStore()
    key = generate_key()
    await store.add(hash_key(key), "user_123")
    assert await store.lookup(hash_key(key)) == "user_123"
    await store.revoke(hash_key(key))
    assert await store.lookup(hash_key(key)) is None


def test_mint_requires_authentication(client):
    assert client.post("/v1/keys").status_code == 401


def test_mint_returns_a_key(client):
    r = client.post("/v1/keys", headers=AUTH)
    assert r.status_code == 200
    assert looks_like_api_key(r.json()["key"])


def test_minted_key_authenticates_translate(client):
    key = client.post("/v1/keys", headers=AUTH).json()["key"]
    r = client.post("/v1/translate", json={"text": "Certainly!"}, headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 200
    assert r.json()["translation"] == "PLAIN::Certainly!"


def test_key_shares_the_quota_of_the_user_who_minted_it(client, usage):
    key = client.post("/v1/keys", headers=AUTH).json()["key"]
    client.post("/v1/translate", json={"text": "hi"}, headers={"Authorization": f"Bearer {key}"})
    assert usage.get_sync("user_123") == 1


def test_minted_key_authenticates_mcp(client):
    key = client.post("/v1/keys", headers=AUTH).json()["key"]
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "translate", "arguments": {"text": "Certainly!"}}},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    assert r.json()["result"]["content"][0]["text"] == "PLAIN::Certainly!"


def test_unknown_key_is_rejected(client):
    r = client.post("/v1/translate", json={"text": "hi"}, headers={"Authorization": "Bearer dc_nope"})
    assert r.status_code == 401


def test_api_key_cannot_mint_another_key(client):
    """A leaked key must not be able to mint replacements for itself."""
    key = client.post("/v1/keys", headers=AUTH).json()["key"]
    r = client.post("/v1/keys", headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 403


def test_key_is_not_stored_in_plain_text(client, api_keys):
    key = client.post("/v1/keys", headers=AUTH).json()["key"]
    assert key not in api_keys._keys
    assert hash_key(key) in api_keys._keys


def test_keys_endpoint_reports_503_when_unconfigured(model, usage, settings):
    """A wiring mistake must be visible, not a silent 500."""
    app = create_app(model=model, auth=FakeAuth(), usage=usage, settings=settings)
    assert TestClient(app).post("/v1/keys", headers=AUTH).status_code == 503
