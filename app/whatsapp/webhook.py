from typing import Any
from app.dialog.models import IncomingMessage


def parse_webhook(payload: dict[str, Any]) -> list[IncomingMessage]:
    """Parses a WhatsApp Cloud API webhook payload into IncomingMessage domain models."""
    parsed_messages: list[IncomingMessage] = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            raw_messages = value.get("messages", [])
            for raw_message in raw_messages:
                phone = raw_message.get("from")
                message_id = raw_message.get("id")
                if not phone or not message_id:
                    continue

                context = raw_message.get("context")
                context_message_id = context.get("id") if isinstance(context, dict) else None
                message_type = raw_message.get("type")

                kind: str = "unsupported"
                text: str | None = None
                reply_id: str | None = None

                if message_type == "text":
                    kind = "text"
                    text_obj = raw_message.get("text")
                    if isinstance(text_obj, dict):
                        text = text_obj.get("body")
                elif message_type == "interactive":
                    interactive = raw_message.get("interactive", {})
                    interactive_type = interactive.get("type")
                    if interactive_type == "button_reply":
                        kind = "button"
                        button_reply = interactive.get("button_reply", {})
                        reply_id = button_reply.get("id")
                        text = button_reply.get("title")
                    elif interactive_type == "list_reply":
                        kind = "list"
                        list_reply = interactive.get("list_reply", {})
                        reply_id = list_reply.get("id")
                        text = list_reply.get("title")
                    else:
                        kind = "unsupported"
                elif message_type == "button":
                    kind = "template_button"
                    button = raw_message.get("button", {})
                    reply_id = button.get("payload")
                    text = button.get("text")
                else:
                    kind = "unsupported"

                parsed_messages.append(
                    IncomingMessage(
                        phone=phone,
                        message_id=message_id,
                        kind=kind,
                        text=text,
                        reply_id=reply_id,
                        context_message_id=context_message_id,
                    )
                )

    return parsed_messages
