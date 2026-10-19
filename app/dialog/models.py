from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


MAX_ROWS = 10
MAX_ROW_TITLE = 24
MAX_ROW_DESCRIPTION = 72


class Step(StrEnum):
    IDLE = "IDLE"
    CONSENT = "CONSENT"
    MENU = "MENU"
    IDENTIFY_CONFIRM = "IDENTIFY_CONFIRM"
    IDENTIFY_ID = "IDENTIFY_ID"
    BOOK_SPECIALTY = "BOOK_SPECIALTY"
    BOOK_PROFESSIONAL = "BOOK_PROFESSIONAL"
    BOOK_DAY = "BOOK_DAY"
    BOOK_SLOT = "BOOK_SLOT"
    BOOK_CONFIRM = "BOOK_CONFIRM"
    APPT_CHOOSE = "APPT_CHOOSE"
    APPT_ACTION = "APPT_ACTION"
    RESCHEDULE_DAY = "RESCHEDULE_DAY"
    RESCHEDULE_SLOT = "RESCHEDULE_SLOT"
    RESCHEDULE_CONFIRM = "RESCHEDULE_CONFIRM"
    CANCEL_CONFIRM = "CANCEL_CONFIRM"
    URGENT_SLOT = "URGENT_SLOT"
    URGENT_CONFIRM = "URGENT_CONFIRM"


class IncomingMessage(BaseModel):
    phone: str
    message_id: str
    kind: Literal["text", "button", "list", "template_button", "unsupported"]
    text: str | None = None
    reply_id: str | None = None
    context_message_id: str | None = None


class TextMessage(BaseModel):
    text: str


class ButtonAction(BaseModel):
    id: str
    title: str = Field(max_length=20)


class ButtonsMessage(BaseModel):
    text: str
    buttons: list[ButtonAction] = Field(min_length=1, max_length=3)


class ListRow(BaseModel):
    id: str
    title: str = Field(max_length=MAX_ROW_TITLE)
    description: str | None = Field(default=None, max_length=MAX_ROW_DESCRIPTION)


class ListSection(BaseModel):
    title: str | None = None
    rows: list[ListRow] = Field(default_factory=list)


class ListMessage(BaseModel):
    text: str
    button_text: str = Field(max_length=20)
    sections: list[ListSection]

    @model_validator(mode="after")
    def validate_total_rows(self) -> "ListMessage":
        total_rows = sum(len(section.rows) for section in self.sections)
        if total_rows < 1:
            raise ValueError("ListMessage must have at least 1 row across all sections")
        if total_rows > 10:
            raise ValueError("ListMessage cannot have more than 10 rows across all sections")
        return self


class TemplateMessage(BaseModel):
    """Approved WhatsApp template. Body parameters go in order; button payloads map to quick_reply buttons 0..n."""

    name: str
    language: str
    body_parameters: list[str] = Field(default_factory=list)
    button_payloads: list[str] = Field(default_factory=list)


OutgoingMessage = TextMessage | ButtonsMessage | ListMessage | TemplateMessage


class Conversation(BaseModel):
    phone: str
    step: Step = Step.IDLE
    consent_accepted: bool = False
    patient_id: str | None = None
    patient_name: str | None = None
    selection: dict[str, Any] = Field(default_factory=dict)
    history: list[str] = Field(default_factory=list)
    handoff_until: datetime | None = None
    unknown_count: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
