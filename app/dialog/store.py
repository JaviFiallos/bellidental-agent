from collections import OrderedDict
from datetime import datetime, timedelta, timezone

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
