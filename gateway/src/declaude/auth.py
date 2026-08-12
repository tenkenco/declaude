"""Authentication: Clerk session JWTs for the browser, declaude API keys for clients."""
from abc import ABC, abstractmethod

import jwt
from jwt import PyJWKClient

from .keys import ApiKeyStore, hash_key, looks_like_api_key


class Authenticator(ABC):
    @abstractmethod
    async def verify(self, token: str) -> str:
        """Return the stable user id for a valid token; raise on anything else."""


class ClerkAuthenticator(Authenticator):
    def __init__(self, jwks_url: str, authorized_parties: list[str] | None = None):
        self._jwks = PyJWKClient(jwks_url, cache_keys=True)
        self._azp = set(authorized_parties or [])

    async def verify(self, token: str) -> str:
        key = self._jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key.key, algorithms=["RS256"], options={"verify_aud": False})
        if self._azp and claims.get("azp") not in self._azp:
            raise ValueError("azp not authorized")
        return claims["sub"]


class ApiKeyAuthenticator(Authenticator):
    """Verify a long-lived declaude API key by hash lookup."""

    def __init__(self, store: ApiKeyStore):
        self._store = store

    async def verify(self, token: str) -> str:
        user_id = await self._store.lookup(hash_key(token))
        if not user_id:
            raise ValueError("unknown api key")
        return user_id


class CompositeAuthenticator(Authenticator):
    """Route by prefix: `dc_` is an API key, anything else is a Clerk session JWT."""

    def __init__(self, *, api_key: Authenticator, clerk: Authenticator):
        self._api_key = api_key
        self._clerk = clerk

    async def verify(self, token: str) -> str:
        if looks_like_api_key(token):
            return await self._api_key.verify(token)
        return await self._clerk.verify(token)
