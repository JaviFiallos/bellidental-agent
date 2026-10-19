import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.dialog.models import Step
from app.nlu.models import Interpretation
from app.nlu.prompt import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger(__name__)
MAX_TOKENS = 150


class OpenAICompatibleClassifier:
    """Classifier for any provider exposing POST {base_url}/chat/completions (OpenAI-compatible API)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client = client

    async def classify(self, text: str, step: Step, recent: list[str]) -> Interpretation | None:
        body: dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_tokens": MAX_TOKENS,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_message(text, step, recent)},
            ],
        }
        try:
            response_payload = await self._post(body)
            content = response_payload["choices"][0]["message"]["content"]
            return Interpretation.model_validate_json(content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValidationError, ValueError) as exc:
            logger.warning("LLM classification unavailable: %s", type(exc).__name__)
            return None

    async def _post(self, body: dict[str, Any]) -> Any:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if self._client is not None:
            response = await self._client.post(url, json=body, headers=headers, timeout=self.timeout)
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=body, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
