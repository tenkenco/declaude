"""OAuth 2.1 for MCP clients: discovery, DCR, PKCE authorize/token.
`claude mcp add --transport http declaude <url>/mcp` with no header must Just Work."""
import base64
import hashlib
import secrets

import pytest
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.config import Settings


class FakeAuth:
    async def verify(self, token: str) -> str:
        if token == "valid-token":
            return "user_123"
        raise ValueError("bad token")


@pytest.fixture
def client(model, usage):
    s = Settings(
        free_tier_monthly_limit=3,
        public_base_url="https://speak-english.tenken.co",
        clerk_publishable_key="pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk",
    )
    app = create_app(model=model, auth=FakeAuth(), usage=usage, settings=s)
    return TestClient(app)


def pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def do_authorize(client, challenge, redirect="http://localhost:33418/callback", state="st8"):
    """Simulate the approve step: signed-in browser posts its Clerk token."""
    cid = client.post("/oauth/register", json={"client_name": "t", "redirect_uris": [redirect]}).json()["client_id"]
    return client.post("/oauth/approve", json={
        "token": "valid-token", "client_id": cid, "redirect_uri": redirect,
        "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
    })


# --- discovery ---

def test_protected_resource_metadata(client):
    r = client.get("/.well-known/oauth-protected-resource")
    assert r.status_code == 200
    body = r.json()
    assert body["resource"] == "https://speak-english.tenken.co"
    assert body["authorization_servers"] == ["https://speak-english.tenken.co"]


def test_authorization_server_metadata(client):
    r = client.get("/.well-known/oauth-authorization-server")
    m = r.json()
    assert m["issuer"] == "https://speak-english.tenken.co"
    assert m["authorization_endpoint"].endswith("/oauth/authorize")
    assert m["token_endpoint"].endswith("/oauth/token")
    assert m["registration_endpoint"].endswith("/oauth/register")
    assert "S256" in m["code_challenge_methods_supported"]
    assert "authorization_code" in m["grant_types_supported"]


def test_mcp_401_advertises_resource_metadata(client):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401
    assert "resource_metadata" in r.headers.get("WWW-Authenticate", "")


# --- dynamic client registration ---

def test_register_returns_public_client(client):
    r = client.post("/oauth/register", json={"redirect_uris": ["http://localhost:1/cb"], "client_name": "claude"})
    assert r.status_code == 201
    body = r.json()
    assert body["client_id"]
    assert body["token_endpoint_auth_method"] == "none"


# --- authorize page ---

def test_authorize_serves_signin_page(client):
    cid = client.post("/oauth/register", json={"client_name": "t", "redirect_uris": ["http://localhost:1/cb"]}).json()["client_id"]
    r = client.get("/oauth/authorize", params={
        "client_id": cid, "redirect_uri": "http://localhost:1/cb", "response_type": "code",
        "state": "s", "code_challenge": "c", "code_challenge_method": "S256",
    })
    assert r.status_code == 200
    assert "clerk" in r.text.lower()


def test_authorize_rejects_plain_challenge_method(client):
    r = client.get("/oauth/authorize", params={
        "client_id": "c", "redirect_uri": "http://localhost:1/cb", "response_type": "code",
        "code_challenge": "c", "code_challenge_method": "plain",
    })
    assert r.status_code == 400


# --- approve + token exchange ---

def test_full_pkce_flow_yields_working_token(client):
    verifier, challenge = pkce()
    r = do_authorize(client, challenge)
    assert r.status_code == 200
    redirect = r.json()["redirect_to"]
    assert redirect.startswith("http://localhost:33418/callback?")
    assert "state=st8" in redirect
    code = redirect.split("code=")[1].split("&")[0]

    t = client.post("/oauth/token", data={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "http://localhost:33418/callback",
        "client_id": "cli_x", "code_verifier": verifier,
    })
    assert t.status_code == 200
    tok = t.json()
    assert tok["token_type"] == "Bearer"
    assert tok["access_token"].startswith("dk_")
    # token works on the MCP endpoint
    m = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                    headers={"Authorization": f"Bearer {tok['access_token']}"})
    assert m.status_code == 200


def test_wrong_verifier_rejected(client):
    _, challenge = pkce()
    code = do_authorize(client, challenge).json()["redirect_to"].split("code=")[1].split("&")[0]
    t = client.post("/oauth/token", data={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "http://localhost:33418/callback",
        "client_id": "cli_x", "code_verifier": "wrong-verifier-aaaaaaaaaaaaaaaaaaaaaaa",
    })
    assert t.status_code == 400


def test_code_is_single_use(client):
    verifier, challenge = pkce()
    code = do_authorize(client, challenge).json()["redirect_to"].split("code=")[1].split("&")[0]
    form = {"grant_type": "authorization_code", "code": code,
            "redirect_uri": "http://localhost:33418/callback",
            "client_id": "cli_x", "code_verifier": verifier}
    assert client.post("/oauth/token", data=form).status_code == 200
    assert client.post("/oauth/token", data=form).status_code == 400


def test_redirect_uri_must_match(client):
    verifier, challenge = pkce()
    code = do_authorize(client, challenge).json()["redirect_to"].split("code=")[1].split("&")[0]
    t = client.post("/oauth/token", data={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "http://evil.example/cb",
        "client_id": "cli_x", "code_verifier": verifier,
    })
    assert t.status_code == 400


def test_approve_requires_valid_session(client):
    r = client.post("/oauth/approve", json={
        "token": "garbage", "client_id": "cli_any", "redirect_uri": "http://localhost:1/cb",
        "state": "s", "code_challenge": "c", "code_challenge_method": "S256",
    })
    assert r.status_code == 401


# --- UX: friendly client names, sticky redirect, auto-approve ---

def test_registered_client_name_shown_on_authorize(client):
    reg = client.post("/oauth/register", json={"client_name": "Claude Code", "redirect_uris": ["http://localhost:1/cb"]}).json()
    r = client.get("/oauth/authorize", params={
        "client_id": reg["client_id"], "redirect_uri": "http://localhost:1/cb", "response_type": "code",
        "state": "s", "code_challenge": "c", "code_challenge_method": "S256",
    })
    assert "Claude Code" in r.text
    assert reg["client_id"] not in r.text  # raw IDs are not for humans


def test_unknown_client_gets_generic_name(client):
    r = client.get("/oauth/authorize", params={
        "client_id": "cli_never_registered", "redirect_uri": "http://localhost:1/cb", "response_type": "code",
        "state": "s", "code_challenge": "c", "code_challenge_method": "S256",
    })
    assert "cli_never_registered" not in r.text


def test_authorize_page_pins_redirect_and_autoapproves(client):
    cid = client.post("/oauth/register", json={"client_name": "t", "redirect_uris": ["http://localhost:1/cb"]}).json()["client_id"]
    r = client.get("/oauth/authorize", params={
        "client_id": cid, "redirect_uri": "http://localhost:1/cb", "response_type": "code",
        "state": "s", "code_challenge": "c", "code_challenge_method": "S256",
    })
    assert "forceRedirectUrl" in r.text   # sign-in must return to this exact page
    assert "autoApprove" in r.text        # signed-in return completes without extra clicks


# --- security review: redirect_uri pinning ---

def register(client, uris):
    return client.post("/oauth/register", json={"client_name": "c", "redirect_uris": uris}).json()


def test_authorize_rejects_unregistered_redirect(client):
    reg = register(client, ["http://localhost:33418/callback"])
    r = client.get("/oauth/authorize", params={
        "client_id": reg["client_id"], "redirect_uri": "https://evil.example/cb",
        "response_type": "code", "code_challenge": "c", "code_challenge_method": "S256"})
    assert r.status_code == 400


def test_approve_rejects_unregistered_redirect(client):
    reg = register(client, ["http://localhost:33418/callback"])
    r = client.post("/oauth/approve", json={
        "token": "valid-token", "client_id": reg["client_id"],
        "redirect_uri": "https://evil.example/cb", "state": "s",
        "code_challenge": "c", "code_challenge_method": "S256"})
    assert r.status_code == 400


def test_localhost_port_variance_allowed(client):
    """MCP clients bind a random localhost port; host match suffices for loopback."""
    reg = register(client, ["http://localhost:33418/callback"])
    r = client.post("/oauth/approve", json={
        "token": "valid-token", "client_id": reg["client_id"],
        "redirect_uri": "http://localhost:19999/callback", "state": "s",
        "code_challenge": "c", "code_challenge_method": "S256"})
    assert r.status_code == 200


def test_unknown_client_cannot_authorize(client):
    r = client.post("/oauth/approve", json={
        "token": "valid-token", "client_id": "cli_ghost",
        "redirect_uri": "http://localhost:1/cb", "state": "s",
        "code_challenge": "c", "code_challenge_method": "S256"})
    assert r.status_code == 400
