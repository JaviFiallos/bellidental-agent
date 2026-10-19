from typing import Any
import httpx

from app.dialog.models import ButtonsMessage, ListMessage, OutgoingMessage, TextMessage


class WhatsAppClient:
    """Client for sending WhatsApp messages via Meta Graph API."""

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        graph_version: str = "v23.0",
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.graph_version = graph_version
        self.timeout = timeout
        self._client = client

    def _build_payload(self, phone: str, message: OutgoingMessage) -> dict[str, Any]:
        base_payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
        }

        if isinstance(message, TextMessage):
            base_payload["type"] = "text"
            base_payload["text"] = {
                "preview_url": False,
                "body": message.text,
            }
        elif isinstance(message, ButtonsMessage):
            base_payload["type"] = "interactive"
            base_payload["interactive"] = {
                "type": "button",
                "body": {"text": message.text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": button.id, "title": button.title},
                        }
                        for button in message.buttons
                    ]
                },
            }
        elif isinstance(message, ListMessage):
            sections_payload: list[dict[str, Any]] = []
            for section in message.sections:
                section_payload: dict[str, Any] = {}
                if section.title:
                    section_payload["title"] = section.title
                row_payloads: list[dict[str, Any]] = []
                for row in section.rows:
                    row_payload: dict[str, Any] = {"id": row.id, "title": row.title}
                    if row.description:
                        row_payload["description"] = row.description
                    row_payloads.append(row_payload)
                section_payload["rows"] = row_payloads
                sections_payload.append(section_payload)

            base_payload["type"] = "interactive"
            base_payload["interactive"] = {
                "type": "list",
                "body": {"text": message.text},
                "action": {
                    "button": message.button_text,
                    "sections": sections_payload,
                },
            }
        else:
            raise ValueError(f"Unsupported message type: {type(message)}")

        return base_payload

    async def send(self, phone: str, message: OutgoingMessage) -> str:
        """Sends an outgoing message to a WhatsApp user and returns the message id (wamid)."""
        url = f"https://graph.facebook.com/{self.graph_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(phone, message)

        if self._client is not None:
            response = await self._client.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

        response.raise_for_status()
        response_body = response.json()
        messages = response_body.get("messages", [])
        if not messages or "id" not in messages[0]:
            raise RuntimeError("Invalid response structure from WhatsApp Graph API")
        return str(messages[0]["id"])
