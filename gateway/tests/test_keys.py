"""API key lifecycle: mint with metadata, list, revoke."""
import pytest
from conftest import FakeAuth
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.config import Settings

SH = {"Authorization": "Bearer valid-token"}


@pytest.fixture
def client(model, usage):
    return TestClient(create_app(model=model, auth=FakeAuth(), usage=usage, settings=Settings()))


def test_mint_returns_key_once_and_lists_metadata(client):
    k = client.post("/v1/keys", headers=SH).json()["key"]
    listed = client.get("/v1/keys", headers=SH).json()["keys"]
    assert len(listed) == 1
    item = listed[0]
    assert item["prefix"] == k[:7] + "…" + k[-4:]
    assert k not in str(listed)          # plaintext never comes back
    assert item["id"] and item["created_at"]


def test_delete_revokes_key(client):
    k = client.post("/v1/keys", headers=SH).json()["key"]
    kid = client.get("/v1/keys", headers=SH).json()["keys"][0]["id"]
    # key works before revocation
    ok = client.post("/v1/translate", json={"text": "hi"}, headers={"Authorization": f"Bearer {k}"})
    assert ok.status_code == 200
    assert client.delete(f"/v1/keys/{kid}", headers=SH).status_code == 204
    assert client.get("/v1/keys", headers=SH).json()["keys"] == []
    gone = client.post("/v1/translate", json={"text": "hi"}, headers={"Authorization": f"Bearer {k}"})
    assert gone.status_code == 401


def test_cannot_delete_someone_elses_key(client, usage):
    import anyio
    anyio.run(usage.add_api_key, "otherhash", "user_other")
    r = client.delete("/v1/keys/otherhash", headers=SH)
    assert r.status_code == 404


def test_list_requires_session(client):
    assert client.get("/v1/keys").status_code == 401
