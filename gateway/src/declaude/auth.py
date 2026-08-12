"""Clerk authentication: verify session JWTs against the Clerk instance JWKS."""
from abc import ABC, abstractmethod

import jwt
from jwt import PyJWKClient


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
