from datetime import date, datetime

from app.backend.models import BackendError, BotPatient, Slot
from app.dialog import router
from app.dialog.models import (
    ButtonsMessage,
    Conversation,
    IncomingMessage,
    ListMessage,
    Step,
    TextMessage,
)
from app.messages.texts import (
    APPOINTMENT_TOO_LATE_TEXT,
    APPOINTMENTS_OTHER_PERSON_TEXT,
    IDENTIFY_ASK_ID_TEXT,
    NO_APPOINTMENTS_TEXT,
)
from app.nlu.models import Intent, Interpretation
from tests.fakes import FakeBackend, FakeClassifier

PHONE = "593987654321"


def _button(reply_id: str) -> IncomingMessage:
    return IncomingMessage(phone=PHONE, message_id="wamid.appointments", kind="button", reply_id=reply_id)


def _text(body: str) -> IncomingMessage:
    return IncomingMessage(phone=PHONE, message_id="wamid.appointments.text", kind="text", text=body)


async def test_reschedule_full_path_calls_reschedule_with_new_slot() -> None:
    backend = FakeBackend()
    backend.available_days = [date(2026, 10, 23)]
    backend.slots = [
        Slot(
            professionalId="prof-1",
            professionalName="Odontóloga Principal",
            startAt=datetime.fromisoformat("2026-10-23T16:00:00-05:00"),
            endAt=datetime.fromisoformat("2026-10-23T16:30:00-05:00"),
        )
    ]
    conversation = Conversation(phone=PHONE, consent_accepted=True)
    await router.handle(_button("menu:appointments"), conversation, backend)
    await router.handle(_button("appt:appt-1"), conversation, backend)
    await router.handle(_button("appt:reschedule"), conversation, backend)
    await router.handle(_button("day:2026-10-23"), conversation, backend)
    await router.handle(_button("slot:prof-1|2026-10-23T16:00:00-05:00"), conversation, backend)

    confirmation = await router.handle(_button("resched:confirm"), conversation, backend)

    assert isinstance(confirmation[0], TextMessage)
    assert backend.rescheduled[0]["appointment_id"] == "appt-1"
    assert backend.rescheduled[0]["start_at"] == datetime.fromisoformat("2026-10-23T16:00:00-05:00")
    assert conversation.step == Step.IDLE


async def test_cancel_too_late_explains_and_derives() -> None:
    backend = FakeBackend()
    backend.cancel_error = BackendError(status=409, code="BOT_TOO_LATE")
    conversation = Conversation(phone=PHONE, consent_accepted=True)
    await router.handle(_button("menu:appointments"), conversation, backend)
    await router.handle(_button("appt:appt-1"), conversation, backend)
    await router.handle(_button("appt:cancel"), conversation, backend)

    result = await router.handle(_button("cancel:yes"), conversation, backend)

    assert result[0].text == APPOINTMENT_TOO_LATE_TEXT
    assert conversation.handoff_until is not None
    assert backend.cancelled == []


async def test_my_appointments_none_offers_booking() -> None:
    backend = FakeBackend()
    backend.appointments = []
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    result = await router.handle(_button("menu:appointments"), conversation, backend)

    assert isinstance(result[0], ButtonsMessage)
    assert result[0].text == NO_APPOINTMENTS_TEXT
    assert "menu:book" in [button.id for button in result[0].buttons]
    assert conversation.step == Step.IDLE


async def test_appointments_single_patient_lists_without_confirm() -> None:
    backend = FakeBackend()
    classifier = FakeClassifier()
    classifier.result = Interpretation(intent=Intent.APPOINTMENTS)
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    messages = await router.handle(_text("quiero ver mis citas"), conversation, backend, classifier)

    assert isinstance(messages[0], ListMessage)
    assert conversation.step == Step.APPT_CHOOSE
    assert conversation.patient_id == "pat-1"


async def test_appointments_other_person_single_patient_refuses() -> None:
    backend = FakeBackend()
    classifier = FakeClassifier()
    classifier.result = Interpretation(intent=Intent.APPOINTMENTS, other_person=True)
    conversation = Conversation(phone=PHONE, consent_accepted=True, patient_id="pat-1", patient_name="Juan P.")

    messages = await router.handle(_text("quiero ver las citas de mi hermano"), conversation, backend, classifier)

    assert messages[0].text == APPOINTMENTS_OTHER_PERSON_TEXT
    assert conversation.step == Step.MENU
    assert conversation.patient_id is None


async def test_appointments_other_person_several_patients_asks_id() -> None:
    backend = FakeBackend()
    backend.patients = [
        BotPatient(patientId="pat-1", displayName="Juan P."),
        BotPatient(patientId="pat-2", displayName="María P."),
    ]
    classifier = FakeClassifier()
    classifier.result = Interpretation(intent=Intent.APPOINTMENTS, other_person=True)
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    messages = await router.handle(_text("quiero ver las citas de mi hermano"), conversation, backend, classifier)

    assert conversation.step == Step.IDENTIFY_ID
    assert messages[0].text == IDENTIFY_ASK_ID_TEXT
