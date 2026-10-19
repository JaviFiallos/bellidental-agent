import hashlib
import hmac
import json
from fastapi.testclient import TestClient

from app.config import Settings
from app.dialog.store import ConversationStore, ProcessedMessages
from app.main import create_app
from app.messages.texts import MENU_TEXT
from app.whatsapp.webhook import parse_webhook
from tests.fakes import FakeBackend, FakeSender


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_webhook_valid_signature_replies_to_text() -> None:
    sender = FakeSender()
    backend = FakeBackend()
    store = ConversationStore()
    processed_messages = ProcessedMessages()
    secret = "secret-123"
    settings = Settings(wa_app_secret=secret)

    app = create_app(
        sender=sender,
        backend=backend,
        store=store,
        processed_messages=processed_messages,
        settings=settings,
    )
    client = TestClient(app)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messages": [
                                {
                                    "from": "593987654321",
                                    "id": "wamid.001",
                                    "type": "text",
                                    "text": {"body": "Hola"},
                                }
                            ]
                        },
                    }
                ],
            }
        ],
    }
    raw_body = json.dumps(payload).encode("utf-8")
    headers = {
        "X-Hub-Signature-256": _sign(raw_body, secret),
        "Content-Type": "application/json",
    }

    response = client.post("/webhook", content=raw_body, headers=headers)

    assert response.status_code == 200
    assert len(sender.sent) == 1
    phone, msg = sender.sent[0]
    assert phone == "593987654321"
    assert getattr(msg, "text", "") == MENU_TEXT


def test_webhook_invalid_signature_returns_401_and_sends_nothing() -> None:
    sender = FakeSender()
    app = create_app(sender=sender, settings=Settings(wa_app_secret="correct-secret"))
    client = TestClient(app)

    payload = {"entry": []}
    raw_body = json.dumps(payload).encode("utf-8")
    headers = {
        "X-Hub-Signature-256": "sha256=invalidhexsignature",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook", content=raw_body, headers=headers)

    assert response.status_code == 401
    assert len(sender.sent) == 0


def test_webhook_duplicate_message_id_processed_once() -> None:
    sender = FakeSender()
    secret = "secret-dedup"
    app = create_app(
        sender=sender,
        backend=FakeBackend(),
        store=ConversationStore(),
        processed_messages=ProcessedMessages(),
        settings=Settings(wa_app_secret=secret),
    )
    client = TestClient(app)

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "593987654321",
                                    "id": "wamid.dup.123",
                                    "type": "text",
                                    "text": {"body": "Hola de nuevo"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    raw_body = json.dumps(payload).encode("utf-8")
    headers = {
        "X-Hub-Signature-256": _sign(raw_body, secret),
        "Content-Type": "application/json",
    }

    resp1 = client.post("/webhook", content=raw_body, headers=headers)
    assert resp1.status_code == 200
    assert len(sender.sent) == 1

    resp2 = client.post("/webhook", content=raw_body, headers=headers)
    assert resp2.status_code == 200
    assert len(sender.sent) == 1


def test_parse_webhook_button_list_and_template_replies_set_reply_id() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "593987654321",
                                    "id": "wamid.btn",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {"id": "btn_accept", "title": "Aceptar"},
                                    },
                                    "context": {"id": "context.btn"},
                                },
                                {
                                    "from": "593987654321",
                                    "id": "wamid.list",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "list_reply",
                                        "list_reply": {"id": "list_slot_1", "title": "10:00"},
                                    },
                                    "context": {"id": "context.list"},
                                },
                                {
                                    "from": "593987654321",
                                    "id": "wamid.tmpl",
                                    "type": "button",
                                    "button": {
                                        "payload": "TEMPLATE_CONFIRM",
                                        "text": "Sí, confirmar",
                                    },
                                    "context": {"id": "context.tmpl"},
                                },
                            ]
                        }
                    }
                ]
            }
        ]
    }

    messages = parse_webhook(payload)

    assert len(messages) == 3

    assert messages[0].kind == "button"
    assert messages[0].reply_id == "btn_accept"
    assert messages[0].context_message_id == "context.btn"

    assert messages[1].kind == "list"
    assert messages[1].reply_id == "list_slot_1"
    assert messages[1].context_message_id == "context.list"

    assert messages[2].kind == "template_button"
    assert messages[2].reply_id == "TEMPLATE_CONFIRM"
    assert messages[2].context_message_id == "context.tmpl"
