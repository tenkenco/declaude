"""Clerk auth boundary: every metered endpoint requires a verified bearer token."""
from conftest import AUTH


def test_missing_token_is_401(client):
    r = client.post("/v1/translate", json={"text": "hello"})
    assert r.status_code == 401


def test_garbage_token_is_401(client):
    r = client.post("/v1/translate", json={"text": "hello"}, headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_valid_token_passes(client):
    r = client.post("/v1/translate", json={"text": "hello"}, headers=AUTH)
    assert r.status_code == 200


def test_usage_is_attributed_to_authenticated_user(client, usage):
    client.post("/v1/translate", json={"text": "hello"}, headers=AUTH)
    assert usage.get_sync("user_123") == 1
