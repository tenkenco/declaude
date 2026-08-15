"""Security headers. The account page mints and deletes credentials, so framing and
script injection are the risks that matter most here."""
import re

import pytest
from conftest import FakeAuth
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.config import Settings


@pytest.fixture
def client(model, usage):
    s = Settings(clerk_publishable_key="pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk")
    return TestClient(create_app(model=model, auth=FakeAuth(), usage=usage, settings=s))


@pytest.mark.parametrize("path", ["/", "/signin", "/documents"])
def test_html_pages_carry_the_baseline_headers(client, path):
    h = client.get(path).headers
    assert h["strict-transport-security"].startswith("max-age=")
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert "referrer-policy" in h
    assert "content-security-policy" in h


def test_csp_blocks_framing_and_objects(client):
    csp = client.get("/signin").headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp


def test_inline_scripts_run_under_a_nonce_not_unsafe_inline(client):
    r = client.get("/signin")
    csp = r.headers["content-security-policy"]
    assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
    nonce = re.search(r"'nonce-([A-Za-z0-9_-]+)'", csp).group(1)
    assert f'nonce="{nonce}"' in r.text


def test_nonce_differs_per_response(client):
    a = client.get("/signin").headers["content-security-policy"]
    b = client.get("/signin").headers["content-security-policy"]
    assert a != b


def test_clerk_is_allowed_to_load(client):
    csp = client.get("/signin").headers["content-security-policy"]
    assert "clerk" in csp or "https:" in csp.split("script-src")[1].split(";")[0]


def test_api_responses_are_not_sniffable(client):
    h = client.post("/v1/demo", json={"text": "Certainly!"}).headers
    assert h["x-content-type-options"] == "nosniff"


def test_api_errors_do_not_leak_internals(client):
    r = client.post("/v1/translate", json={"text": "x"},
                    headers={"Authorization": "Bearer dk_bogus"})
    body = r.text.lower()
    assert "traceback" not in body and "file \"" not in body


# A nonce whitelists <script> blocks but never on* attributes, so an inline handler on the
# Clerk loader is dropped and every signed-out page renders blank. Caught in production.
@pytest.mark.parametrize("path", ["/", "/signin", "/documents"])
def test_pages_have_no_inline_event_handlers(client, path):
    html = client.get(path).text
    assert not re.search(r"<[^>]*\son[a-z]+\s*=", html), f"{path} uses an inline event handler"


@pytest.mark.parametrize("path", ["/signin", "/documents"])
def test_clerk_loader_is_wired_from_a_nonced_script(client, path):
    html = client.get(path).text
    assert 'id="clerk-js"' in html
    assert 'getElementById("clerk-js")' in html


def directives(csp: str) -> dict[str, list[str]]:
    """CSP text to {directive: [sources]}. Exact sources, so a check cannot pass on a
    substring of some other host."""
    out = {}
    for part in csp.split(";"):
        if tokens := part.split():
            out[tokens[0]] = tokens[1:]
    return out


def test_csp_allows_what_clerk_needs_to_render_sign_in(client):
    d = directives(client.get("/signin").headers["content-security-policy"])
    assert d["worker-src"] == ["'self'", "blob:"]          # session token refresh worker
    turnstile = "https://challenges.cloudflare.com"        # Clerk's bot check, in an iframe
    assert turnstile in d["frame-src"]
    assert turnstile in d["script-src"]


def test_csp_allows_analytics_beacons(client):
    d = directives(client.get("/signin").headers["content-security-policy"])
    # equality per source, not substring: CodeQL reads `"https://host" in text` as a
    # half-done URL check, and the exact-source form is what the test means anyway
    assert any(src == "https://www.google-analytics.com" for src in d["connect-src"])
    assert any(src == "https://www.googletagmanager.com" for src in d["script-src"])
