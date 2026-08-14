"""Review finding: the paid flag must actually flip when a customer pays."""
import pytest
from conftest import FakeAuth
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.config import Settings

BH = {"Authorization": "Bearer valid-token"}


@pytest.fixture
def client(model, usage):
    s = Settings(free_tier_monthly_limit=1, stripe_payment_link="https://buy.stripe.com/x")
    return TestClient(create_app(model=model, auth=FakeAuth(), usage=usage, settings=s))


def test_402_upgrade_url_carries_user_reference(client):
    client.post("/v1/translate", json={"text": "a"}, headers=BH)
    r = client.post("/v1/translate", json={"text": "b"}, headers=BH)
    assert r.status_code == 402
    assert r.json()["upgrade_url"].endswith("/upgrade?ref=user_123")


def test_upgrade_redirect_appends_client_reference(client):
    r = client.get("/upgrade", params={"ref": "user_123"}, follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "https://buy.stripe.com/x?client_reference_id=user_123"


def test_upgrade_without_ref_still_redirects(client):
    r = client.get("/upgrade", follow_redirects=False)
    assert r.headers["location"] == "https://buy.stripe.com/x"


# --- Stripe Link autofills a saved browser email; prefill the real account email instead ---

def test_upgrade_prefills_email(client):
    r = client.get("/upgrade", params={"ref": "user_123", "email": "a@b.co"}, follow_redirects=False)
    loc = r.headers["location"]
    assert "client_reference_id=user_123" in loc
    assert "prefilled_email=a%40b.co" in loc


def test_upgrade_rejects_bogus_email(client):
    r = client.get("/upgrade", params={"ref": "user_123", "email": "not an email"},
                   follow_redirects=False)
    assert "prefilled_email" not in r.headers["location"]
    assert "client_reference_id=user_123" in r.headers["location"]


def test_upgrade_email_cannot_inject_params(client):
    r = client.get("/upgrade", params={"ref": "user_123", "email": "a@b.co&utm=evil"},
                   follow_redirects=False)
    assert "utm=evil" not in r.headers["location"]
