from datetime import timedelta

from app.dialog import booking, menu
from app.dialog.dependencies import Backend
from app.dialog.models import (
    MAX_ROW_TITLE,
    MAX_ROWS,
    ButtonAction,
    ButtonsMessage,
    Conversation,
    ListMessage,
    ListRow,
    ListSection,
    OutgoingMessage,
    TextMessage,
)
from app.dialog.store import load_clinic_info
from app.messages.dates import clinic_today
from app.messages.texts import (
    APPOINTMENTS_HOME_TITLE,
    HOURS_BOOK_TITLE,
    HOURS_CHOOSE_TEXT,
    HOURS_GENERAL_TITLE,
    HOURS_NEXT_WEEK_TITLE,
    HOURS_NO_SCHEDULE_TEXT,
    HOURS_OPTIONS_TEXT,
    HOURS_SECTION_TITLE,
    LIST_BUTTON_TEXT,
    fit_length,
    hours_text,
    technical_problem_text,
    weekly_schedule_text,
)

HOURS_PREFIX = "hours:"
HOURS_GENERAL_ID = "hours:general"
HOURS_SPEC_PREFIX = "hours:spec:"
HOURS_BOOK_PREFIX = "hours:book:"
HOME_ID = "menu:home"


async def show_hours_menu(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    specialties = await backend.get_specialties()
    rows = [ListRow(id=HOURS_GENERAL_ID, title=HOURS_GENERAL_TITLE)]
    for spec in specialties:
        rows.append(ListRow(id=f"{HOURS_SPEC_PREFIX}{spec.specialty_id}:0", title=fit_length(spec.name, MAX_ROW_TITLE)))
    sections = [ListSection(title=HOURS_SECTION_TITLE, rows=rows[:MAX_ROWS])]
    return [ListMessage(text=HOURS_CHOOSE_TEXT, button_text=LIST_BUTTON_TEXT, sections=sections)]


async def answer_hours(
    reply_id: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    if reply_id == HOURS_GENERAL_ID:
        info = await load_clinic_info(backend)
        if info is None:
            return [TextMessage(text=technical_problem_text(""))]
        return [TextMessage(text=hours_text(info)), *await menu.show_menu(conversation)]

    if reply_id.startswith(HOURS_BOOK_PREFIX):
        specialty_id = reply_id.removeprefix(HOURS_BOOK_PREFIX)
        specialties = await backend.get_specialties()
        specialty = next((s for s in specialties if s.specialty_id == specialty_id), None)
        if specialty is None:
            return await show_hours_menu(conversation, backend)
        return await booking.start(conversation, backend, hints={"specialty": specialty.name})

    if reply_id.startswith(HOURS_SPEC_PREFIX):
        payload = reply_id.removeprefix(HOURS_SPEC_PREFIX)
        parts = payload.split(":")
        specialty_id = parts[0]
        raw_week = parts[1] if len(parts) > 1 else "0"
        week = int(raw_week) if raw_week in ("0", "1") else 0

        specialties = await backend.get_specialties()
        specialty = next((s for s in specialties if s.specialty_id == specialty_id), None)
        if specialty is None:
            return await show_hours_menu(conversation, backend)

        today = clinic_today()
        from_day = today + timedelta(days=7 * week)
        to_day = from_day + timedelta(days=6)

        schedules = await backend.get_schedule(from_day, to_day, specialty_id=specialty_id)
        has_shifts = any(any(day.shifts for day in prof.days) for prof in schedules)

        if not schedules or not has_shifts:
            text_content = HOURS_NO_SCHEDULE_TEXT
        else:
            text_content = weekly_schedule_text(specialty.name, from_day, to_day, schedules)

        buttons = [
            ButtonAction(id=f"{HOURS_BOOK_PREFIX}{specialty_id}", title=HOURS_BOOK_TITLE),
        ]
        if week == 0:
            buttons.append(ButtonAction(id=f"{HOURS_SPEC_PREFIX}{specialty_id}:1", title=HOURS_NEXT_WEEK_TITLE))
        buttons.append(ButtonAction(id=HOME_ID, title=APPOINTMENTS_HOME_TITLE))

        return [
            TextMessage(text=text_content),
            ButtonsMessage(text=HOURS_OPTIONS_TEXT, buttons=buttons),
        ]

    return await show_hours_menu(conversation, backend)
