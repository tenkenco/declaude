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
    async def add_api_key(self, key_hash: str, user_id: str, prefix: str = "") -> None: ...
    @abstractmethod
    async def list_api_keys(self, user_id: str) -> list[dict]: ...
    @abstractmethod
    async def delete_api_key(self, user_id: str, key_hash: str) -> bool: ...
    @abstractmethod
    async def put_oauth_code(self, code_hash: str, data: dict) -> None: ...
    @abstractmethod
    async def pop_oauth_code(self, code_hash: str) -> dict | None: ...
    @abstractmethod
    async def put_oauth_client(self, client_id: str, name: str) -> None: ...
    @abstractmethod
    async def get_oauth_client(self, client_id: str) -> str | None: ...


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

    async def add_api_key(self, key_hash: str, user_id: str, prefix: str = "") -> None:
        self._keys[key_hash] = user_id
        self._key_meta = getattr(self, "_key_meta", {})
        self._key_meta[key_hash] = {"prefix": prefix, "created_at": __import__("time").time()}

    async def list_api_keys(self, user_id: str) -> list[dict]:
        meta = getattr(self, "_key_meta", {})
        return [{"id": h, **meta.get(h, {"prefix": "", "created_at": 0})}
                for h, uid in self._keys.items() if uid == user_id]

    async def delete_api_key(self, user_id: str, key_hash: str) -> bool:
        if self._keys.get(key_hash) != user_id:
            return False
        del self._keys[key_hash]
        getattr(self, "_key_meta", {}).pop(key_hash, None)
        return True

    async def put_oauth_code(self, code_hash: str, data: dict) -> None:
        self._codes = getattr(self, "_codes", {})
        self._codes[code_hash] = data

    async def pop_oauth_code(self, code_hash: str) -> dict | None:
        self._codes = getattr(self, "_codes", {})
        return self._codes.pop(code_hash, None)

    async def put_oauth_client(self, client_id: str, name: str) -> None:
        self._clients = getattr(self, "_clients", {})
        self._clients[client_id] = name

    async def get_oauth_client(self, client_id: str) -> str | None:
        return getattr(self, "_clients", {}).get(client_id)


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

    async def add_api_key(self, key_hash: str, user_id: str, prefix: str = "") -> None:
        import time as _time

        await self._db.collection("apikeys").document(key_hash).set(
            {"user_id": user_id, "prefix": prefix, "created_at": _time.time()})

    async def list_api_keys(self, user_id: str) -> list[dict]:
        q = self._db.collection("apikeys").where("user_id", "==", user_id)
        out = []
        async for doc in q.stream():
            d = doc.to_dict()
            out.append({"id": doc.id, "prefix": d.get("prefix", ""),
                        "created_at": d.get("created_at", 0)})
        return sorted(out, key=lambda x: x["created_at"])

    async def delete_api_key(self, user_id: str, key_hash: str) -> bool:
        ref = self._db.collection("apikeys").document(key_hash)
        snap = await ref.get()
        if not snap.exists or snap.to_dict().get("user_id") != user_id:
            return False
        await ref.delete()
        return True

    async def put_oauth_code(self, code_hash: str, data: dict) -> None:
        await self._db.collection("oauth_codes").document(code_hash).set(data)

    async def pop_oauth_code(self, code_hash: str) -> dict | None:
        ref = self._db.collection("oauth_codes").document(code_hash)
        snapshot = await ref.get()
        if not snapshot.exists:
            return None
        await ref.delete()  # single-use; PKCE binding is the hard security boundary
        return snapshot.to_dict()

    async def put_oauth_client(self, client_id: str, name: str) -> None:
        await self._db.collection("oauth_clients").document(client_id).set({"name": name})

    async def get_oauth_client(self, client_id: str) -> str | None:
        snap = await self._db.collection("oauth_clients").document(client_id).get()
        return snap.to_dict().get("name") if snap.exists else None
