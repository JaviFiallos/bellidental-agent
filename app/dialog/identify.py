from collections.abc import Awaitable, Callable

from app.backend.models import BackendError
from app.dialog.dependencies import Backend
from app.dialog.handoff import hand_off_from_backend
from app.dialog.models import (
    ButtonAction,
    ButtonsMessage,
    Conversation,
    IncomingMessage,
    OutgoingMessage,
    Step,
    TextMessage,
)
from app.messages.texts import (
    FIRST_APPOINTMENT_TEXT,
    IDENTIFY_ASK_ID_TEXT,
    IDENTIFY_ID_RETRY_TEXT,
    IDENTIFY_NO_TITLE,
    IDENTIFY_YES_TITLE,
    identify_confirm_text,
)

IDENTIFY_YES_ID = "ident:yes"
IDENTIFY_NO_ID = "ident:no"
MAX_ID_ATTEMPTS = 2

Continuation = Callable[[Conversation, Backend], Awaitable[list[OutgoingMessage]]]
_continuations: dict[str, Continuation] = {}


def register_continuation(name: str, continuation: Continuation) -> None:
    """Registers the flow that runs once the patient is identified (e.g. 'book')."""
    _continuations[name] = continuation


async def start_identification(
    conversation: Conversation,
    backend: Backend,
    then: str,
) -> list[OutgoingMessage]:
    """Identifies the patient by phone (and cédula if needed), then runs the continuation named `then`."""
    if conversation.patient_id is not None:
        return await _continuations[then](conversation, backend)

    patients = await backend.get_patients(conversation.phone)
    conversation.selection = {"then": then}
    if not patients:
        return [TextMessage(text=FIRST_APPOINTMENT_TEXT), *await hand_off_from_backend(conversation, backend)]
    if len(patients) == 1:
        conversation.selection["candidate_id"] = patients[0].patient_id
        conversation.selection["candidate_name"] = patients[0].display_name
        conversation.step = Step.IDENTIFY_CONFIRM
        return [_confirm_message(patients[0].display_name)]

    conversation.step = Step.IDENTIFY_ID
    conversation.selection["id_attempts"] = 0
    return [TextMessage(text=IDENTIFY_ASK_ID_TEXT)]


async def answer_identification(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if conversation.step == Step.IDENTIFY_CONFIRM:
        return await _answer_confirm(incoming, conversation, backend)
    return await _answer_id_number(incoming.text, conversation, backend)


def _confirm_message(patient_name: str) -> ButtonsMessage:
    return ButtonsMessage(
        text=identify_confirm_text(patient_name),
        buttons=[
            ButtonAction(id=IDENTIFY_YES_ID, title=IDENTIFY_YES_TITLE),
            ButtonAction(id=IDENTIFY_NO_ID, title=IDENTIFY_NO_TITLE),
        ],
    )


async def _answer_confirm(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if incoming.reply_id == IDENTIFY_YES_ID:
        return await _set_patient(
            conversation,
            backend,
            patient_id=str(conversation.selection["candidate_id"]),
            patient_name=str(conversation.selection["candidate_name"]),
        )
    if incoming.reply_id == IDENTIFY_NO_ID:
        return await hand_off_from_backend(conversation, backend)
    return [_confirm_message(str(conversation.selection["candidate_name"]))]


async def _answer_id_number(
    text: str | None,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if not text or not text.strip():
        return [TextMessage(text=IDENTIFY_ASK_ID_TEXT)]
    try:
        patient = await backend.verify_patient(conversation.phone, text.strip())
    except BackendError:
        attempts = int(conversation.selection.get("id_attempts", 0)) + 1
        if attempts >= MAX_ID_ATTEMPTS:
            return await hand_off_from_backend(conversation, backend)
        conversation.selection["id_attempts"] = attempts
        return [TextMessage(text=IDENTIFY_ID_RETRY_TEXT)]
    return await _set_patient(
        conversation,
        backend,
        patient_id=patient.patient_id,
        patient_name=patient.display_name,
    )


async def _set_patient(
    conversation: Conversation,
    backend: Backend,
    patient_id: str,
    patient_name: str,
) -> list[OutgoingMessage]:
    then = str(conversation.selection["then"])
    conversation.patient_id = patient_id
    conversation.patient_name = patient_name
    conversation.selection = {"then": then}
    return await _continuations[then](conversation, backend)
