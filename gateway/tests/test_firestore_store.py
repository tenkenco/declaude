"""FirestoreUsageStore against a fake async client.

The production store held the lowest coverage of any module while owning quota, paid flags,
keys and OAuth codes: every path where a bug costs money or access.
"""
import anyio
import pytest

from declaude.usage import FirestoreUsageStore


class FakeDoc:
    def __init__(self, data=None):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data or {})

    def get(self, field):  # real snapshots expose field access as well as to_dict
        return (self._data or {}).get(field)


class FakeRef:
    def __init__(self, store, key):
        self._store, self._key = store, key
        self.id = key.split("/")[-1]

    async def get(self):
        return FakeDoc(self._store.data.get(self._key))

    async def set(self, values, merge=False):
        cur = self._store.data.get(self._key, {}) if merge else {}
        resolved = {}
        for k, v in values.items():
            if hasattr(v, "value"):  # Increment sentinel
                resolved[k] = cur.get(k, 0) + v.value
            else:
                resolved[k] = v
        self._store.data[self._key] = {**cur, **resolved}

    async def update(self, values):
        await self.set(values, merge=True)

    async def delete(self):
        self._store.data.pop(self._key, None)


class FakeQuery:
    def __init__(self, store, prefix, field, value):
        self._store, self._prefix, self._field, self._value = store, prefix, field, value

    async def stream(self):
        for key, data in list(self._store.data.items()):
            if key.startswith(self._prefix) and data.get(self._field) == self._value:
                doc = FakeDoc(data)
                doc.id = key.split("/")[-1]
                yield doc


class FakeCollection:
    def __init__(self, store, name):
        self._store, self._name = store, name

    def document(self, key):
        return FakeRef(self._store, f"{self._name}/{key}")

    def where(self, field, _op, value):
        return FakeQuery(self._store, f"{self._name}/", field, value)


class FakeDB:
    def __init__(self):
        self.data = {}

    def collection(self, name):
        return FakeCollection(self, name)


@pytest.fixture
def store():
    s = FirestoreUsageStore.__new__(FirestoreUsageStore)
    s._db = FakeDB()
    return s


def test_increment_accumulates(store):
    async def go():
        assert await store.increment("u1", "2026-08") == 1
        assert await store.increment("u1", "2026-08") == 2
        assert await store.get("u1", "2026-08") == 2
    anyio.run(go)


def test_periods_are_independent(store):
    async def go():
        await store.increment("u1", "2026-08")
        assert await store.get("u1", "2026-09") == 0
        assert await store.get("u2", "2026-08") == 0
    anyio.run(go)


def test_paid_flag_roundtrip(store):
    async def go():
        assert await store.is_paid("u1") is False
        await store.set_paid("u1", True)
        assert await store.is_paid("u1") is True
        await store.set_paid("u1", False)
        assert await store.is_paid("u1") is False
    anyio.run(go)


def test_paid_flag_survives_customer_write(store):
    """Both write users/{id}; a non-merging write would silently un-pay a customer."""
    async def go():
        await store.set_paid("u1", True)
        await store.set_stripe_customer("u1", "cus_1")
        assert await store.is_paid("u1") is True
        assert await store.get_stripe_customer("u1") == "cus_1"
    anyio.run(go)


def test_api_key_lifecycle(store):
    async def go():
        await store.add_api_key("hash1", "u1", "dk_ab…yz")
        assert await store.get_user_for_key("hash1") == "u1"
        keys = await store.list_api_keys("u1")
        assert len(keys) == 1 and keys[0]["prefix"] == "dk_ab…yz" and keys[0]["id"] == "hash1"
        assert await store.delete_api_key("u1", "hash1") is True
        assert await store.get_user_for_key("hash1") is None
    anyio.run(go)


def test_cannot_delete_another_users_key(store):
    async def go():
        await store.add_api_key("hash1", "owner")
        assert await store.delete_api_key("attacker", "hash1") is False
        assert await store.get_user_for_key("hash1") == "owner"
    anyio.run(go)


def test_keys_are_listed_per_user(store):
    async def go():
        await store.add_api_key("h1", "u1")
        await store.add_api_key("h2", "u1")
        await store.add_api_key("h3", "u2")
        assert len(await store.list_api_keys("u1")) == 2
        assert len(await store.list_api_keys("u2")) == 1
    anyio.run(go)


def test_oauth_code_is_single_use(store):
    async def go():
        await store.put_oauth_code("codehash", {"user_id": "u1"})
        assert (await store.pop_oauth_code("codehash"))["user_id"] == "u1"
        assert await store.pop_oauth_code("codehash") is None
    anyio.run(go)


def test_oauth_client_roundtrip(store):
    async def go():
        await store.put_oauth_client("cli_1", '{"name": "Claude Code"}')
        assert "Claude Code" in await store.get_oauth_client("cli_1")
        assert await store.get_oauth_client("cli_missing") is None
    anyio.run(go)


def test_missing_user_has_no_customer(store):
    async def go():
        assert await store.get_stripe_customer("nobody") is None
    anyio.run(go)
