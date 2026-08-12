"""Long-lived declaude API keys.

A Clerk session token expires quickly, so it cannot sit in a Claude Code hook or a
shell profile. An API key does. Users mint one after signing in; only the SHA-256
hash is ever stored."""
import hashlib
import secrets
from abc import ABC, abstractmethod

KEY_PREFIX = "dc_"


def generate_key() -> str:
    """Return a fresh plaintext key. The caller must show it once and never store it."""
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def looks_like_api_key(token: str) -> bool:
    return token.startswith(KEY_PREFIX)


class ApiKeyStore(ABC):
    @abstractmethod
    async def add(self, key_hash: str, user_id: str) -> None: ...
    @abstractmethod
    async def lookup(self, key_hash: str) -> str | None: ...
    @abstractmethod
    async def revoke(self, key_hash: str) -> None: ...


class InMemoryApiKeyStore(ApiKeyStore):
    def __init__(self):
        self._keys: dict[str, str] = {}

    async def add(self, key_hash: str, user_id: str) -> None:
        self._keys[key_hash] = user_id

    async def lookup(self, key_hash: str) -> str | None:
        return self._keys.get(key_hash)

    async def revoke(self, key_hash: str) -> None:
        self._keys.pop(key_hash, None)


class FirestoreApiKeyStore(ApiKeyStore):
    """`api_keys/{sha256(key)}` -> {user_id}. The plaintext key never reaches Firestore.

    Accepts a google.cloud.firestore.AsyncClient (or a duck-typed fake in tests)."""

    def __init__(self, client):
        self._db = client

    def _doc(self, key_hash: str):
        return self._db.collection("api_keys").document(key_hash)

    async def add(self, key_hash: str, user_id: str) -> None:
        await self._doc(key_hash).set({"user_id": user_id})

    async def lookup(self, key_hash: str) -> str | None:
        snapshot = await self._doc(key_hash).get()
        if not snapshot.exists:
            return None
        return snapshot.get("user_id")

    async def revoke(self, key_hash: str) -> None:
        await self._doc(key_hash).delete()
