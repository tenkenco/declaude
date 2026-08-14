"""Anonymous landing-page demo: tightly capped, IP-throttled, no account needed."""
import pytest
from conftest import FakeAuth
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.config import Settings


@pytest.fixture
def client(model, usage):
    s = Settings(demo_daily_limit=3, demo_max_chars=500)
    return TestClient(create_app(model=model, auth=FakeAuth(), usage=usage, settings=s))


def test_demo_translates_without_auth(client):
    r = client.post("/v1/demo", json={"text": "Certainly! Let me delve in."})
    assert r.status_code == 200
    assert r.json()["translation"].startswith("PLAIN::")


def test_demo_caps_input_length(client):
    assert client.post("/v1/demo", json={"text": "x" * 501}).status_code == 413


def test_demo_ip_throttle(client):
    for _ in range(3):
        assert client.post("/v1/demo", json={"text": "hi"}).status_code == 200
    r = client.post("/v1/demo", json={"text": "hi"})
    assert r.status_code == 429
    assert "/signin" in r.json()["signup_url"]
