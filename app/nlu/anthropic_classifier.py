import logging

import anthropic
from pydantic import ValidationError

from app.dialog.models import Step
from app.nlu.models import Interpretation
from app.nlu.prompt import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger(__name__)
MAX_TOKENS = 256


class AnthropicClassifier:
    """Classifier for the Anthropic API. Structured outputs guarantee JSON that matches Interpretation."""

    def __init__(self, client: anthropic.AsyncAnthropic, model: str) -> None:
        self.model = model
        self._client = client

    async def classify(self, text: str, step: Step, recent: list[str]) -> Interpretation | None:
        try:
            response = await self._client.messages.parse(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_message(text, step, recent)}],
                output_format=Interpretation,
                thinking={"type": "disabled"},
            )
        except anthropic.APIStatusError as exc:
            logger.warning("LLM classification unavailable: status=%s", exc.status_code)
            return None
        except (anthropic.APIError, ValidationError) as exc:
            logger.warning("LLM classification unavailable: %s", type(exc).__name__)
            return None

        if response.stop_reason != "end_turn" or response.parsed_output is None:
            return None
        logger.info("LLM intent=%s", response.parsed_output.intent)
        return response.parsed_output
