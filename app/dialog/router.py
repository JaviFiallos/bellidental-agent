from unicodedata import combining, normalize

from app.backend.models import BackendError
from app.dialog.consent import CONSENT_NO_ID, CONSENT_YES_ID, answer_consent, build_notice, is_accepted
from app.dialog.dependencies import Backend
from app.dialog.handoff import is_handoff_active
from app.dialog.menu import MENU_PREFIX, answer_menu, show_menu
from app.dialog.models import Conversation, IncomingMessage, OutgoingMessage, TextMessage
from app.dialog.store import peek_clinic_info
from app.messages.texts import UNSUPPORTED_MESSAGE, technical_problem_text

MENU_KEYWORD = "menu"


def _normalize_text(text: str) -> str:
    decomposed = normalize("NFKD", text.strip().lower())
    return "".join(char for char in decomposed if not combining(char))


def _is_menu_request(incoming: IncomingMessage) -> bool:
    if incoming.reply_id is not None and incoming.reply_id.startswith(MENU_PREFIX):
        return True
    return incoming.text is not None and _normalize_text(incoming.text) == MENU_KEYWORD


async def handle(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    """Handles an incoming message, updates conversation state, and returns outgoing messages."""
    if incoming.text:
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
        return [TextMessage(text=UNSUPPORTED_MESSAGE), *await show_menu(conversation)]

    if incoming.reply_id is not None and incoming.reply_id.startswith(MENU_PREFIX):
        return await answer_menu(incoming.reply_id, conversation, backend)
    return await show_menu(conversation)
