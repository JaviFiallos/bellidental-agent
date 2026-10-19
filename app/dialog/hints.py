import re
from datetime import date
from unicodedata import combining, normalize

from app.backend.models import Slot
from app.messages.dates import WEEKDAYS, clinic_hour

MORNING = "manana"
AFTERNOON = "tarde"
AFTERNOON_START_HOUR = 12
DAY_MONTH_PATTERN = re.compile(r"(\d{1,2})/(\d{1,2})")


def normalize_text(text: str) -> str:
    """Lowercases and removes accents, so comparisons ignore case and tildes."""
    decomposed = normalize("NFKD", text.strip().lower())
    return "".join(char for char in decomposed if not combining(char))


def matches_text(hint: str, candidate: str) -> bool:
    """True when one normalized text contains the other ('limpieza' matches 'Limpieza dental')."""
    normalized_hint = normalize_text(hint)
    normalized_candidate = normalize_text(candidate)
    if not normalized_hint or not normalized_candidate:
        return False
    return normalized_hint in normalized_candidate or normalized_candidate in normalized_hint


def resolve_date_hint(hint: str | None, today: date, available: list[date]) -> date | None:
    """Maps a hint ('mañana', 'jueves', '23/10') to one of the available days, or None."""
    if not hint:
        return None
    normalized = normalize_text(hint)
    relative = _relative_day(normalized, today)
    day_month = _day_month(normalized, today)
    candidate = relative if relative is not None else day_month
    if candidate is not None:
        return candidate if candidate in available else None
    for day in available:
        if normalize_text(WEEKDAYS[day.weekday()]) == normalized:
            return day
    return None


def filter_slots_by_period(slots: list[Slot], period: str | None) -> list[Slot]:
    """Keeps the morning (before 12:00) or afternoon (from 12:00) slots; other values keep all slots."""
    if not period:
        return slots
    normalized = normalize_text(period)
    if normalized == MORNING:
        return [slot for slot in slots if clinic_hour(slot.start_at) < AFTERNOON_START_HOUR]
    if normalized == AFTERNOON:
        return [slot for slot in slots if clinic_hour(slot.start_at) >= AFTERNOON_START_HOUR]
    return slots


def _relative_day(normalized: str, today: date) -> date | None:
    offsets = {"hoy": 0, "manana": 1, "pasado manana": 2}
    offset = offsets.get(normalized)
    if offset is None:
        return None
    return date.fromordinal(today.toordinal() + offset)


def _day_month(normalized: str, today: date) -> date | None:
    match = DAY_MONTH_PATTERN.fullmatch(normalized)
    if match is None:
        return None
    try:
        return date(today.year, int(match.group(2)), int(match.group(1)))
    except ValueError:
        return None
