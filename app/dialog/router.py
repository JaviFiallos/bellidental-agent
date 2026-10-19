from unicodedata import combining, normalize

from app.backend.models import BackendError
from app.dialog import booking, identify, menu
from app.dialog.consent import CONSENT_NO_ID, CONSENT_YES_ID, answer_consent, build_notice, is_accepted
from app.dialog.dependencies import Backend
from app.dialog.handoff import is_handoff_active
from app.dialog.menu import MENU_PREFIX, answer_menu, show_menu
from app.dialog.models import Conversation, IncomingMessage, OutgoingMessage, Step, TextMessage
from app.dialog.store import peek_clinic_info
from app.messages.texts import UNSUPPORTED_MESSAGE, technical_problem_text

MENU_KEYWORD = "menu"
IDENTIFY_STEPS = frozenset({Step.IDENTIFY_CONFIRM, Step.IDENTIFY_ID})
BOOKING_STEPS = frozenset(
    {
        Step.BOOK_SPECIALTY,
        Step.BOOK_PROFESSIONAL,
        Step.BOOK_DAY,
        Step.BOOK_SLOT,
        Step.BOOK_CONFIRM,
    }
)
FLOW_STEPS = IDENTIFY_STEPS | BOOKING_STEPS


def _normalize_text(text: str) -> str:
    decomposed = normalize("NFKD", text.strip().lower())
    return "".join(char for char in decomposed if not combining(char))


def _is_menu_text(incoming: IncomingMessage) -> bool:
    return incoming.text is not None and _normalize_text(incoming.text) == MENU_KEYWORD


def _is_menu_request(incoming: IncomingMessage) -> bool:
    if incoming.reply_id is not None and incoming.reply_id.startswith(MENU_PREFIX):
        return True
    return _is_menu_text(incoming)


async def handle(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    """Handles an incoming message, updates conversation state, and returns outgoing messages."""
    # The cédula typed during identification is not conversation text: it stays out of history.
    if incoming.text and conversation.step != Step.IDENTIFY_ID:
        conversation.history.append(incoming.text)
        conversation.history = conversation.history[-6:]

    try:
        return await _route(incoming, conversation, backend)
    except BackendError:
        info = peek_clinic_info(backend)
        reception_whatsapp = info.reception_whatsapp if info is not None else ""
        return [TextMessage(text=technical_problem_text(reception_whatsapp))]


async def _route(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if is_handoff_active(conversation):
        if not _is_menu_request(incoming):
            return []
        conversation.handoff_until = None

    if not await is_accepted(conversation, backend):
        if incoming.reply_id in (CONSENT_YES_ID, CONSENT_NO_ID):
            return await answer_consent(incoming.reply_id, conversation, backend)
        return build_notice(conversation)

    if incoming.kind == "unsupported":
        return [TextMessage(text=UNSUPPORTED_MESSAGE), *await booking.cancel_flow(conversation)]

    if conversation.step in FLOW_STEPS:
        if _is_menu_text(incoming):
            return await booking.cancel_flow(conversation)
        if conversation.step in IDENTIFY_STEPS:
            return await identify.answer_identification(incoming, conversation, backend)
        return await booking.answer_booking(incoming, conversation, backend)

    if incoming.reply_id == menu.BOOK_ID:
        return await booking.start(conversation, backend)
    if incoming.reply_id is not None and incoming.reply_id.startswith(MENU_PREFIX):
        return await answer_menu(incoming.reply_id, conversation, backend)
    return await show_menu(conversation)
