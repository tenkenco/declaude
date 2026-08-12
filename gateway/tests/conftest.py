"""Shared fixtures. All external boundaries (model, auth, usage store) are injected fakes."""
import pytest
from fastapi.testclient import TestClient

from declaude.app import create_app
from declaude.auth import ApiKeyAuthenticator, CompositeAuthenticator
from declaude.config import Settings
from declaude.keys import InMemoryApiKeyStore
from declaude.model import ModelClient
from declaude.usage import InMemoryUsageStore


class FakeModelClient(ModelClient):
    """Deterministic fake standing in for the vLLM/Ollama backend."""

    def __init__(self):
        self.calls: list[dict] = []

    async def complete(self, system: str, prompt: str) -> str:
        self.calls.append({"system": system, "prompt": prompt})
        return f"PLAIN::{prompt}"


class FakeAuth:
    """Stub Clerk verifier: token 'valid-token' -> user 'user_123'; anything else rejected."""

    async def verify(self, token: str) -> str:
        if token == "valid-token":
            return "user_123"
        raise ValueError("bad token")


@pytest.fixture
def model():
    return FakeModelClient()


@pytest.fixture
def usage():
    return InMemoryUsageStore()


@pytest.fixture
def api_keys():
    return InMemoryApiKeyStore()


@pytest.fixture
def settings():
    return Settings(
        free_tier_monthly_limit=3,
        stripe_payment_link="https://buy.stripe.com/test_declaude",
        clerk_publishable_key="pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk",
    )


@pytest.fixture
def client(model, usage, settings, api_keys):
    auth = CompositeAuthenticator(api_key=ApiKeyAuthenticator(api_keys), clerk=FakeAuth())
    app = create_app(model=model, auth=auth, usage=usage, settings=settings, api_keys=api_keys)
    return TestClient(app)


AUTH = {"Authorization": "Bearer valid-token"}
