"""Free tier + x402-style payment gate: N free requests/month, then HTTP 402 with payment info."""
from conftest import AUTH


def test_free_tier_allows_up_to_limit(client, settings):
    for _ in range(settings.free_tier_monthly_limit):
        r = client.post("/v1/translate", json={"text": "hi"}, headers=AUTH)
        assert r.status_code == 200


def test_exceeding_free_tier_returns_402(client, settings):
    for _ in range(settings.free_tier_monthly_limit):
        client.post("/v1/translate", json={"text": "hi"}, headers=AUTH)
    r = client.post("/v1/translate", json={"text": "hi"}, headers=AUTH)
    assert r.status_code == 402


def test_402_carries_x402_payment_details(client, settings):
    for _ in range(settings.free_tier_monthly_limit):
        client.post("/v1/translate", json={"text": "hi"}, headers=AUTH)
    r = client.post("/v1/translate", json={"text": "hi"}, headers=AUTH)
    body = r.json()
    # x402-style machine-readable payment challenge
    assert body["error"] == "payment_required"
    assert body["accepts"][0]["url"] == settings.stripe_payment_link
    assert r.headers.get("X-Payment-Required") is not None


def test_remaining_quota_reported_in_headers(client, settings):
    r = client.post("/v1/translate", json={"text": "hi"}, headers=AUTH)
    assert r.headers["X-RateLimit-Remaining"] == str(settings.free_tier_monthly_limit - 1)


def test_paid_user_bypasses_free_tier(client, usage, settings):
    usage.mark_paid_sync("user_123")
    for _ in range(settings.free_tier_monthly_limit + 2):
        r = client.post("/v1/translate", json={"text": "hi"}, headers=AUTH)
        assert r.status_code == 200
