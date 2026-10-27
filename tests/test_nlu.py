from datetime import datetime, timezone

import anthropic
import httpx

from app.backend.models import BotPatient
from app.config import Settings
from app.dialog import router
from app.dialog.models import ButtonsMessage, Conversation, IncomingMessage, ListMessage, TextMessage
from app.main import build_classifier
from app.messages.texts import URGENT_EMERGENCY_TEXT, single_price_text
from app.nlu.anthropic_classifier import AnthropicClassifier
from app.nlu.models import Intent, Interpretation
from app.nlu.openai_compatible import OpenAICompatibleClassifier
from tests.fakes import FakeBackend, FakeClassifier

PHONE = "593987654321"


def _text(body: str) -> IncomingMessage:
    return IncomingMessage(phone=PHONE, message_id="wamid.nlu", kind="text", text=body)


def _button(reply_id: str) -> IncomingMessage:
    return IncomingMessage(phone=PHONE, message_id="wamid.nlu", kind="button", reply_id=reply_id)


async def test_free_text_urgent_sends_emergency_text_then_slot_buttons() -> None:
    backend = FakeBackend()
    classifier = FakeClassifier()
    classifier.result = Interpretation(intent=Intent.URGENT)
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    reply = await router.handle(_text("me duele mucho una muela"), conversation, backend, classifier)

    assert isinstance(reply[0], TextMessage)
    assert reply[0].text == URGENT_EMERGENCY_TEXT
    assert isinstance(reply[-1], ButtonsMessage)
    assert 1 <= len(reply[-1].buttons) <= 3
    assert all(len(button.title) <= 20 for button in reply[-1].buttons)


async def test_free_text_price_known_treatment_replies_only_that_price() -> None:
    backend = FakeBackend()
    classifier = FakeClassifier()
    classifier.result = Interpretation(intent=Intent.PRICE, treatment="consulta")
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    reply = await router.handle(_text("cuánto cuesta una consulta"), conversation, backend, classifier)

    assert isinstance(reply[0], TextMessage)
    assert reply[0].text == single_price_text(backend.clinic_info.prices[0])
    assert "Formas de pago" not in reply[0].text


async def test_classifier_failure_shows_menu() -> None:
    backend = FakeBackend()
    classifier = FakeClassifier()
    classifier.result = None
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    reply = await router.handle(_text("hola"), conversation, backend, classifier)

    assert isinstance(reply[-1], ListMessage)
    assert conversation.unknown_count == 0


async def test_identity_step_never_calls_classifier() -> None:
    backend = FakeBackend()
    backend.patients = [
        BotPatient(patientId="pat-1", displayName="Juan P."),
        BotPatient(patientId="pat-2", displayName="María L."),
    ]
    backend.id_numbers["1712345678"] = BotPatient(patientId="pat-1", displayName="Juan P.")
    classifier = FakeClassifier()
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    await router.handle(_button("menu:book"), conversation, backend, classifier)
    await router.handle(_text("1712345678"), conversation, backend, classifier)

    assert classifier.calls == []


async def test_free_text_payment_intent_explains_and_hands_off() -> None:
    backend = FakeBackend()
    classifier = FakeClassifier()
    classifier.result = Interpretation(intent=Intent.PAYMENT)
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    reply = await router.handle(_text("quiero pagar"), conversation, backend, classifier)

    assert len(reply) == 2
    assert isinstance(reply[0], TextMessage)
    assert "no recibimos pagos" in reply[0].text
    assert conversation.handoff_until is not None
    assert conversation.handoff_until > datetime.now(timezone.utc)


def test_build_classifier_claude_model_selects_anthropic() -> None:
    http_client = httpx.AsyncClient()
    anthropic_client = anthropic.AsyncAnthropic(api_key="k")

    claude = build_classifier(
        Settings(llm_api_key="k", llm_model="claude-haiku-5-5"), http_client, anthropic_client
    )
    qwen = build_classifier(
        Settings(llm_api_key="k", llm_model="qwen/qwen3-32b"), http_client, anthropic_client
    )

    assert isinstance(claude, AnthropicClassifier)
    assert isinstance(qwen, OpenAICompatibleClassifier)
