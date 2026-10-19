from datetime import datetime

from app.backend.models import BackendError, DueReminder, ReminderResponse
from app.config import Settings
from app.dialog import router
from app.dialog.models import Conversation, IncomingMessage, ListMessage, Step, TemplateMessage, TextMessage
from app.dialog.reminder_reply import CONFIRM_PAYLOAD, RESCHEDULE_PAYLOAD
from app.messages.texts import REMINDER_CONFIRMED_TEXT
from app.reminders import job
from tests.fakes import FakeBackend, FakeSender

PHONE = "593987654321"
WA_MESSAGE_ID = "wamid.reminder-1"


def _settings() -> Settings:
    return Settings(_env_file=None)


def _due_reminder() -> DueReminder:
    return DueReminder(
        reminderId="rem-1",
        appointmentId="appt-1",
        phone=PHONE,
        patientFirstName="Juan",
        professionalName="Odontóloga Principal",
        startAt=datetime.fromisoformat("2026-10-21T10:30:00-05:00"),
    )


def _template_button(reply_id: str) -> IncomingMessage:
    return IncomingMessage(
        phone=PHONE,
        message_id="wamid.button",
        kind="template_button",
        reply_id=reply_id,
        context_message_id=WA_MESSAGE_ID,
    )


async def test_job_sends_template_and_marks_sent_with_wamid() -> None:
    backend = FakeBackend()
    backend.due_reminders = [_due_reminder()]
    sender = FakeSender()

    await job.run_once(backend, sender, _settings())

    _, message = sender.sent[0]
    assert isinstance(message, TemplateMessage)
    assert message.name == "recordatorio_cita"
    assert message.body_parameters == ["Juan", "miércoles 21 de octubre", "10:30", "Odontóloga Principal"]
    assert message.button_payloads == ["reminder:confirm", "reminder:cancel", "reminder:reschedule"]
    assert backend.sent_reminders == [("rem-1", "fake-wamid-1")]


async def test_job_send_fails_twice_marks_failed() -> None:
    backend = FakeBackend()
    backend.due_reminders = [_due_reminder()]
    sender = FakeSender()
    sender.error = RuntimeError("graph down")

    await job.run_once(backend, sender, _settings())

    assert sender.attempts == 2
    assert backend.failed_reminders == ["rem-1"]
    assert backend.sent_reminders == []


async def test_reminder_confirm_button_posts_response_with_context_id_and_thanks() -> None:
    backend = FakeBackend()
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    messages = await router.handle(_template_button(CONFIRM_PAYLOAD), conversation, backend)

    assert messages == [TextMessage(text=REMINDER_CONFIRMED_TEXT)]
    assert backend.reminder_responses == [
        {"wa_message_id": WA_MESSAGE_ID, "phone": PHONE, "response": "CONFIRMED"}
    ]


async def test_reminder_reschedule_outcome_starts_reschedule_flow() -> None:
    backend = FakeBackend()
    backend.reminder_outcome = ReminderResponse(
        outcome="RESCHEDULE_REQUESTED", appointmentId="appt-1", patientId="pat-1"
    )
    conversation = Conversation(phone=PHONE, consent_accepted=True)

    messages = await router.handle(_template_button(RESCHEDULE_PAYLOAD), conversation, backend)

    assert conversation.step == Step.RESCHEDULE_DAY
    assert conversation.patient_id == "pat-1"
    assert isinstance(messages[0], ListMessage)
    assert len(messages[0].sections[0].rows) == len(backend.available_days)
