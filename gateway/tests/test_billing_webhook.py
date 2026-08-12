"""Stripe webhook: public endpoint, signature-verified, flips paid flags in the usage store."""
import pytest
from fastapi.testclient import TestClient

from declaude.app import create_app


class FakeAuth:
    async def verify(self, token: str) -> str:
        if token == "valid-token":
            return "user_123"
        raise ValueError("bad token")


class StubVerifier:
    """Stands in for stripe.Webhook.construct_event."""

    def __init__(self):
        self.event: dict | None = None
        self.calls: list[tuple[bytes, str]] = []

    def __call__(self, payload: bytes, sig_header: str) -> dict:
        self.calls.append((payload, sig_header))
        if self.event is None:
            raise ValueError("invalid signature")
        return self.event


@pytest.fixture
def verifier():
    return StubVerifier()


@pytest.fixture
def client(model, usage, settings, verifier):
    app = create_app(
        model=model, auth=FakeAuth(), usage=usage, settings=settings, webhook_verifier=verifier
    )
    return TestClient(app)


def post_webhook(client, body=b"{}", sig="t=1,v1=abc"):
    return client.post("/v1/billing/webhook", content=body, headers={"Stripe-Signature": sig})


async def test_invalid_signature_returns_400(client, verifier):
    verifier.event = None  # stub raises
    resp = post_webhook(client)
    assert resp.status_code == 400


async def test_no_auth_required(client, verifier):
    """Webhook is public: no Clerk bearer token, only Stripe signature."""
    verifier.event = {"type": "ping", "data": {"object": {}}}
    resp = post_webhook(client)
    assert resp.status_code == 200


async def test_checkout_completed_sets_paid_via_metadata(client, verifier, usage):
    verifier.event = {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"clerk_user_id": "user_123"}}},
    }
    resp = post_webhook(client)
    assert resp.status_code == 200
    assert await usage.is_paid("user_123") is True


async def test_checkout_completed_sets_paid_via_client_reference_id(client, verifier, usage):
    verifier.event = {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {}, "client_reference_id": "user_456"}},
    }
    resp = post_webhook(client)
    assert resp.status_code == 200
    assert await usage.is_paid("user_456") is True


async def test_checkout_completed_without_user_id_is_acknowledged(client, verifier, usage):
    verifier.event = {"type": "checkout.session.completed", "data": {"object": {"metadata": {}}}}
    resp = post_webhook(client)
    assert resp.status_code == 200


async def test_subscription_deleted_clears_paid(client, verifier, usage):
    await usage.set_paid("user_123", True)
    verifier.event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"metadata": {"clerk_user_id": "user_123"}}},
    }
    resp = post_webhook(client)
    assert resp.status_code == 200
    assert await usage.is_paid("user_123") is False


async def test_unknown_event_type_returns_received(client, verifier):
    verifier.event = {"type": "invoice.paid", "data": {"object": {}}}
    resp = post_webhook(client)
    assert resp.status_code == 200
    assert resp.json() == {"received": True}


async def test_verifier_receives_raw_body_and_signature(client, verifier):
    verifier.event = {"type": "ping", "data": {"object": {}}}
    post_webhook(client, body=b'{"raw": true}', sig="t=9,v1=zzz")
    assert verifier.calls[-1] == (b'{"raw": true}', "t=9,v1=zzz")


def test_default_verifier_returns_plain_dict(monkeypatch):
    """Prod finding: stripe.Webhook.construct_event returns a StripeObject whose
    `.get` lookup can raise; the verifier must hand the handler a plain dict."""
    import json
    import time

    import stripe
    from declaude.app import default_webhook_verifier

    secret = "whsec_testsecret"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    payload = json.dumps({
        "id": "evt_1", "object": "event", "api_version": stripe.api_version,
        "type": "checkout.session.completed",
        "data": {"object": {"object": "checkout.session", "metadata": {"clerk_user_id": "user_x"}}},
    }).encode()
    ts = int(time.time())
    sig = stripe.WebhookSignature._compute_signature(f"{ts}.{payload.decode()}", secret)
    event = default_webhook_verifier(payload, f"t={ts},v1={sig}")
    assert type(event) is dict
    assert event.get("type") == "checkout.session.completed"
    assert event["data"]["object"]["metadata"]["clerk_user_id"] == "user_x"
