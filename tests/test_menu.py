from app.backend.models import ConsentStatus
from app.dialog import router
from app.dialog.models import ButtonsMessage, Conversation, IncomingMessage, ListMessage, TextMessage
from app.messages.texts import PRICES_NOTE
from tests.fakes import FakeBackend

PHONE = "593987654321"


def _text(body: str) -> IncomingMessage:
    return IncomingMessage(phone=PHONE, message_id="wamid.test", kind="text", text=body)


def _button(reply_id: str) -> IncomingMessage:
    return IncomingMessage(phone=PHONE, message_id="wamid.test", kind="button", reply_id=reply_id)


async def test_router_without_consent_sends_notice_and_ignores_other_messages() -> None:
    backend = FakeBackend()
    backend.consent_status = ConsentStatus(accepted=False, noticeVersion="v1.0")
    conversation = Conversation(phone=PHONE)

    first = await router.handle(_text("hola"), conversation, backend)
    second = await router.handle(_text("menú"), conversation, backend)

    for outgoing in (first, second):
        assert len(outgoing) == 1
        assert isinstance(outgoing[0], ButtonsMessage)
        assert [button.id for button in outgoing[0].buttons] == ["consent:yes", "consent:no"]
    assert conversation.consent_accepted is False


async def test_consent_accept_saves_consent_and_shows_menu() -> None:
    backend = FakeBackend()
    backend.consent_status = ConsentStatus(accepted=False, noticeVersion="v1.0")
    conversation = Conversation(phone=PHONE)

    outgoing = await router.handle(_button("consent:yes"), conversation, backend)

    assert len(outgoing) == 1
    assert isinstance(outgoing[0], ListMessage)
    assert conversation.consent_accepted is True


async def test_menu_human_sets_handoff_and_next_free_text_gets_no_reply() -> None:
    backend = FakeBackend()
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    handoff = await router.handle(_button("menu:human"), conversation, backend)
    assert len(handoff) == 1
    assert isinstance(handoff[0], TextMessage)
    assert conversation.handoff_until is not None

    silent = await router.handle(_text("hola"), conversation, backend)
    assert silent == []

    menu_again = await router.handle(_text("menú"), conversation, backend)
    assert len(menu_again) == 1
    assert isinstance(menu_again[0], ListMessage)
    assert conversation.handoff_until is None


async def test_menu_prices_lists_backend_prices_with_referential_note() -> None:
    backend = FakeBackend()
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    outgoing = await router.handle(_button("menu:prices"), conversation, backend)

    assert len(outgoing) == 2
    assert isinstance(outgoing[0], TextMessage)
    assert "Consulta General: $20.00" in outgoing[0].text
    assert PRICES_NOTE in outgoing[0].text
    assert isinstance(outgoing[1], ListMessage)
