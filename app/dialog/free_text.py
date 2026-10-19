from app.dialog import appointments, booking, urgent
from app.dialog.dependencies import Backend
from app.dialog.handoff import hand_off_from_backend
from app.dialog.hints import matches_text
from app.dialog.menu import HOURS_ID, PRICES_ID, answer_menu, show_menu
from app.dialog.models import Conversation, IncomingMessage, OutgoingMessage, Step, TextMessage
from app.dialog.store import load_clinic_info
from app.messages.texts import OFF_TOPIC_TEXT, single_price_text, technical_problem_text
from app.nlu.classifier import Classifier
from app.nlu.models import Intent, Interpretation

MAX_RECENT_TEXTS = 2
MAX_UNKNOWN_BEFORE_HANDOFF = 2
FLOW_INTERRUPTS = frozenset({Intent.URGENT, Intent.HUMAN, Intent.CLINICAL, Intent.BALANCE})


async def _interpret(
    incoming: IncomingMessage,
    conversation: Conversation,
    classifier: Classifier,
) -> Interpretation | None:
    # history already holds the current text as its last item; the LLM only sees the texts before it.
    recent = conversation.history[:-1][-MAX_RECENT_TEXTS:]
    return await classifier.classify(incoming.text or "", conversation.step, recent)


async def interrupt_flow(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
    classifier: Classifier,
) -> list[OutgoingMessage] | None:
    """Mid-flow: only urgent, human, clinical and balance messages leave the flow. Others return None."""
    interpretation = await _interpret(incoming, conversation, classifier)
    if interpretation is None or interpretation.intent not in FLOW_INTERRUPTS:
        return None
    conversation.step = Step.IDLE
    conversation.selection = {}
    conversation.unknown_count = 0
    return await _act(interpretation, conversation, backend)


async def answer_free_text(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
    classifier: Classifier,
) -> list[OutgoingMessage]:
    interpretation = await _interpret(incoming, conversation, classifier)
    if interpretation is None:
        return await show_menu(conversation)
    if interpretation.intent == Intent.OTHER:
        conversation.unknown_count += 1
        if conversation.unknown_count >= MAX_UNKNOWN_BEFORE_HANDOFF:
            conversation.unknown_count = 0
            return await hand_off_from_backend(conversation, backend)
        return [TextMessage(text=OFF_TOPIC_TEXT), *await show_menu(conversation)]
    conversation.unknown_count = 0
    return await _act(interpretation, conversation, backend)


async def _act(interpretation: Interpretation, conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    match interpretation.intent:
        case Intent.HOURS:
            return await answer_menu(HOURS_ID, conversation, backend)
        case Intent.PRICE:
            return await _answer_price(interpretation.treatment, conversation, backend)
        case Intent.BOOK:
            return await booking.start(conversation, backend, hints=_booking_hints(interpretation))
        case Intent.RESCHEDULE:
            return await appointments.start(conversation, backend, action=appointments.RESCHEDULE_ID)
        case Intent.CANCEL:
            return await appointments.start(conversation, backend, action=appointments.CANCEL_ID)
        case Intent.CONFIRM:
            return await appointments.start(conversation, backend, action=appointments.CONFIRM_ID)
        case Intent.URGENT:
            return await urgent.start(conversation, backend)
        case Intent.CLINICAL | Intent.BALANCE | Intent.HUMAN:
            return await hand_off_from_backend(conversation, backend)
        case _:
            return await show_menu(conversation)


async def _answer_price(treatment: str | None, conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    info = await load_clinic_info(backend)
    if info is None:
        return [TextMessage(text=technical_problem_text(""))]
    if treatment:
        match = next((price for price in info.prices if matches_text(treatment, price.name)), None)
        if match is not None:
            return [TextMessage(text=single_price_text(match)), *await show_menu(conversation)]
    return await answer_menu(PRICES_ID, conversation, backend)


def _booking_hints(interpretation: Interpretation) -> dict[str, str]:
    values = {
        "specialty": interpretation.specialty,
        "date": interpretation.date_hint,
        "time": interpretation.time_hint,
    }
    return {key: value for key, value in values.items() if value}
