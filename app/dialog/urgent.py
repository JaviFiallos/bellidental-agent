from typing import Any

from app.backend.models import BackendError, Slot
from app.dialog.booking import cancel_flow
from app.dialog.dependencies import Backend
from app.dialog.handoff import hand_off_from_backend
from app.dialog.identify import register_continuation, start_identification
from app.dialog.models import (
    ButtonAction,
    ButtonsMessage,
    Conversation,
    IncomingMessage,
    OutgoingMessage,
    Step,
    TextMessage,
)
from app.dialog.store import load_clinic_info
from app.messages.dates import clinic_date, clinic_today, format_long, format_time
from app.messages.texts import (
    BOOK_CANCEL_TITLE,
    BOOK_CONFIRM_TITLE,
    BOOK_LIMIT_TEXT,
    BOOK_OVERLAP_TEXT,
    URGENT_EMERGENCY_TEXT,
    URGENT_SLOTS_TEXT,
    URGENT_SPECIALTY_LABEL,
    booking_success_text,
    booking_summary_text,
    urgent_after_hours_text,
    urgent_no_slots_text,
    urgent_slot_title,
)

URGENT_FLOW = "urgent"
SLOT_PREFIX = "urgent:slot:"
CONFIRM_ID = "urgent:confirm"
CANCEL_ID = "urgent:cancel"
MAX_SLOT_BUTTONS = 3
BOT_LIMIT_CODE = "BOT_LIMIT_REACHED"
OVERLAP_CODE = "APPOINTMENT_OVERLAP"


async def start(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    """Emergency flow (D-21): fixed emergency text first, then the first urgent slots as buttons."""
    return [TextMessage(text=URGENT_EMERGENCY_TEXT), *await _offer_slots(conversation, backend)]


async def answer_urgent(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    reply_id = incoming.reply_id or ""
    step = conversation.step
    if step == Step.URGENT_SLOT and reply_id.startswith(SLOT_PREFIX):
        return await _answer_slot(reply_id, conversation, backend)
    if step == Step.URGENT_CONFIRM and reply_id in (CONFIRM_ID, CANCEL_ID):
        return await _answer_confirm(reply_id, conversation, backend)
    return await _show_current_step(conversation, backend)


async def _offer_slots(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    urgent = await backend.get_urgent_slots()
    info = await load_clinic_info(backend)
    after_hours_phone = info.after_hours_phone if info is not None else ""
    if not urgent.slots:
        no_slots_text = TextMessage(text=urgent_no_slots_text(after_hours_phone))
        return [no_slots_text, *await hand_off_from_backend(conversation, backend)]

    offered = urgent.slots[:MAX_SLOT_BUTTONS]
    conversation.step = Step.URGENT_SLOT
    conversation.selection = {
        "specialty_id": urgent.specialty_id,
        "slots": [slot.model_dump(mode="json", by_alias=True) for slot in offered],
    }
    messages: list[OutgoingMessage] = []
    if urgent.no_slots_today and after_hours_phone:
        messages.append(TextMessage(text=urgent_after_hours_text(after_hours_phone)))
    today = clinic_today()
    buttons = [
        ButtonAction(
            id=f"{SLOT_PREFIX}{index}",
            title=urgent_slot_title(clinic_date(slot.start_at) == today, format_time(slot.start_at)),
        )
        for index, slot in enumerate(offered)
    ]
    messages.append(ButtonsMessage(text=URGENT_SLOTS_TEXT, buttons=buttons))
    return messages


def show_confirm(conversation: Conversation) -> list[OutgoingMessage]:
    slot = Slot.model_validate(conversation.selection["slot"])
    conversation.step = Step.URGENT_CONFIRM
    summary = booking_summary_text(
        specialty_name=URGENT_SPECIALTY_LABEL,
        when=format_long(slot.start_at),
        professional_name=slot.professional_name,
        patient_name=str(conversation.patient_name),
    )
    return [
        ButtonsMessage(
            text=summary,
            buttons=[
                ButtonAction(id=CONFIRM_ID, title=BOOK_CONFIRM_TITLE),
                ButtonAction(id=CANCEL_ID, title=BOOK_CANCEL_TITLE),
            ],
        )
    ]


async def _continue_after_identification(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    carry: dict[str, Any] = conversation.selection.get("carry", {})
    conversation.selection = {"specialty_id": carry["specialty_id"], "slot": carry["slot"]}
    return show_confirm(conversation)


async def _answer_slot(reply_id: str, conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    index_text = reply_id.removeprefix(SLOT_PREFIX)
    offered: list[dict[str, Any]] = conversation.selection.get("slots", [])
    if not index_text.isdigit() or int(index_text) >= len(offered):
        return await _show_current_step(conversation, backend)
    carry = {"specialty_id": conversation.selection["specialty_id"], "slot": offered[int(index_text)]}
    return await start_identification(conversation, backend, then=URGENT_FLOW, carry=carry)


async def _answer_confirm(reply_id: str, conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    if reply_id == CANCEL_ID:
        return await cancel_flow(conversation)
    return await _confirm_booking(conversation, backend)


async def _confirm_booking(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    slot = Slot.model_validate(conversation.selection["slot"])
    try:
        await backend.book_appointment(
            phone=conversation.phone,
            patient_id=str(conversation.patient_id),
            specialty_id=str(conversation.selection["specialty_id"]),
            professional_id=slot.professional_id,
            start_at=slot.start_at,
        )
    except BackendError as exc:
        if exc.code == OVERLAP_CODE:
            return [TextMessage(text=BOOK_OVERLAP_TEXT), *await _offer_slots(conversation, backend)]
        if exc.code == BOT_LIMIT_CODE:
            return [TextMessage(text=BOOK_LIMIT_TEXT), *await hand_off_from_backend(conversation, backend)]
        return await hand_off_from_backend(conversation, backend)

    conversation.step = Step.IDLE
    conversation.selection = {}
    return [TextMessage(text=booking_success_text(format_long(slot.start_at)))]


async def _show_current_step(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    """Repeats the question of the current step (used for unexpected replies)."""
    if conversation.step == Step.URGENT_CONFIRM:
        return show_confirm(conversation)
    if conversation.step == Step.URGENT_SLOT:
        return await _offer_slots(conversation, backend)
    return await cancel_flow(conversation)


register_continuation(URGENT_FLOW, _continue_after_identification)
