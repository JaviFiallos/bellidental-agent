from datetime import timedelta

from app.backend.models import ProfessionalSchedule, ScheduleDay, Shift, Specialty
from app.dialog import router
from app.dialog.hints import resolve_date_hint
from app.dialog.models import ButtonsMessage, Conversation, IncomingMessage, TextMessage
from app.messages.dates import clinic_today
from app.nlu.models import Intent, Interpretation
from tests.fakes import FakeBackend, FakeClassifier

PHONE = "593987654321"


def _button(reply_id: str) -> IncomingMessage:
    return IncomingMessage(phone=PHONE, message_id="wamid.hours", kind="button", reply_id=reply_id)


def _text(body: str) -> IncomingMessage:
    return IncomingMessage(phone=PHONE, message_id="wamid.hours.text", kind="text", text=body)


async def test_hours_specialty_shows_week_and_buttons() -> None:
    backend = FakeBackend()
    backend.specialties = [Specialty(specialtyId="spec-1", name="Ortodoncia", durationMinutes=30)]

    today = clinic_today()
    prof1 = ProfessionalSchedule(
        professionalId="prof-1",
        professionalName="Dra. Ana P.",
        days=[
            ScheduleDay(date=today, shifts=[Shift(startTime="08:00", endTime="12:00")]),
            ScheduleDay(date=today + timedelta(days=1), shifts=[]),
        ],
    )
    prof2 = ProfessionalSchedule(
        professionalId="prof-2",
        professionalName="Dr. Juan M.",
        days=[
            ScheduleDay(date=today, shifts=[Shift(startTime="14:00", endTime="18:00")]),
            ScheduleDay(date=today + timedelta(days=1), shifts=[Shift(startTime="14:00", endTime="18:00")]),
        ],
    )
    backend.schedules = [prof1, prof2]

    conversation = Conversation(phone=PHONE, consent_accepted=True)
    messages = await router.handle(_button("hours:spec:spec-1:0"), conversation, backend)

    assert len(messages) == 2
    assert isinstance(messages[0], TextMessage)
    assert "Dra. Ana P." in messages[0].text
    assert "Dr. Juan M." in messages[0].text
    assert "no atiende" in messages[0].text

    assert isinstance(messages[1], ButtonsMessage)
    button_ids = [button.id for button in messages[1].buttons]
    assert "hours:book:spec-1" in button_ids
    assert "hours:spec:spec-1:1" in button_ids


async def test_hours_next_week_has_no_next_button() -> None:
    backend = FakeBackend()
    backend.specialties = [Specialty(specialtyId="spec-1", name="Ortodoncia", durationMinutes=30)]

    today = clinic_today()
    prof = ProfessionalSchedule(
        professionalId="prof-1",
        professionalName="Dra. Ana P.",
        days=[
            ScheduleDay(date=today + timedelta(days=7), shifts=[Shift(startTime="08:00", endTime="12:00")]),
        ],
    )
    backend.schedules = [prof]

    conversation = Conversation(phone=PHONE, consent_accepted=True)
    messages = await router.handle(_button("hours:spec:spec-1:1"), conversation, backend)

    assert backend.schedule_calls[0]["from_day"] == today + timedelta(days=7)

    assert isinstance(messages[1], ButtonsMessage)
    button_titles = [button.title for button in messages[1].buttons]
    assert "Semana siguiente" not in button_titles


async def test_hours_text_day_without_shifts_says_no_attention() -> None:
    backend = FakeBackend()
    backend.schedules = []

    classifier = FakeClassifier()
    classifier.result = Interpretation(intent=Intent.HOURS, date_hint="sábado")

    conversation = Conversation(phone=PHONE, consent_accepted=True)
    messages = await router.handle(_text("atienden el sábado"), conversation, backend, classifier)

    today = clinic_today()
    available = [today + timedelta(days=i) for i in range(14)]
    expected_saturday = resolve_date_hint("sábado", today, available)

    assert backend.schedule_calls[0]["from_day"] == expected_saturday
    assert backend.schedule_calls[0]["to_day"] == expected_saturday
    assert "no hay atención" in messages[0].text


async def test_hours_text_professional_shows_only_matching() -> None:
    backend = FakeBackend()
    today = clinic_today()
    prof1 = ProfessionalSchedule(
        professionalId="prof-1",
        professionalName="Dra. Ana P.",
        days=[ScheduleDay(date=today, shifts=[Shift(startTime="08:00", endTime="12:00")])],
    )
    prof2 = ProfessionalSchedule(
        professionalId="prof-2",
        professionalName="Dra. Mariana R.",
        days=[ScheduleDay(date=today, shifts=[Shift(startTime="09:00", endTime="13:00")])],
    )
    backend.schedules = [prof1, prof2]

    classifier = FakeClassifier()
    classifier.result = Interpretation(intent=Intent.HOURS, professional="ana")

    conversation = Conversation(phone=PHONE, consent_accepted=True)
    messages = await router.handle(_text("qué horario tiene la doctora Ana"), conversation, backend, classifier)

    assert isinstance(messages[0], TextMessage)
    assert "Ana" in messages[0].text
    assert "Mariana" not in messages[0].text

