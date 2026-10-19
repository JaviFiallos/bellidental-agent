from app.dialog.dependencies import Backend
from app.dialog.handoff import hand_off, hand_off_from_backend
from app.dialog.models import (
    Conversation,
    ListMessage,
    ListRow,
    ListSection,
    OutgoingMessage,
    Step,
    TextMessage,
)
from app.dialog.store import load_clinic_info
from app.messages.texts import (
    MENU_BUTTON_TEXT,
    MENU_ROW_APPOINTMENTS,
    MENU_ROW_BOOK,
    MENU_ROW_HOURS,
    MENU_ROW_HUMAN,
    MENU_ROW_PRICES,
    MENU_SECTION_TITLE,
    MENU_TEXT,
    hours_text,
    prices_text,
    technical_problem_text,
)

MENU_PREFIX = "menu:"
HOURS_ID = "menu:hours"
PRICES_ID = "menu:prices"
BOOK_ID = "menu:book"
APPOINTMENTS_ID = "menu:appointments"
HUMAN_ID = "menu:human"


def build_menu() -> ListMessage:
    return ListMessage(
        text=MENU_TEXT,
        button_text=MENU_BUTTON_TEXT,
        sections=[
            ListSection(
                title=MENU_SECTION_TITLE,
                rows=[
                    ListRow(id=HOURS_ID, title=MENU_ROW_HOURS),
                    ListRow(id=PRICES_ID, title=MENU_ROW_PRICES),
                    ListRow(id=BOOK_ID, title=MENU_ROW_BOOK),
                    ListRow(id=APPOINTMENTS_ID, title=MENU_ROW_APPOINTMENTS),
                    ListRow(id=HUMAN_ID, title=MENU_ROW_HUMAN),
                ],
            )
        ],
    )


async def show_menu(conversation: Conversation) -> list[OutgoingMessage]:
    conversation.step = Step.MENU
    return [build_menu()]


async def answer_menu(reply_id: str, conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    if reply_id == HOURS_ID:
        info = await load_clinic_info(backend)
        if info is None:
            return [TextMessage(text=technical_problem_text(""))]
        return [TextMessage(text=hours_text(info)), *await show_menu(conversation)]
    if reply_id == PRICES_ID:
        info = await load_clinic_info(backend)
        if info is None:
            return [TextMessage(text=technical_problem_text(""))]
        return [TextMessage(text=prices_text(info)), *await show_menu(conversation)]
    if reply_id in (APPOINTMENTS_ID, HUMAN_ID):
        return await hand_off_from_backend(conversation, backend)
    return await show_menu(conversation)
