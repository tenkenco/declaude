"""Per-user, per-month usage metering and paid-plan flags.
InMemory for tests/dev; Firestore-backed implementation used in production."""
from abc import ABC, abstractmethod
from datetime import UTC, datetime


def current_period() -> str:
    now = datetime.now(UTC)
    return f"{now.year:04d}-{now.month:02d}"


class UsageStore(ABC):
    @abstractmethod
    async def increment(self, user_id: str, period: str) -> int: ...
    @abstractmethod
    async def get(self, user_id: str, period: str) -> int: ...
    @abstractmethod
    async def is_paid(self, user_id: str) -> bool: ...
    @abstractmethod
    async def set_paid(self, user_id: str, paid: bool) -> None: ...
    @abstractmethod
    async def get_user_for_key(self, key_hash: str) -> str | None: ...
    @abstractmethod
    async def add_api_key(self, key_hash: str, user_id: str) -> None: ...
    @abstractmethod
    async def put_oauth_code(self, code_hash: str, data: dict) -> None: ...
    @abstractmethod
    async def pop_oauth_code(self, code_hash: str) -> dict | None: ...


class InMemoryUsageStore(UsageStore):
    def __init__(self):
        self._counts: dict[tuple[str, str], int] = {}
        self._paid: set[str] = set()
        self._keys: dict[str, str] = {}

    async def increment(self, user_id: str, period: str) -> int:
        key = (user_id, period)
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def get(self, user_id: str, period: str) -> int:
        return self._counts.get((user_id, period), 0)

    async def is_paid(self, user_id: str) -> bool:
        return user_id in self._paid

    async def set_paid(self, user_id: str, paid: bool) -> None:
        (self._paid.add if paid else self._paid.discard)(user_id)

    # sync helpers for tests
    def get_sync(self, user_id: str, period: str | None = None) -> int:
        return self._counts.get((user_id, period or current_period()), 0)

    def mark_paid_sync(self, user_id: str) -> None:
        self._paid.add(user_id)

    async def get_user_for_key(self, key_hash: str) -> str | None:
        return self._keys.get(key_hash)

    def add_api_key_sync(self, key_hash: str, user_id: str) -> None:
        self._keys[key_hash] = user_id

    async def add_api_key(self, key_hash: str, user_id: str) -> None:
        self._keys[key_hash] = user_id

    async def put_oauth_code(self, code_hash: str, data: dict) -> None:
        self._codes = getattr(self, "_codes", {})
        self._codes[code_hash] = data

    async def pop_oauth_code(self, code_hash: str) -> dict | None:
        self._codes = getattr(self, "_codes", {})
        return self._codes.pop(code_hash, None)


class FirestoreUsageStore(UsageStore):
    """Firestore-backed store: `usage/{user_id}:{period}` counters, `users/{user_id}` paid flags.

    Accepts a google.cloud.firestore.AsyncClient (or a duck-typed fake in tests)."""

    def __init__(self, client):
        self._db = client

    def _usage_doc(self, user_id: str, period: str):
        return self._db.collection("usage").document(f"{user_id}:{period}")

    async def increment(self, user_id: str, period: str) -> int:
        from google.cloud.firestore_v1.transforms import Increment

        ref = self._usage_doc(user_id, period)
        await ref.set({"count": Increment(1)}, merge=True)
        snapshot = await ref.get()
        return snapshot.get("count") or 0

    async def get(self, user_id: str, period: str) -> int:
        snapshot = await self._usage_doc(user_id, period).get()
        if not snapshot.exists:
            return 0
        return snapshot.get("count") or 0

    async def is_paid(self, user_id: str) -> bool:
        snapshot = await self._db.collection("users").document(user_id).get()
        return bool(snapshot.exists and snapshot.get("paid"))

    async def set_paid(self, user_id: str, paid: bool) -> None:
        await self._db.collection("users").document(user_id).set({"paid": paid}, merge=True)

    async def get_user_for_key(self, key_hash: str) -> str | None:
        snapshot = await self._db.collection("apikeys").document(key_hash).get()
        if not snapshot.exists:
            return None
        return snapshot.get("user_id")

    async def add_api_key(self, key_hash: str, user_id: str) -> None:
        await self._db.collection("apikeys").document(key_hash).set({"user_id": user_id})

    async def put_oauth_code(self, code_hash: str, data: dict) -> None:
        await self._db.collection("oauth_codes").document(code_hash).set(data)

    async def pop_oauth_code(self, code_hash: str) -> dict | None:
        ref = self._db.collection("oauth_codes").document(code_hash)
        snapshot = await ref.get()
        if not snapshot.exists:
            return None
        await ref.delete()  # single-use; PKCE binding is the hard security boundary
        return snapshot.to_dict()
