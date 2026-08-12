"""FirestoreUsageStore contract tests against an in-memory fake of the Firestore AsyncClient."""
import pytest
from google.cloud.firestore_v1.transforms import Increment

from declaude.usage import FirestoreUsageStore


class FakeSnapshot:
    def __init__(self, data):
        self._data = data

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None

    def get(self, field):
        return (self._data or {}).get(field)


class FakeDocument:
    def __init__(self, store, path):
        self._store, self._path = store, path

    async def set(self, data, merge=False):
        current = self._store.get(self._path, {}) if merge else {}
        current = dict(current)
        for k, v in data.items():
            if isinstance(v, Increment):
                current[k] = current.get(k, 0) + v.value
            else:
                current[k] = v
        self._store[self._path] = current

    async def get(self):
        return FakeSnapshot(self._store.get(self._path))


class FakeCollection:
    def __init__(self, store, name):
        self._store, self._name = store, name

    def document(self, doc_id):
        return FakeDocument(self._store, f"{self._name}/{doc_id}")


class FakeFirestoreClient:
    def __init__(self):
        self.data: dict[str, dict] = {}

    def collection(self, name):
        return FakeCollection(self.data, name)


@pytest.fixture
def db():
    return FakeFirestoreClient()


@pytest.fixture
def store(db):
    return FirestoreUsageStore(db)


async def test_get_defaults_to_zero(store):
    assert await store.get("user_123", "2025-01") == 0


async def test_increment_returns_new_count(store):
    assert await store.increment("user_123", "2025-01") == 1
    assert await store.increment("user_123", "2025-01") == 2
    assert await store.get("user_123", "2025-01") == 2


async def test_increment_uses_expected_doc_layout(store, db):
    await store.increment("user_123", "2025-01")
    assert db.data["usage/user_123:2025-01"] == {"count": 1}


async def test_counts_isolated_per_user_and_period(store):
    await store.increment("user_a", "2025-01")
    assert await store.get("user_b", "2025-01") == 0
    assert await store.get("user_a", "2025-02") == 0


async def test_is_paid_defaults_false(store):
    assert await store.is_paid("user_123") is False


async def test_set_paid_roundtrip(store, db):
    await store.set_paid("user_123", True)
    assert await store.is_paid("user_123") is True
    assert db.data["users/user_123"] == {"paid": True}
    await store.set_paid("user_123", False)
    assert await store.is_paid("user_123") is False
