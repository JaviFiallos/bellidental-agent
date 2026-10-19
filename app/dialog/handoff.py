from datetime import datetime, timedelta, timezone

from app.backend.models import ClinicInfo
from app.dialog.models import Conversation, OutgoingMessage, Step, TextMessage
from app.messages.texts import handoff_text, technical_problem_text

HANDOFF_DURATION = timedelta(hours=4)


def is_handoff_active(conversation: Conversation) -> bool:
    return conversation.handoff_until is not None and conversation.handoff_until > datetime.now(timezone.utc)


def hand_off(conversation: Conversation, info: ClinicInfo | None) -> list[OutgoingMessage]:
    """Hands the conversation over to reception for 4 hours and returns the handoff message."""
    conversation.handoff_until = datetime.now(timezone.utc) + HANDOFF_DURATION
    conversation.step = Step.IDLE
    conversation.selection = {}
    text = handoff_text(info) if info is not None else technical_problem_text("")
    return [TextMessage(text=text)]
