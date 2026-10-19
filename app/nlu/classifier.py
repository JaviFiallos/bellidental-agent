from typing import Protocol

from app.dialog.models import Step
from app.nlu.models import Interpretation


class Classifier(Protocol):
    """Classifies a free-text message. Returns None when the result is unavailable or invalid."""

    async def classify(self, text: str, step: Step, recent: list[str]) -> Interpretation | None: ...


class DisabledClassifier:
    """Used when no LLM is configured: the bot falls back to the menu."""

    async def classify(self, text: str, step: Step, recent: list[str]) -> Interpretation | None:
        return None
