"""Per-user, per-month usage metering and paid-plan flags.
InMemory for tests/dev; Firestore-backed implementation used in production."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone


def current_period() -> str:
    now = datetime.now(timezone.utc)
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


class InMemoryUsageStore(UsageStore):
    def __init__(self):
        self._counts: dict[tuple[str, str], int] = {}
        self._paid: set[str] = set()

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
