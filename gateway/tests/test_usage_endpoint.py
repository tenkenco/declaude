"""Usage must be visible before you hit a 402 — in the GUI and over MCP."""
import pytest
from conftest import FakeAuth
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.config import Settings

KH = {"Authorization": "Bearer dk_test"}
SH = {"Authorization": "Bearer valid-token"}


@pytest.fixture
def client(model, usage):
    s = Settings(free_tier_monthly_limit=100, free_tier_monthly_documents=5,
                 paid_monthly_documents=500, stripe_payment_link="https://buy.stripe.com/x",
                 clerk_publishable_key="pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk")
    c = TestClient(create_app(model=model, auth=FakeAuth(), usage=usage, settings=s))
    import anyio

    from declaude.keys import hash_key
    anyio.run(usage.add_api_key, hash_key("dk_test"), "user_123", "dk_test…test")
    return c


def test_usage_with_api_key(client):
    r = client.get("/v1/usage", headers=KH)
    assert r.status_code == 200
    b = r.json()
    assert b["plan"] == "free"
    assert b["translations"] == {"used": 0, "limit": 100}
    assert b["documents"] == {"used": 0, "limit": 5}
    assert b["upgrade_url"].endswith("/upgrade?ref=user_123")
    assert b["period"]


def test_usage_counts_real_activity(client):
    client.post("/v1/translate", json={"text": "hi"}, headers=KH)
    client.post("/v1/documents", files={"file": ("a.md", b"Certainly! Robust.", "text/markdown")}, headers=KH)
    b = client.get("/v1/usage", headers=KH).json()
    assert b["translations"]["used"] == 1
    assert b["documents"]["used"] == 1


def test_paid_plan_is_unlimited_translations(client, usage):
    import anyio
    anyio.run(usage.set_paid, "user_123", True)
    b = client.get("/v1/usage", headers=KH).json()
    assert b["plan"] == "paid"
    assert b["translations"]["limit"] is None
    assert b["documents"]["limit"] == 500
    assert "upgrade_url" not in b


def test_usage_requires_auth(client):
    assert client.get("/v1/usage").status_code == 401


def test_usage_works_with_session_too(client):
    assert client.get("/v1/usage", headers=SH).status_code == 200


# --- MCP surface ---

def rpc(client, method, params=None, headers=KH):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        body["params"] = params
    return client.post("/mcp", json=body, headers=headers).json()


def test_mcp_lists_usage_tool(client):
    names = [t["name"] for t in rpc(client, "tools/list")["result"]["tools"]]
    assert "usage" in names and "translate" in names


def test_mcp_usage_tool_reports_quota(client):
    client.post("/v1/translate", json={"text": "hi"}, headers=KH)
    text = rpc(client, "tools/call", {"name": "usage", "arguments": {}})["result"]["content"][0]["text"]
    assert "1" in text and "100" in text
    assert "upgrade" in text.lower()


def test_mcp_usage_tool_paid(client, usage):
    import anyio
    anyio.run(usage.set_paid, "user_123", True)
    text = rpc(client, "tools/call", {"name": "usage", "arguments": {}})["result"]["content"][0]["text"]
    assert "unlimited" in text.lower()


# --- account page ---

def test_account_shows_usage_first_with_upgrade(client):
    html = client.get("/signin").text
    assert html.index('id="usage-card"') < html.index('id="docs-card"')
    assert 'id="upgrade"' in html
    assert "<progress" in html or 'class="bar"' in html
