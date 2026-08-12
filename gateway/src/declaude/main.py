"""Production/dev entrypoint.

DECLAUDE_AUTH_MODE=clerk (default) verifies Clerk JWTs via JWKS.
DECLAUDE_AUTH_MODE=dev accepts the static token in DECLAUDE_DEV_TOKEN (local dogfooding only).
"""
import os

from .app import create_app
from .auth import Authenticator, ClerkAuthenticator
from .config import Settings
from .model import OpenAICompatClient
from .usage import InMemoryUsageStore


class DevAuthenticator(Authenticator):
    def __init__(self, token: str):
        if not token:
            raise RuntimeError("DECLAUDE_DEV_TOKEN required in dev auth mode")
        self._token = token

    async def verify(self, token: str) -> str:
        if token != self._token:
            raise ValueError("bad token")
        return "dev_user"


def build_app():
    settings = Settings.from_env()
    if os.environ.get("DECLAUDE_AUTH_MODE", "clerk") == "dev":
        auth: Authenticator = DevAuthenticator(os.environ.get("DECLAUDE_DEV_TOKEN", ""))
    else:
        auth = ClerkAuthenticator(
            jwks_url=os.environ["CLERK_JWKS_URL"],
            authorized_parties=[p for p in os.environ.get("CLERK_AUTHORIZED_PARTIES", "").split(",") if p],
        )
    model = OpenAICompatClient(base_url=settings.model_base_url, model=settings.model_name)
    return create_app(model=model, auth=auth, usage=InMemoryUsageStore(), settings=settings)


app = build_app()
