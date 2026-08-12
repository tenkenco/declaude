"""Long-lived API keys (dk_...) for hooks/CLIs where short-lived Clerk JWTs don't fit.
Only salted-free SHA-256 digests are stored; a leaked database never yields usable keys."""
import hashlib
import secrets


def generate_key() -> str:
    return "dk_" + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()
