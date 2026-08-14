"""A paying customer must be able to cancel from inside the product."""
import pytest
from conftest import FakeAuth
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.config import Settings

SH = {"Authorization": "Bearer valid-token"}


@pytest.fixture
def client(model, usage, monkeypatch):
    monkeypatch.setattr("declaude.app.create_portal_session",
                        lambda cid, return_url: f"https://billing.stripe.com/p/{cid}")
    s = Settings(clerk_publishable_key="pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk",
                 stripe_payment_link="https://buy.stripe.com/x")
    return TestClient(create_app(model=model, auth=FakeAuth(), usage=usage, settings=s))


def test_webhook_stores_the_stripe_customer(model, usage, monkeypatch):
    monkeypatch.setattr("declaude.billing.create_portal_session", lambda c, r: "https://x")
    app = create_app(model=model, auth=FakeAuth(), usage=usage, settings=Settings(),
                     webhook_verifier=lambda p, s: {
                         "type": "checkout.session.completed",
                         "data": {"object": {"client_reference_id": "user_123",
                                             "customer": "cus_abc"}}})
    r = TestClient(app).post("/v1/billing/webhook", content=b"{}", headers={"Stripe-Signature": "x"})
    assert r.status_code == 200
    import anyio
    assert anyio.run(usage.get_stripe_customer, "user_123") == "cus_abc"


def test_portal_session_for_paying_customer(client, usage):
    import anyio
    anyio.run(usage.set_paid, "user_123", True)
    anyio.run(usage.set_stripe_customer, "user_123", "cus_abc")
    r = client.post("/v1/billing/portal", headers=SH)
    assert r.status_code == 200
    assert r.json()["url"] == "https://billing.stripe.com/p/cus_abc"


def test_portal_requires_a_customer(client, usage):
    import anyio
    anyio.run(usage.set_paid, "user_123", True)
    assert client.post("/v1/billing/portal", headers=SH).status_code == 404


def test_portal_requires_auth(client):
    assert client.post("/v1/billing/portal").status_code == 401


def test_account_page_offers_management_when_paid(client):
    html = client.get("/signin").text
    assert 'id="manage"' in html
    assert "cancel" in html.lower()
