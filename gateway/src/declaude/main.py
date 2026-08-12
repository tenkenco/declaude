"""Production/dev entrypoint.

DECLAUDE_AUTH_MODE=clerk (default) verifies Clerk JWTs via JWKS.
DECLAUDE_AUTH_MODE=dev accepts the static token in DECLAUDE_DEV_TOKEN (local dogfooding only).
DECLAUDE_USAGE_BACKEND=firestore|memory (default memory) selects the usage store.
STRIPE_WEBHOOK_SECRET enables Stripe webhook signature verification.
"""
import os

from .app import create_app, default_webhook_verifier
from .auth import Authenticator, ClerkAuthenticator
from .config import Settings
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


def build_usage_store() -> UsageStore:
    if os.environ.get("DECLAUDE_USAGE_BACKEND", "memory") == "firestore":
        from google.cloud import firestore

        return FirestoreUsageStore(firestore.AsyncClient(project=os.environ.get("GOOGLE_CLOUD_PROJECT")))
    return InMemoryUsageStore()


def build_app():
    settings = Settings.from_env()
    if not settings.clerk_publishable_key and os.environ.get("CLERK_JWKS_URL"):
        # /signin derives the publishable key from the JWKS host: same Clerk frontend,
        # no second config value to keep in sync.
        settings.clerk_publishable_key = publishable_key_from_jwks(os.environ["CLERK_JWKS_URL"])
    if os.environ.get("DECLAUDE_AUTH_MODE", "clerk") == "dev":
        auth: Authenticator = DevAuthenticator(os.environ.get("DECLAUDE_DEV_TOKEN", ""))
    else:
        auth = ClerkAuthenticator(
            jwks_url=os.environ["CLERK_JWKS_URL"],
            authorized_parties=[p for p in os.environ.get("CLERK_AUTHORIZED_PARTIES", "").split(",") if p],
        )
    model = OpenAICompatClient(base_url=settings.model_base_url, model=settings.model_name)
    return create_app(
        model=model,
        auth=auth,
        usage=build_usage_store(),
        settings=settings,
        webhook_verifier=default_webhook_verifier,
    )


app = build_app()
