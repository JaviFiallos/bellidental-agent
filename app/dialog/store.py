from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from weakref import WeakKeyDictionary

from app.backend.models import ClinicInfo
from app.dialog.dependencies import Backend
from app.dialog.models import Conversation


class ProcessedMessages:
    """In-memory cache keeping track of the last 1000 seen message IDs to deduplicate webhook events."""

    def __init__(self, max_size: int = 1000) -> None:
        self._max_size = max_size
        self._seen: OrderedDict[str, None] = OrderedDict()

    def has(self, message_id: str) -> bool:
        return message_id in self._seen

    def add(self, message_id: str) -> None:
        if message_id in self._seen:
            return
        if len(self._seen) >= self._max_size:
            self._seen.popitem(last=False)
        self._seen[message_id] = None


class ConversationStore:
    """In-memory conversation store with TTL expiration."""

    def __init__(self, ttl_minutes: int = 30) -> None:
        self.ttl = timedelta(minutes=ttl_minutes)
        self._conversations: dict[str, Conversation] = {}

    def get(self, phone: str) -> Conversation:
        now = datetime.now(timezone.utc)
        conversation = self._conversations.get(phone)
        if conversation is not None:
            if now - conversation.updated_at > self.ttl:
                conversation = Conversation(phone=phone, updated_at=now)
                self._conversations[phone] = conversation
        else:
            conversation = Conversation(phone=phone, updated_at=now)
            self._conversations[phone] = conversation
        return conversation

    def save(self, conversation: Conversation) -> None:
        conversation.updated_at = datetime.now(timezone.utc)
        self._conversations[conversation.phone] = conversation

    def discard(self, phone: str) -> None:
        self._conversations.pop(phone, None)


class ClinicInfoCache:
    """Caches the clinic /info for 10 minutes. Returns None when the backend fails."""

    def __init__(self, ttl_minutes: int = 10) -> None:
        self.ttl = timedelta(minutes=ttl_minutes)
        self._info: ClinicInfo | None = None
        self._fetched_at: datetime | None = None

    def last_info(self) -> ClinicInfo | None:
        return self._info

    async def get(self, backend: Backend) -> ClinicInfo | None:
        now = datetime.now(timezone.utc)
        if self._info is not None and self._fetched_at is not None and now - self._fetched_at <= self.ttl:
            return self._info
        try:
            info = await backend.get_info()
        except Exception:
            return self._info
        self._info = info
        self._fetched_at = now
        return info


_clinic_info_caches: WeakKeyDictionary[Backend, ClinicInfoCache] = WeakKeyDictionary()


def peek_clinic_info(backend: Backend) -> ClinicInfo | None:
    """Returns the last cached clinic info for this backend without calling it, even if stale."""
    cache = _clinic_info_caches.get(backend)
    return cache.last_info() if cache is not None else None


async def load_clinic_info(backend: Backend) -> ClinicInfo | None:
    """Returns the cached clinic info for this backend, fetching it when stale."""
    cache = _clinic_info_caches.get(backend)
    if cache is None:
        cache = ClinicInfoCache()
        _clinic_info_caches[backend] = cache
    return await cache.get(backend)
