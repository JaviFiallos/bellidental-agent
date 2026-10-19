from app.backend.models import BackendError, ReminderResponse
from app.dialog import appointments
from app.dialog.dependencies import Backend
from app.dialog.handoff import hand_off_from_backend
from app.dialog.menu import show_menu
from app.dialog.models import Conversation, IncomingMessage, OutgoingMessage, TextMessage
from app.messages.texts import APPOINTMENT_CANCELLED_TEXT, REMINDER_CONFIRMED_TEXT, REMINDER_TOO_LATE_TEXT

CONFIRM_PAYLOAD = "reminder:confirm"
CANCEL_PAYLOAD = "reminder:cancel"
RESCHEDULE_PAYLOAD = "reminder:reschedule"
REMINDER_PAYLOADS = (CONFIRM_PAYLOAD, CANCEL_PAYLOAD, RESCHEDULE_PAYLOAD)

RESPONSES_BY_PAYLOAD = {
    CONFIRM_PAYLOAD: "CONFIRMED",
    CANCEL_PAYLOAD: "CANCELLED",
    RESCHEDULE_PAYLOAD: "RESCHEDULED",
}
NOT_FOUND_STATUS = 404
RESCHEDULE_REQUESTED = "RESCHEDULE_REQUESTED"
TOO_LATE = "TOO_LATE"
CANCELLED = "CANCELLED"
CONFIRMED = "CONFIRMED"


async def answer_reminder_button(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    # A reminder reply restarts the conversation with the bot: an earlier handoff no longer blocks the next replies.
    conversation.handoff_until = None
    response = RESPONSES_BY_PAYLOAD.get(incoming.reply_id or "")
    if response is None or incoming.context_message_id is None:
        return await show_menu(conversation)
    try:
        result = await backend.send_reminder_response(
            wa_message_id=incoming.context_message_id,
            phone=incoming.phone,
            response=response,
        )
    except BackendError as exc:
        if exc.status == NOT_FOUND_STATUS:
            return await show_menu(conversation)
        raise
    return await _answer_outcome(result, conversation, backend)


async def _answer_outcome(
    result: ReminderResponse,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if result.outcome == CONFIRMED:
        return [TextMessage(text=REMINDER_CONFIRMED_TEXT)]
    if result.outcome == CANCELLED:
        return [TextMessage(text=APPOINTMENT_CANCELLED_TEXT), *await show_menu(conversation)]
    if result.outcome == RESCHEDULE_REQUESTED:
        return await _start_reschedule(result, conversation, backend)
    if result.outcome == TOO_LATE:
        return [TextMessage(text=REMINDER_TOO_LATE_TEXT), *await hand_off_from_backend(conversation, backend)]
    return await show_menu(conversation)


async def _start_reschedule(
    result: ReminderResponse,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    conversation.patient_id = result.patient_id
    appointments_list = await backend.get_appointments(phone=conversation.phone, patient_id=result.patient_id)
    for appointment in appointments_list:
        if appointment.appointment_id == result.appointment_id:
            return await appointments.start_reschedule(conversation, appointment, backend)
    return await show_menu(conversation)
