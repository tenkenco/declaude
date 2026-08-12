"""Sign-in page: public, self-describing, and wired to the real Clerk instance."""
from conftest import FakeAuth
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.config import Settings
from declaude.signin import clerk_js_for, signin_html

PK = "pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk"  # base64 of "example.clerk.accounts.dev$"


def test_signin_is_public_html(client):
    r = client.get("/signin")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")


def test_signin_embeds_the_publishable_key(client):
    assert PK in client.get("/signin").text


def test_signin_loads_clerk_from_the_instance_host(client):
    assert "https://example.clerk.accounts.dev/npm/@clerk/clerk-js" in client.get("/signin").text


def test_signin_posts_to_the_keys_endpoint(client):
    assert "/v1/keys" in client.get("/signin").text


def test_signin_tells_the_user_the_key_is_shown_once(client):
    assert "shown once" in client.get("/signin").text


def test_signin_names_the_hook_variable(client):
    assert "DECLAUDE_TOKEN" in client.get("/signin").text


def test_clerk_js_url_derives_the_host_from_the_key():
    assert clerk_js_for(PK).startswith("https://example.clerk.accounts.dev/npm/")


def test_clerk_js_url_survives_a_malformed_key():
    """A bad key must not raise on a public page."""
    assert clerk_js_for("pk_test_@@@@").startswith("https://")


def test_unconfigured_gateway_explains_itself(model, usage):
    settings = Settings(clerk_publishable_key="")
    app = create_app(model=model, auth=FakeAuth(), usage=usage, settings=settings)
    body = TestClient(app).get("/signin").text
    assert "DECLAUDE_CLERK_PUBLISHABLE_KEY" in body


def test_signin_page_is_lightweight(client):
    assert len(client.get("/signin").content) < 15 * 1024


def test_signin_html_never_leaks_a_secret_key():
    assert "sk_" not in signin_html(PK)
