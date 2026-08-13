"""OAuth 2.1 authorization server for MCP clients (RFC 8414/7591/7636/9728).

Deliberately minimal: public clients only, PKCE S256 required, and the issued
access token IS a declaude dk_ API key — one credential model everywhere.
"""
import base64
import hashlib
import secrets
import time
from dataclasses import dataclass

CODE_TTL_SECONDS = 600


@dataclass(frozen=True)
class AuthCode:
    """One authorization grant: issued at /oauth/approve, consumed once at /oauth/token."""

    user_id: str
    redirect_uri: str
    code_challenge: str
    expires_at: float

    def expired(self, now: float | None = None) -> bool:
        return (now if now is not None else time.time()) > self.expires_at


def new_code() -> str:
    return secrets.token_urlsafe(32)


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def verify_pkce(verifier: str, challenge: str) -> bool:
    computed = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return secrets.compare_digest(computed, challenge)


def resource_metadata(base_url: str) -> dict:
    b = base_url.rstrip("/")
    return {"resource": b, "authorization_servers": [b], "bearer_methods_supported": ["header"]}


def server_metadata(base_url: str) -> dict:
    b = base_url.rstrip("/")
    return {
        "issuer": b,
        "authorization_endpoint": f"{b}/oauth/authorize",
        "token_endpoint": f"{b}/oauth/token",
        "registration_endpoint": f"{b}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["translate"],
    }
