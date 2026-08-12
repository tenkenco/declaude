"""Key minting: POST /v1/keys requires a Clerk session; API keys cannot mint keys."""
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


def test_mint_key_with_clerk_session(client, usage):
    r = client.post("/v1/keys", headers={"Authorization": "Bearer valid-token"})
    assert r.status_code == 200
    key = r.json()["key"]
    assert key.startswith("dk_")
    # key is registered and usable
    r2 = client.post("/v1/translate", json={"text": "hello"}, headers={"Authorization": f"Bearer {key}"})
    assert r2.status_code == 200


def test_api_key_cannot_mint_another_key(client, usage):
    usage.add_api_key_sync(hash_key("dk_existing"), "user_123")
    r = client.post("/v1/keys", headers={"Authorization": "Bearer dk_existing"})
    assert r.status_code == 403


def test_basic_auth_cannot_mint(client, usage):
    usage.add_api_key_sync(hash_key("dk_existing"), "user_123")
    h = {"Authorization": "Basic " + base64.b64encode(b"x:dk_existing").decode()}
    r = client.post("/v1/keys", headers=h)
    assert r.status_code == 403


def test_mint_requires_auth(client):
    assert client.post("/v1/keys").status_code == 401


def test_plaintext_key_is_never_stored(client, usage):
    key = client.post("/v1/keys", headers={"Authorization": "Bearer valid-token"}).json()["key"]
    assert key not in str(usage._keys)  # only the hash lands in the store
