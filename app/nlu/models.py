from enum import StrEnum

from pydantic import BaseModel, Field

MAX_HINT_LENGTH = 40


class Intent(StrEnum):
    HOURS = "HOURS"
    PRICE = "PRICE"
    BOOK = "BOOK"
    RESCHEDULE = "RESCHEDULE"
    CANCEL = "CANCEL"
    CONFIRM = "CONFIRM"
    URGENT = "URGENT"
    CLINICAL = "CLINICAL"
    BALANCE = "BALANCE"
    HUMAN = "HUMAN"
    GREETING = "GREETING"
    OTHER = "OTHER"


class Interpretation(BaseModel):
    """Structured output of the LLM. It only classifies: its texts are compared with the backend catalogs, never sent."""

    intent: Intent
    specialty: str | None = Field(default=None, max_length=MAX_HINT_LENGTH)
    treatment: str | None = Field(default=None, max_length=MAX_HINT_LENGTH)
    date_hint: str | None = Field(default=None, max_length=MAX_HINT_LENGTH)
    time_hint: str | None = Field(default=None, max_length=MAX_HINT_LENGTH)
