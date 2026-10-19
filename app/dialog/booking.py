from datetime import date, datetime

from app.backend.models import BackendError
from app.dialog.dependencies import Backend
from app.dialog.handoff import hand_off_from_backend
from app.dialog.identify import register_continuation, start_identification
from app.dialog.menu import show_menu
from app.dialog.models import (
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
from app.dialog.slot_picker import SLOT_PREFIX, build_day_list, build_slot_list, parse_slot_row_id
from app.messages.dates import format_day, format_long
from app.messages.texts import (
    BOOK_CANCEL_TITLE,
    BOOK_CHANGE_TITLE,
    BOOK_CONFIRM_TITLE,
    BOOK_FIRST_AVAILABLE_TITLE,
    BOOK_LIMIT_TEXT,
    BOOK_NO_DAYS_TEXT,
    BOOK_NO_SLOTS_TEXT,
    BOOK_OVERLAP_TEXT,
    BOOK_PROFESSIONAL_TEXT,
    BOOK_SPECIALTY_TEXT,
    LIST_BUTTON_TEXT,
    booking_success_text,
    booking_summary_text,
    fit_length,
)

BOOK_FLOW = "book"
SPECIALTY_PREFIX = "spec:"
PROFESSIONAL_PREFIX = "prof:"
ANY_PROFESSIONAL_ID = "prof:any"
DAY_PREFIX = "day:"
CONFIRM_ID = "book:confirm"
CHANGE_ID = "book:change"
CANCEL_ID = "book:cancel"
MAX_PROFESSIONAL_ROWS = 9


def _list(text: str, rows: list[ListRow]) -> ListMessage:
    return ListMessage(text=text, button_text=LIST_BUTTON_TEXT, sections=[ListSection(rows=rows)])


async def start(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    conversation.selection = {}
    return await start_identification(conversation, backend, then=BOOK_FLOW)


async def cancel_flow(conversation: Conversation) -> list[OutgoingMessage]:
    conversation.step = Step.IDLE
    conversation.selection = {}
    return await show_menu(conversation)


async def show_specialties(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    specialties = await backend.get_specialties()
    if not specialties:
        return await hand_off_from_backend(conversation, backend)
    if len(specialties) == 1:
        return await _choose_specialty(conversation, backend, specialties[0].specialty_id, specialties[0].name)
    conversation.step = Step.BOOK_SPECIALTY
    rows = [ListRow(id=f"{SPECIALTY_PREFIX}{item.specialty_id}", title=fit_length(item.name, MAX_ROW_TITLE)) for item in specialties[:MAX_ROWS]]
    return [_list(BOOK_SPECIALTY_TEXT, rows)]


async def show_professionals(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    professionals = await backend.get_professionals(str(conversation.selection["specialty_id"]))
    if not professionals:
        return await hand_off_from_backend(conversation, backend)
    if len(professionals) == 1:
        only = professionals[0]
        return await _choose_professional(conversation, backend, only.professional_id, only.display_name)
    conversation.step = Step.BOOK_PROFESSIONAL
    rows = [ListRow(id=ANY_PROFESSIONAL_ID, title=BOOK_FIRST_AVAILABLE_TITLE)]
    rows += [
        ListRow(id=f"{PROFESSIONAL_PREFIX}{item.professional_id}", title=fit_length(item.display_name, MAX_ROW_TITLE))
        for item in professionals[:MAX_PROFESSIONAL_ROWS]
    ]
    return [_list(BOOK_PROFESSIONAL_TEXT, rows)]


async def show_days(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    days = await backend.get_available_days(
        str(conversation.selection["specialty_id"]),
        conversation.selection.get("professional_id"),
    )
    if not days:
        return [TextMessage(text=BOOK_NO_DAYS_TEXT), *await hand_off_from_backend(conversation, backend)]
    conversation.step = Step.BOOK_DAY
    return [build_day_list(days)]


async def show_slots(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    day = date.fromisoformat(str(conversation.selection["date"]))
    slots = await backend.get_slots(
        str(conversation.selection["specialty_id"]),
        day,
        professional_id=conversation.selection.get("professional_id"),
    )
    if not slots:
        return [TextMessage(text=BOOK_NO_SLOTS_TEXT), *await show_days(conversation, backend)]
    conversation.selection["professional_names"] = {slot.professional_id: slot.professional_name for slot in slots}
    conversation.step = Step.BOOK_SLOT
    return [build_slot_list(slots)]


async def show_confirm(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    start_at = datetime.fromisoformat(str(conversation.selection["start_at"]))
    summary = booking_summary_text(
        specialty_name=str(conversation.selection["specialty_name"]),
        when=format_long(start_at),
        professional_name=str(conversation.selection["slot_professional_name"]),
        patient_name=str(conversation.patient_name),
    )
    conversation.step = Step.BOOK_CONFIRM
    return [
        ButtonsMessage(
            text=summary,
            buttons=[
                ButtonAction(id=CONFIRM_ID, title=BOOK_CONFIRM_TITLE),
                ButtonAction(id=CHANGE_ID, title=BOOK_CHANGE_TITLE),
                ButtonAction(id=CANCEL_ID, title=BOOK_CANCEL_TITLE),
            ],
        )
    ]


async def answer_booking(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    reply_id = incoming.reply_id or ""
    step = conversation.step
    if step == Step.BOOK_SPECIALTY and reply_id.startswith(SPECIALTY_PREFIX):
        return await _answer_specialty(reply_id.removeprefix(SPECIALTY_PREFIX), conversation, backend)
    if step == Step.BOOK_PROFESSIONAL and reply_id.startswith(PROFESSIONAL_PREFIX):
        return await _answer_professional(reply_id, conversation, backend)
    if step == Step.BOOK_DAY and reply_id.startswith(DAY_PREFIX):
        conversation.selection["date"] = reply_id.removeprefix(DAY_PREFIX)
        return await show_slots(conversation, backend)
    if step == Step.BOOK_SLOT and reply_id.startswith(SLOT_PREFIX):
        return await _answer_slot(reply_id, conversation, backend)
    if step == Step.BOOK_CONFIRM and reply_id in (CONFIRM_ID, CHANGE_ID, CANCEL_ID):
        return await _answer_confirm(reply_id, conversation, backend)
    return await _show_current_step(conversation, backend)


async def _answer_specialty(
    specialty_id: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    for item in await backend.get_specialties():
        if item.specialty_id == specialty_id:
            return await _choose_specialty(conversation, backend, item.specialty_id, item.name)
    return await _show_current_step(conversation, backend)


async def _answer_professional(
    reply_id: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if reply_id == ANY_PROFESSIONAL_ID:
        return await _choose_professional(conversation, backend, None, None)
    professional_id = reply_id.removeprefix(PROFESSIONAL_PREFIX)
    for item in await backend.get_professionals(str(conversation.selection["specialty_id"])):
        if item.professional_id == professional_id:
            return await _choose_professional(conversation, backend, item.professional_id, item.display_name)
    return await _show_current_step(conversation, backend)


async def _answer_slot(
    reply_id: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    parsed = parse_slot_row_id(reply_id)
    names: dict[str, str] = conversation.selection.get("professional_names", {})
    if parsed is None or parsed[0] not in names:
        return await _show_current_step(conversation, backend)
    professional_id, start_at = parsed
    conversation.selection["slot_professional_id"] = professional_id
    conversation.selection["slot_professional_name"] = names[professional_id]
    conversation.selection["start_at"] = start_at
    return await show_confirm(conversation, backend)


async def _answer_confirm(
    reply_id: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if reply_id == CHANGE_ID:
        return await show_slots(conversation, backend)
    if reply_id == CANCEL_ID:
        return await cancel_flow(conversation)
    return await _confirm_booking(conversation, backend)


async def _confirm_booking(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    start_at = datetime.fromisoformat(str(conversation.selection["start_at"]))
    try:
        await backend.book_appointment(
            phone=conversation.phone,
            patient_id=str(conversation.patient_id),
            specialty_id=str(conversation.selection["specialty_id"]),
            professional_id=str(conversation.selection["slot_professional_id"]),
            start_at=start_at,
        )
    except BackendError as exc:
        if exc.code == "APPOINTMENT_OVERLAP":
            return [TextMessage(text=BOOK_OVERLAP_TEXT), *await show_slots(conversation, backend)]
        if exc.code == "BOT_LIMIT_REACHED":
            return [TextMessage(text=BOOK_LIMIT_TEXT), *await hand_off_from_backend(conversation, backend)]
        return await hand_off_from_backend(conversation, backend)

    conversation.step = Step.IDLE
    conversation.selection = {}
    return [TextMessage(text=booking_success_text(format_long(start_at)))]


async def _choose_specialty(
    conversation: Conversation,
    backend: Backend,
    specialty_id: str,
    specialty_name: str,
) -> list[OutgoingMessage]:
    conversation.selection["specialty_id"] = specialty_id
    conversation.selection["specialty_name"] = specialty_name
    return await show_professionals(conversation, backend)


async def _choose_professional(
    conversation: Conversation,
    backend: Backend,
    professional_id: str | None,
    professional_name: str | None,
) -> list[OutgoingMessage]:
    conversation.selection["professional_id"] = professional_id
    conversation.selection["professional_name"] = professional_name
    return await show_days(conversation, backend)


async def _show_current_step(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    """Repeats the question of the current step (used for unexpected replies)."""
    handlers = {
        Step.BOOK_SPECIALTY: show_specialties,
        Step.BOOK_PROFESSIONAL: show_professionals,
        Step.BOOK_DAY: show_days,
        Step.BOOK_SLOT: show_slots,
        Step.BOOK_CONFIRM: show_confirm,
    }
    handler = handlers.get(conversation.step)
    if handler is None:
        return await show_menu(conversation)
    return await handler(conversation, backend)


register_continuation(BOOK_FLOW, show_specialties)
