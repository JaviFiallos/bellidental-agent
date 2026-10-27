from datetime import datetime

from app.backend.models import BackendError, BotPatient, Specialty
from app.dialog import router
from app.dialog.models import ButtonsMessage, Conversation, IncomingMessage, ListMessage, Step, TextMessage
from app.messages.texts import BOOK_LIMIT_TEXT, BOOK_OVERLAP_TEXT
from tests.fakes import FakeBackend

PHONE = "593987654321"
SLOT_REPLY_ID = "slot:prof-1|2026-10-21T10:30:00-05:00"


def _button(reply_id: str) -> IncomingMessage:
    return IncomingMessage(phone=PHONE, message_id="wamid.booking", kind="button", reply_id=reply_id)


def _text(body: str) -> IncomingMessage:
    return IncomingMessage(phone=PHONE, message_id="wamid.booking", kind="text", text=body)


async def _reach_confirmation(backend: FakeBackend, conversation: Conversation) -> list:
    """Drives the flow from 'menu:book' to the confirmation with a single patient."""
    await router.handle(_button("menu:book"), conversation, backend)
    await router.handle(_button("ident:yes"), conversation, backend)
    await router.handle(_button("prof:any"), conversation, backend)
    await router.handle(_button("day:2026-10-21"), conversation, backend)
    return await router.handle(_button(SLOT_REPLY_ID), conversation, backend)


async def test_booking_single_patient_full_path_confirm_books_selected_slot() -> None:
    backend = FakeBackend()
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    confirmation = await _reach_confirmation(backend, conversation)
    assert isinstance(confirmation[0], ButtonsMessage)
    done = await router.handle(_button("book:confirm"), conversation, backend)

    assert isinstance(done[0], TextMessage)
    assert len(backend.booked) == 1
    assert backend.booked[0]["professional_id"] == "prof-1"
    assert backend.booked[0]["start_at"] == datetime.fromisoformat("2026-10-21T10:30:00-05:00")


async def test_booking_confirm_overlap_reoffers_hours_of_same_day() -> None:
    backend = FakeBackend()
    backend.book_error = BackendError(status=409, code="APPOINTMENT_OVERLAP")
    conversation = Conversation(phone=PHONE, consent_accepted=True)
    await _reach_confirmation(backend, conversation)

    reoffer = await router.handle(_button("book:confirm"), conversation, backend)

    assert isinstance(reoffer[0], TextMessage)
    assert reoffer[0].text == BOOK_OVERLAP_TEXT
    assert isinstance(reoffer[-1], ListMessage)
    assert all(row.id.startswith("slot:") for row in reoffer[-1].sections[0].rows)
    assert backend.booked == []


async def test_identification_two_patients_wrong_id_twice_derives() -> None:
    backend = FakeBackend()
    backend.patients = [
        BotPatient(patientId="pat-1", displayName="Juan P."),
        BotPatient(patientId="pat-2", displayName="María L."),
    ]
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    asked = await router.handle(_button("menu:book"), conversation, backend)
    first_try = await router.handle(_text("1111111111"), conversation, backend)
    second_try = await router.handle(_text("2222222222"), conversation, backend)

    assert isinstance(asked[0], TextMessage)
    assert isinstance(first_try[0], TextMessage)
    assert conversation.handoff_until is not None
    assert isinstance(second_try[-1], TextMessage)
    assert conversation.patient_id is None


async def test_booking_limit_reached_explains_and_derives() -> None:
    backend = FakeBackend()
    backend.book_error = BackendError(status=409, code="BOT_LIMIT_REACHED")
    conversation = Conversation(phone=PHONE, consent_accepted=True)
    await _reach_confirmation(backend, conversation)

    result = await router.handle(_button("book:confirm"), conversation, backend)

    assert isinstance(result[0], TextMessage)
    assert result[0].text == BOOK_LIMIT_TEXT
    assert conversation.handoff_until is not None


async def test_booking_specialty_without_professionals_offers_other_specialties() -> None:
    backend = FakeBackend()
    backend.specialties.append(
        Specialty.model_validate({"specialtyId": 2, "name": "Endodoncia", "durationMinutes": 30})
    )
    backend.professionals = []
    conversation = Conversation(phone=PHONE, consent_accepted=True)
    await router.handle(_button("menu:book"), conversation, backend)
    await router.handle(_button("ident:yes"), conversation, backend)

    reply = await router.handle(_button("spec:1"), conversation, backend)

    assert len(reply) == 2
    assert isinstance(reply[0], TextMessage)
    assert isinstance(reply[1], ListMessage)
    assert all(row.id != "spec:1" for row in reply[1].sections[0].rows)
    assert conversation.step == Step.BOOK_SPECIALTY
    assert conversation.handoff_until is None
