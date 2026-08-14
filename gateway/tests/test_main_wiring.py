"""Bootstrap wiring: the code that only ever runs in production.

Every branch here is a deploy-time decision, so a mistake shows up as a broken revision
rather than a failing test. That is exactly why it is worth covering.
"""
import os

import pytest

# declaude.main builds `app` at import time so uvicorn can find it, which means the module
# cannot be imported without deploy config present. Satisfy it before importing.
CLERK_ENV = {"CLERK_JWKS_URL": "https://clerk.tenken.co/.well-known/jwks.json"}
os.environ.setdefault("CLERK_JWKS_URL", CLERK_ENV["CLERK_JWKS_URL"])

from declaude.main import DevAuthenticator, build_app, build_usage_store
from declaude.usage import InMemoryUsageStore


def test_dev_authenticator_accepts_only_its_token():
    import anyio

    auth = DevAuthenticator("s3cret")
    assert anyio.run(auth.verify, "s3cret") == "dev_user"
    with pytest.raises(ValueError):
        anyio.run(auth.verify, "wrong")


def test_dev_mode_requires_a_token():
    with pytest.raises(RuntimeError, match="DECLAUDE_DEV_TOKEN"):
        DevAuthenticator("")


def test_usage_store_defaults_to_memory(monkeypatch):
    monkeypatch.delenv("DECLAUDE_USAGE_BACKEND", raising=False)
    assert isinstance(build_usage_store(), InMemoryUsageStore)


def test_app_builds_in_dev_mode(monkeypatch):
    monkeypatch.setenv("DECLAUDE_AUTH_MODE", "dev")
    monkeypatch.setenv("DECLAUDE_DEV_TOKEN", "t")
    app = build_app()
    assert any(r.path == "/v1/translate" for r in app.routes)


def test_publishable_key_is_derived_from_jwks(monkeypatch):
    """A deploy sets CLERK_JWKS_URL only; /signin must still render a working widget."""
    monkeypatch.setenv("DECLAUDE_AUTH_MODE", "dev")
    monkeypatch.setenv("DECLAUDE_DEV_TOKEN", "t")
    monkeypatch.delenv("DECLAUDE_CLERK_PUBLISHABLE_KEY", raising=False)
    for k, v in CLERK_ENV.items():
        monkeypatch.setenv(k, v)
    from fastapi.testclient import TestClient

    body = TestClient(build_app()).get("/signin").text
    assert "pk_live_" in body
    assert "clerk.tenken.co" in body


def test_clerk_mode_is_the_default(monkeypatch):
    monkeypatch.delenv("DECLAUDE_AUTH_MODE", raising=False)
    for k, v in CLERK_ENV.items():
        monkeypatch.setenv(k, v)
    app = build_app()
    assert any(r.path == "/mcp" for r in app.routes)
