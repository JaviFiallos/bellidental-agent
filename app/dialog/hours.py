import re
from collections.abc import Callable
from datetime import date, timedelta

from app.backend.models import ProfessionalSchedule, Specialty
from app.dialog import booking, menu
from app.dialog.dependencies import Backend
from app.dialog.hints import matches_text, matches_words, resolve_date_hint
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
    HOURS_MATCHES_TITLE,
    HOURS_NEXT_WEEK_TITLE,
    HOURS_NO_SCHEDULE_TEXT,
    HOURS_OPTIONS_TEXT,
    HOURS_SECTION_TITLE,
    LIST_BUTTON_TEXT,
    day_no_schedule_text,
    day_schedule_text,
    fit_length,
    hours_text,
    technical_problem_text,
    weekly_schedule_text,
)
from app.nlu.models import Interpretation

HOURS_PREFIX = "hours:"
HOURS_GENERAL_ID = "hours:general"
HOURS_SPEC_PREFIX = "hours:spec:"
HOURS_BOOK_PREFIX = "hours:book:"
HOURS_PROF_PREFIX = "hours:prof:"
HOME_ID = "menu:home"
DAYS_PER_WEEK = 7
SCHEDULE_WINDOW_DAYS = 14

TITLE_CLEAN_PATTERN = re.compile(r"^(doctora|doctor|dra\.?|dr\.?)\s+", re.IGNORECASE)


async def show_hours_menu(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    specialties = await backend.get_specialties()
    rows = [ListRow(id=HOURS_GENERAL_ID, title=HOURS_GENERAL_TITLE)]
    for specialty in specialties:
        rows.append(
            ListRow(id=f"{HOURS_SPEC_PREFIX}{specialty.specialty_id}:0", title=fit_length(specialty.name, MAX_ROW_TITLE))
        )
    sections = [ListSection(title=HOURS_SECTION_TITLE, rows=rows[:MAX_ROWS])]
    return [ListMessage(text=HOURS_CHOOSE_TEXT, button_text=LIST_BUTTON_TEXT, sections=sections)]


async def answer_hours(
    reply_id: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    """Answers the stateless 'hours:' ids of the hours list and of the weekly view buttons."""
    if reply_id == HOURS_GENERAL_ID:
        return await _answer_general(conversation, backend)
    if reply_id.startswith(HOURS_BOOK_PREFIX):
        return await _answer_book(reply_id.removeprefix(HOURS_BOOK_PREFIX), conversation, backend)
    if reply_id.startswith(HOURS_SPEC_PREFIX):
        specialty_id, week = _parse_week_id(reply_id.removeprefix(HOURS_SPEC_PREFIX))
        return await _answer_specialty_week(specialty_id, week, conversation, backend)
    if reply_id.startswith(HOURS_PROF_PREFIX):
        professional_id, week = _parse_week_id(reply_id.removeprefix(HOURS_PROF_PREFIX))
        return await _answer_professional_week(professional_id, week, backend)
    return await show_hours_menu(conversation, backend)


async def answer_hours_text(
    interpretation: Interpretation,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    """Free-text HOURS: professional, then specialty, then a day; otherwise the hours list."""
    if interpretation.professional:
        return await _answer_professional_hint(interpretation.professional, conversation, backend)
    if interpretation.specialty:
        specialty = await _find_specialty(backend, lambda item: matches_text(str(interpretation.specialty), item.name))
        if specialty is not None:
            return await _answer_specialty_week(specialty.specialty_id, 0, conversation, backend)
    if interpretation.date_hint:
        today = clinic_today()
        window = [today + timedelta(days=offset) for offset in range(SCHEDULE_WINDOW_DAYS)]
        day = resolve_date_hint(interpretation.date_hint, today, window)
        if day is not None:
            return await _answer_day(day, conversation, backend)
    return await show_hours_menu(conversation, backend)


async def _answer_general(conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    info = await load_clinic_info(backend)
    if info is None:
        return [TextMessage(text=technical_problem_text(""))]
    return [TextMessage(text=hours_text(info)), *await menu.show_menu(conversation)]


async def _answer_book(specialty_id: str, conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    specialty = await _find_specialty(backend, lambda item: item.specialty_id == specialty_id)
    if specialty is None:
        return await show_hours_menu(conversation, backend)
    return await booking.start(conversation, backend, hints={"specialty": specialty.name})


async def _answer_specialty_week(
    specialty_id: str,
    week: int,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    specialty = await _find_specialty(backend, lambda item: item.specialty_id == specialty_id)
    if specialty is None:
        return await show_hours_menu(conversation, backend)
    from_day, to_day = _week_range(week)
    schedules = await backend.get_schedule(from_day, to_day, specialty_id=specialty_id)
    buttons = [ButtonAction(id=f"{HOURS_BOOK_PREFIX}{specialty_id}", title=HOURS_BOOK_TITLE)]
    if week == 0:
        buttons.append(ButtonAction(id=f"{HOURS_SPEC_PREFIX}{specialty_id}:1", title=HOURS_NEXT_WEEK_TITLE))
    return _week_messages(specialty.name, from_day, to_day, schedules, buttons)


async def _answer_professional_week(professional_id: str, week: int, backend: Backend) -> list[OutgoingMessage]:
    from_day, to_day = _week_range(week)
    schedules = await backend.get_schedule(from_day, to_day, professional_id=professional_id)
    title = schedules[0].professional_name if schedules else HOURS_MATCHES_TITLE
    return _week_messages(title, from_day, to_day, schedules, _professional_buttons(professional_id, week))


async def _answer_professional_hint(
    hint: str,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    name = TITLE_CLEAN_PATTERN.sub("", hint.strip())
    if not name:
        return await show_hours_menu(conversation, backend)
    from_day, to_day = _week_range(0)
    schedules = await backend.get_schedule(from_day, to_day)
    matching = [item for item in schedules if matches_words(name, item.professional_name)]
    if not matching:
        return await show_hours_menu(conversation, backend)
    if len(matching) == 1:
        only = matching[0]
        buttons = _professional_buttons(only.professional_id, 0)
        return _week_messages(only.professional_name, from_day, to_day, matching, buttons)
    return _week_messages(HOURS_MATCHES_TITLE, from_day, to_day, matching, [])


async def _answer_day(day: date, conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    schedules = await backend.get_schedule(day, day)
    if _has_shifts(schedules):
        text = day_schedule_text(day, schedules)
    else:
        text = day_no_schedule_text(day, await load_clinic_info(backend))
    return [TextMessage(text=text), *await menu.show_menu(conversation)]


def _week_messages(
    title: str,
    from_day: date,
    to_day: date,
    schedules: list[ProfessionalSchedule],
    buttons: list[ButtonAction],
) -> list[OutgoingMessage]:
    """Weekly view: the schedule in its own text (button bodies allow only 1024 characters), then the buttons."""
    if _has_shifts(schedules):
        text = weekly_schedule_text(title, from_day, to_day, schedules)
    else:
        text = HOURS_NO_SCHEDULE_TEXT
    return [TextMessage(text=text), ButtonsMessage(text=HOURS_OPTIONS_TEXT, buttons=[*buttons, _home_button()])]


def _professional_buttons(professional_id: str, week: int) -> list[ButtonAction]:
    if week != 0:
        return []
    return [ButtonAction(id=f"{HOURS_PROF_PREFIX}{professional_id}:1", title=HOURS_NEXT_WEEK_TITLE)]


def _home_button() -> ButtonAction:
    return ButtonAction(id=HOME_ID, title=APPOINTMENTS_HOME_TITLE)


def _parse_week_id(payload: str) -> tuple[str, int]:
    """'{id}:{week}' → (id, week); a week other than 0 or 1 becomes 0."""
    item_id, _, raw_week = payload.partition(":")
    return item_id, 1 if raw_week == "1" else 0


def _week_range(week: int) -> tuple[date, date]:
    from_day = clinic_today() + timedelta(days=DAYS_PER_WEEK * week)
    return from_day, from_day + timedelta(days=DAYS_PER_WEEK - 1)


def _has_shifts(schedules: list[ProfessionalSchedule]) -> bool:
    return any(day.shifts for item in schedules for day in item.days)


async def _find_specialty(backend: Backend, predicate: Callable[[Specialty], bool]) -> Specialty | None:
    return next((item for item in await backend.get_specialties() if predicate(item)), None)
