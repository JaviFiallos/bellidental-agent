from datetime import date, datetime

from app.backend.models import Slot
from app.dialog.models import MAX_ROW_DESCRIPTION, MAX_ROWS, ListMessage, ListRow, ListSection
from app.messages.dates import format_day, format_time
from app.messages.texts import BOOK_DAY_TEXT, BOOK_SLOT_TEXT, LIST_BUTTON_TEXT, fit_length

DAY_PREFIX = "day:"
SLOT_PREFIX = "slot:"


def build_day_list(days: list[date]) -> ListMessage:
    rows = [ListRow(id=f"{DAY_PREFIX}{day.isoformat()}", title=format_day(day)) for day in days[:MAX_ROWS]]
    return ListMessage(text=BOOK_DAY_TEXT, button_text=LIST_BUTTON_TEXT, sections=[ListSection(rows=rows)])


def build_slot_list(slots: list[Slot]) -> ListMessage:
    rows = [
        ListRow(
            id=make_slot_row_id(slot.professional_id, slot.start_at),
            title=format_time(slot.start_at),
            description=fit_length(slot.professional_name, MAX_ROW_DESCRIPTION),
        )
        for slot in slots[:MAX_ROWS]
    ]
    return ListMessage(text=BOOK_SLOT_TEXT, button_text=LIST_BUTTON_TEXT, sections=[ListSection(rows=rows)])


def make_slot_row_id(professional_id: str, start_at: datetime) -> str:
    return f"{SLOT_PREFIX}{professional_id}|{start_at.isoformat()}"


def parse_slot_row_id(reply_id: str) -> tuple[str, str] | None:
    """Returns (professional_id, startAt ISO) from 'slot:<professionalId>|<startAt>', or None if malformed."""
    professional_id, separator, start_at = reply_id.removeprefix(SLOT_PREFIX).partition("|")
    if not separator or not professional_id or not start_at:
        return None
    return professional_id, start_at
