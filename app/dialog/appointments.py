from datetime import date, datetime

from app.backend.models import Appointment, BackendError
from app.dialog.booking import cancel_flow
from app.dialog.dependencies import Backend
from app.dialog.handoff import hand_off_from_backend
from app.dialog.identify import register_continuation, start_identification
from app.dialog.menu import BOOK_ID, show_menu
from app.dialog.models import (
    MAX_ROW_DESCRIPTION,
    MAX_ROW_TITLE,
    MAX_ROWS,
    ButtonAction,
    ButtonsMessage,
    Conversation,
    IncomingMessage,
    ListMessage,
    ListRow,
    ListSection,
    OutgoingMessage,
    Step,
    TextMessage,
)
from app.dialog.slot_picker import (
    DAY_PREFIX,
    SLOT_PREFIX,
    build_day_list,
    build_slot_list,
    make_slot_row_id,
    parse_slot_row_id,
)
from app.messages.dates import format_day_time, format_long
from app.messages.texts import (
    APPOINTMENT_CANCEL_TITLE,
    APPOINTMENT_CANCELLED_TEXT,
    APPOINTMENT_CONFIRMED_TEXT,
    APPOINTMENT_TOO_LATE_TEXT,
    APPOINTMENTS_BOOK_TITLE,
    APPOINTMENTS_HOME_TITLE,
    APPOINTMENTS_LIST_TEXT,
    BOOK_CANCEL_TITLE,
    BOOK_CONFIRM_TITLE,
    BOOK_NO_DAYS_TEXT,
    BOOK_NO_SLOTS_TEXT,
    BOOK_OVERLAP_TEXT,
    CANCEL_NO_TITLE,
    CANCEL_YES_TITLE,
    LIST_BUTTON_TEXT,
    NO_APPOINTMENTS_TEXT,
    RESCHEDULE_TITLE,
    booking_summary_text,
    cancel_ask_text,
    fit_length,
    reschedule_success_text,
    reschedule_summary_text,
)

APPOINTMENTS_FLOW = "appointments"
ROW_PREFIX = "appt:"
RESCHEDULE_ID = "appt:reschedule"
CANCEL_ID = "appt:cancel"
CONFIRM_ID = "appt:confirm"
CANCEL_YES_ID = "cancel:yes"
CANCEL_NO_ID = "cancel:no"
RESCHEDULE_CONFIRM_ID = "resched:confirm"
RESCHEDULE_CANCEL_ID = "resched:cancel"
HOME_ID = "menu:home"
PENDING_STATUS = "PENDING"
TOO_LATE_CODE = "BOT_TOO_LATE"
OVERLAP_CODE = "APPOINTMENT_OVERLAP"


async def start(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    conversation.selection = {}
    return await start_identification(conversation, backend, then=APPOINTMENTS_FLOW)


async def show_appointments(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    appointments = await _load_appointments(conversation, backend)
    conversation.selection = {}
    if not appointments:
        conversation.step = Step.IDLE
        return [_no_appointments_message()]
    conversation.step = Step.APPT_CHOOSE
    rows = [_appointment_row(item) for item in appointments[:MAX_ROWS]]
    return [ListMessage(text=APPOINTMENTS_LIST_TEXT, button_text=LIST_BUTTON_TEXT, sections=[ListSection(rows=rows)])]


def summary_messages(conversation: Conversation, appointment: Appointment) -> list[OutgoingMessage]:
    conversation.step = Step.APPT_ACTION
    conversation.selection = {"appointment": appointment.model_dump(mode="json", by_alias=True)}
    buttons = [
        ButtonAction(id=RESCHEDULE_ID, title=RESCHEDULE_TITLE),
        ButtonAction(id=CANCEL_ID, title=APPOINTMENT_CANCEL_TITLE),
    ]
    if appointment.status == PENDING_STATUS:
        buttons.append(ButtonAction(id=CONFIRM_ID, title=BOOK_CONFIRM_TITLE))
    summary = booking_summary_text(
        specialty_name=appointment.specialty_name,
        when=format_long(appointment.start_at),
        professional_name=appointment.professional_name,
        patient_name=str(conversation.patient_name),
    )
    return [ButtonsMessage(text=summary, buttons=buttons)]


async def start_reschedule(
    conversation: Conversation,
    appointment: Appointment,
    backend: Backend,
) -> list[OutgoingMessage]:
    """Starts rescheduling `appointment` (also used by the reminder flow, 017b)."""
    conversation.selection = {"appointment": appointment.model_dump(mode="json", by_alias=True)}
    return await show_reschedule_days(conversation, backend)


async def show_reschedule_days(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    appointment = _selected(conversation)
    days = await backend.get_available_days(appointment.specialty_id, appointment.professional_id)
    if not days:
        return [TextMessage(text=BOOK_NO_DAYS_TEXT), *await hand_off_from_backend(conversation, backend)]
    conversation.step = Step.RESCHEDULE_DAY
    return [build_day_list(days)]


async def show_reschedule_slots(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    appointment = _selected(conversation)
    day = date.fromisoformat(str(conversation.selection["date"]))
    slots = await backend.get_slots(appointment.specialty_id, day, professional_id=appointment.professional_id)
    if not slots:
        return [TextMessage(text=BOOK_NO_SLOTS_TEXT), *await show_reschedule_days(conversation, backend)]
    conversation.selection["slot_row_ids"] = [
        make_slot_row_id(slot.professional_id, slot.start_at) for slot in slots[:MAX_ROWS]
    ]
    conversation.step = Step.RESCHEDULE_SLOT
    return [build_slot_list(slots)]


def show_reschedule_confirm(conversation: Conversation) -> list[OutgoingMessage]:
    appointment = _selected(conversation)
    new_start = _new_start(conversation)
    conversation.step = Step.RESCHEDULE_CONFIRM
    summary = reschedule_summary_text(
        old_when=format_long(appointment.start_at),
        new_when=format_long(new_start),
    )
    return [
        ButtonsMessage(
            text=summary,
            buttons=[
                ButtonAction(id=RESCHEDULE_CONFIRM_ID, title=BOOK_CONFIRM_TITLE),
                ButtonAction(id=RESCHEDULE_CANCEL_ID, title=BOOK_CANCEL_TITLE),
            ],
        )
    ]


def show_cancel_confirm(conversation: Conversation) -> list[OutgoingMessage]:
    appointment = _selected(conversation)
    conversation.step = Step.CANCEL_CONFIRM
    return [
        ButtonsMessage(
            text=cancel_ask_text(format_long(appointment.start_at)),
            buttons=[
                ButtonAction(id=CANCEL_YES_ID, title=CANCEL_YES_TITLE),
                ButtonAction(id=CANCEL_NO_ID, title=CANCEL_NO_TITLE),
            ],
        )
    ]


async def answer_appointments(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    reply_id = incoming.reply_id or ""
    step = conversation.step
    if step == Step.APPT_CHOOSE and reply_id.startswith(ROW_PREFIX):
        return await _answer_choose(reply_id, conversation, backend)
    if step == Step.APPT_ACTION and reply_id in (RESCHEDULE_ID, CANCEL_ID, CONFIRM_ID):
        return await _answer_action(reply_id, conversation, backend)
    if step == Step.RESCHEDULE_DAY and reply_id.startswith(DAY_PREFIX):
        conversation.selection["date"] = reply_id.removeprefix(DAY_PREFIX)
        return await show_reschedule_slots(conversation, backend)
    if step == Step.RESCHEDULE_SLOT and reply_id.startswith(SLOT_PREFIX):
        return await _answer_slot(reply_id, conversation, backend)
    if step == Step.RESCHEDULE_CONFIRM and reply_id in (RESCHEDULE_CONFIRM_ID, RESCHEDULE_CANCEL_ID):
        return await _answer_reschedule_confirm(reply_id, conversation, backend)
    if step == Step.CANCEL_CONFIRM and reply_id in (CANCEL_YES_ID, CANCEL_NO_ID):
        return await _answer_cancel_confirm(reply_id, conversation, backend)
    return await _show_current_step(conversation, backend)


register_continuation(APPOINTMENTS_FLOW, show_appointments)


async def _load_appointments(conversation: Conversation, backend: Backend) -> list[Appointment]:
    return await backend.get_appointments(phone=conversation.phone, patient_id=str(conversation.patient_id))


def _no_appointments_message() -> ButtonsMessage:
    return ButtonsMessage(
        text=NO_APPOINTMENTS_TEXT,
        buttons=[
            ButtonAction(id=BOOK_ID, title=APPOINTMENTS_BOOK_TITLE),
            ButtonAction(id=HOME_ID, title=APPOINTMENTS_HOME_TITLE),
        ],
    )


def _appointment_row(appointment: Appointment) -> ListRow:
    return ListRow(
        id=f"{ROW_PREFIX}{appointment.appointment_id}",
        title=fit_length(format_day_time(appointment.start_at), MAX_ROW_TITLE),
        description=fit_length(
            f"{appointment.specialty_name} · {appointment.professional_name}",
            MAX_ROW_DESCRIPTION,
        ),
    )


def _selected(conversation: Conversation) -> Appointment:
    return Appointment.model_validate(conversation.selection["appointment"])


def _new_start(conversation: Conversation) -> datetime:
    return datetime.fromisoformat(str(conversation.selection["start_at"]))


async def _answer_choose(
    reply_id: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    appointment_id = reply_id.removeprefix(ROW_PREFIX)
    for item in await _load_appointments(conversation, backend):
        if item.appointment_id == appointment_id:
            return summary_messages(conversation, item)
    return await show_appointments(conversation, backend)


async def _answer_action(
    reply_id: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if reply_id == RESCHEDULE_ID:
        return await start_reschedule(conversation, _selected(conversation), backend)
    if reply_id == CANCEL_ID:
        return show_cancel_confirm(conversation)
    return await _confirm_appointment(conversation, backend)


async def _answer_slot(
    reply_id: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    parsed = parse_slot_row_id(reply_id)
    offered: list[str] = conversation.selection.get("slot_row_ids", [])
    if parsed is None or reply_id not in offered:
        return await _show_current_step(conversation, backend)
    conversation.selection["start_at"] = parsed[1]
    return show_reschedule_confirm(conversation)


async def _answer_reschedule_confirm(
    reply_id: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if reply_id == RESCHEDULE_CANCEL_ID:
        return await cancel_flow(conversation)
    return await _confirm_reschedule(conversation, backend)


async def _confirm_reschedule(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    appointment = _selected(conversation)
    new_start = _new_start(conversation)
    try:
        await backend.reschedule_appointment(
            phone=conversation.phone,
            appointment_id=appointment.appointment_id,
            start_at=new_start,
        )
    except BackendError as exc:
        if exc.code == OVERLAP_CODE:
            return [TextMessage(text=BOOK_OVERLAP_TEXT), *await show_reschedule_slots(conversation, backend)]
        return await _derive_after_error(exc, conversation, backend)

    conversation.step = Step.IDLE
    conversation.selection = {}
    return [TextMessage(text=reschedule_success_text(format_long(new_start)))]


async def _answer_cancel_confirm(
    reply_id: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if reply_id == CANCEL_NO_ID:
        return summary_messages(conversation, _selected(conversation))
    return await _confirm_cancel(conversation, backend)


async def _confirm_cancel(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    appointment = _selected(conversation)
    try:
        await backend.cancel_appointment(phone=conversation.phone, appointment_id=appointment.appointment_id)
    except BackendError as exc:
        return await _derive_after_error(exc, conversation, backend)

    conversation.step = Step.IDLE
    conversation.selection = {}
    return [TextMessage(text=APPOINTMENT_CANCELLED_TEXT), *await show_menu(conversation)]


async def _confirm_appointment(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    appointment = _selected(conversation)
    try:
        await backend.confirm_appointment(phone=conversation.phone, appointment_id=appointment.appointment_id)
    except BackendError as exc:
        return await _derive_after_error(exc, conversation, backend)

    conversation.step = Step.IDLE
    conversation.selection = {}
    return [TextMessage(text=APPOINTMENT_CONFIRMED_TEXT)]


async def _derive_after_error(
    exc: BackendError,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if exc.code == TOO_LATE_CODE:
        return [TextMessage(text=APPOINTMENT_TOO_LATE_TEXT), *await hand_off_from_backend(conversation, backend)]
    return await hand_off_from_backend(conversation, backend)


async def _show_current_step(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    """Repeats the question of the current step (used for unexpected replies)."""
    step = conversation.step
    if step == Step.APPT_CHOOSE:
        return await show_appointments(conversation, backend)
    if step == Step.APPT_ACTION:
        return summary_messages(conversation, _selected(conversation))
    if step == Step.RESCHEDULE_DAY:
        return await show_reschedule_days(conversation, backend)
    if step == Step.RESCHEDULE_SLOT:
        return await show_reschedule_slots(conversation, backend)
    if step == Step.RESCHEDULE_CONFIRM:
        return show_reschedule_confirm(conversation)
    if step == Step.CANCEL_CONFIRM:
        return show_cancel_confirm(conversation)
    return await show_menu(conversation)
