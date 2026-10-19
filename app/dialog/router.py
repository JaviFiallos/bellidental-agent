from app.backend.models import BackendError
from app.dialog import appointments, booking, free_text, identify, menu, reminder_reply, urgent
from app.dialog.consent import CONSENT_NO_ID, CONSENT_YES_ID, answer_consent, build_notice, is_accepted
from app.dialog.dependencies import Backend, Classifier
from app.dialog.hints import normalize_text
from app.dialog.handoff import is_handoff_active
from app.dialog.menu import MENU_PREFIX, answer_menu, show_menu
from app.dialog.models import Conversation, IncomingMessage, OutgoingMessage, Step, TextMessage
from app.dialog.store import peek_clinic_info
from app.messages.texts import UNSUPPORTED_MESSAGE, technical_problem_text
from app.nlu.classifier import DisabledClassifier

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
APPOINTMENT_STEPS = frozenset(
    {
        Step.APPT_CHOOSE,
        Step.APPT_ACTION,
        Step.RESCHEDULE_DAY,
        Step.RESCHEDULE_SLOT,
        Step.RESCHEDULE_CONFIRM,
        Step.CANCEL_CONFIRM,
    }
)
URGENT_STEPS = frozenset({Step.URGENT_SLOT, Step.URGENT_CONFIRM})
FLOW_STEPS = IDENTIFY_STEPS | BOOKING_STEPS | APPOINTMENT_STEPS | URGENT_STEPS


def _is_menu_text(incoming: IncomingMessage) -> bool:
    return incoming.text is not None and normalize_text(incoming.text) == MENU_KEYWORD


def _is_menu_request(incoming: IncomingMessage) -> bool:
    if incoming.reply_id is not None and incoming.reply_id.startswith(MENU_PREFIX):
        return True
    return _is_menu_text(incoming)


async def handle(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
    classifier: Classifier | None = None,
) -> list[OutgoingMessage]:
    """Handles an incoming message, updates conversation state, and returns outgoing messages."""
    # The cédula typed during identification is not conversation text: it stays out of history.
    if incoming.text and conversation.step != Step.IDENTIFY_ID:
        conversation.history.append(incoming.text)
        conversation.history = conversation.history[-6:]

    try:
        return await _route(incoming, conversation, backend, classifier or DisabledClassifier())
    except BackendError:
        info = peek_clinic_info(backend)
        reception_whatsapp = info.reception_whatsapp if info is not None else ""
        return [TextMessage(text=technical_problem_text(reception_whatsapp))]


async def _route(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
    classifier: Classifier,
) -> list[OutgoingMessage]:
    # Reminder buttons are always answered, even during handoff or an unfinished flow (017b).
    if incoming.kind == "template_button":
        return await reminder_reply.answer_reminder_button(incoming, conversation, backend)

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
        if incoming.kind == "text" and conversation.step != Step.IDENTIFY_ID:
            interrupted = await free_text.interrupt_flow(incoming, conversation, backend, classifier)
            if interrupted is not None:
                return interrupted
        return await _answer_flow(incoming, conversation, backend)

    if incoming.reply_id == menu.BOOK_ID:
        return await booking.start(conversation, backend)
    if incoming.reply_id == menu.APPOINTMENTS_ID:
        return await appointments.start(conversation, backend)
    if incoming.reply_id is not None and incoming.reply_id.startswith(MENU_PREFIX):
        return await answer_menu(incoming.reply_id, conversation, backend)
    if incoming.kind == "text" and not _is_menu_text(incoming):
        return await free_text.answer_free_text(incoming, conversation, backend, classifier)
    return await show_menu(conversation)


async def _answer_flow(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if conversation.step in IDENTIFY_STEPS:
        return await identify.answer_identification(incoming, conversation, backend)
    if conversation.step in BOOKING_STEPS:
        return await booking.answer_booking(incoming, conversation, backend)
    if conversation.step in URGENT_STEPS:
        return await urgent.answer_urgent(incoming, conversation, backend)
    return await appointments.answer_appointments(incoming, conversation, backend)
