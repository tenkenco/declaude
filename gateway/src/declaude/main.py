"""Production/dev entrypoint.

DECLAUDE_AUTH_MODE=clerk (default) verifies Clerk JWTs via JWKS.
DECLAUDE_AUTH_MODE=dev accepts the static token in DECLAUDE_DEV_TOKEN (local dogfooding only).
DECLAUDE_USAGE_BACKEND=firestore|memory (default memory) selects the usage store.
STRIPE_WEBHOOK_SECRET enables Stripe webhook signature verification.
"""
import os

from .app import create_app, default_webhook_verifier
from .auth import (
    ApiKeyAuthenticator,
    Authenticator,
    ClerkAuthenticator,
    CompositeAuthenticator,
)
from .config import Settings
from .keys import ApiKeyStore, FirestoreApiKeyStore, InMemoryApiKeyStore
from .model import OpenAICompatClient
from .signin import publishable_key_from_jwks
from .usage import FirestoreUsageStore, InMemoryUsageStore, UsageStore


class DevAuthenticator(Authenticator):
    def __init__(self, token: str):
        if not token:
            raise RuntimeError("DECLAUDE_DEV_TOKEN required in dev auth mode")
        self._token = token

    async def verify(self, token: str) -> str:
        if token != self._token:
            raise ValueError("bad token")
        return "dev_user"


def _firestore_client():
    from google.cloud import firestore

    return firestore.AsyncClient(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))


def build_usage_store() -> UsageStore:
    if os.environ.get("DECLAUDE_USAGE_BACKEND", "memory") == "firestore":
        return FirestoreUsageStore(_firestore_client())
    return InMemoryUsageStore()


def build_api_key_store() -> ApiKeyStore:
    """Keys share the usage backend: both are per-user state that must survive a restart."""
    if os.environ.get("DECLAUDE_USAGE_BACKEND", "memory") == "firestore":
        return FirestoreApiKeyStore(_firestore_client())
    return InMemoryApiKeyStore()


def build_app():
    settings = Settings.from_env()
    if not settings.clerk_publishable_key:
        settings = settings.model_copy(
            update={"clerk_publishable_key": publishable_key_from_jwks(os.environ.get("CLERK_JWKS_URL", ""))}
        )
    api_keys = build_api_key_store()
    if os.environ.get("DECLAUDE_AUTH_MODE", "clerk") == "dev":
        session_auth: Authenticator = DevAuthenticator(os.environ.get("DECLAUDE_DEV_TOKEN", ""))
    else:
        session_auth = ClerkAuthenticator(
            jwks_url=os.environ["CLERK_JWKS_URL"],
            authorized_parties=[p for p in os.environ.get("CLERK_AUTHORIZED_PARTIES", "").split(",") if p],
        )
    auth = CompositeAuthenticator(api_key=ApiKeyAuthenticator(api_keys), clerk=session_auth)
    model = OpenAICompatClient(base_url=settings.model_base_url, model=settings.model_name)
    return create_app(
        model=model,
        auth=auth,
        usage=build_usage_store(),
        settings=settings,
        webhook_verifier=default_webhook_verifier,
        api_keys=api_keys,
    )


app = build_app()
