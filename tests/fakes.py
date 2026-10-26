from datetime import date, datetime
from typing import Any

from app.backend.models import (
    Appointment,
    BackendError,
    BotPatient,
    ClinicInfo,
    ConsentStatus,
    DueReminder,
    Professional,
    PublicPrice,
    ReminderResponse,
    Slot,
    Specialty,
    UrgentSlots,
)
from app.dialog.models import OutgoingMessage, Step
from app.nlu.models import Interpretation


class FakeBackend:
    """Fake implementation of Backend protocol for tests."""

    def __init__(self) -> None:
        self.consent_status = ConsentStatus(accepted=True, noticeVersion="v1.0")
        self.clinic_info = ClinicInfo(
            clinicName="Bellidental",
            address="Av. Cevallos y Montalvo",
            hours=["09:00-18:00"],
            paymentMethods=["Efectivo", "Transferencia"],
            receptionWhatsapp="593987654321",
            afterHoursPhone="593987654322",
            prices=[PublicPrice(code="CONS", name="Consulta General", price=20.0)],
        )
        self.patients: list[BotPatient] = [
            BotPatient(patientId="pat-1", displayName="Juan P.")
        ]
        self.id_numbers: dict[str, BotPatient] = {}
        self.specialties: list[Specialty] = [
            Specialty.model_validate({"specialtyId": 1, "name": "Odontología general", "durationMinutes": 30})
        ]
        self.professionals: list[Professional] = [
            Professional(professionalId="prof-1", displayName="Odontóloga Principal"),
            Professional(professionalId="prof-2", displayName="Dr. Ramírez"),
        ]
        self.available_days: list[date] = [date(2026, 10, 21), date(2026, 10, 22)]
        self.slots: list[Slot] = [
            Slot(
                professionalId="prof-1",
                professionalName="Odontóloga Principal",
                startAt=datetime.fromisoformat("2026-10-21T10:30:00-05:00"),
                endAt=datetime.fromisoformat("2026-10-21T11:00:00-05:00"),
            ),
            Slot(
                professionalId="prof-2",
                professionalName="Dr. Ramírez",
                startAt=datetime.fromisoformat("2026-10-21T11:00:00-05:00"),
                endAt=datetime.fromisoformat("2026-10-21T11:30:00-05:00"),
            ),
        ]
        self.specialties_error: Exception | None = None
        self.book_error: BackendError | None = None
        self.booked: list[dict[str, Any]] = []
        self.appointments: list[Appointment] = [
            Appointment.model_validate(
                {
                    "appointmentId": "appt-1",
                    "specialtyId": 1,
                    "specialtyName": "Odontología general",
                    "professionalId": "prof-1",
                    "professionalName": "Odontóloga Principal",
                    "startAt": "2026-10-21T10:30:00-05:00",
                    "status": "PENDING",
                }
            )
        ]
        self.urgent_slots = UrgentSlots.model_validate(
            {"specialtyId": 99, "noSlotsToday": False, "slots": self.slots}
        )
        self.reschedule_error: BackendError | None = None
        self.cancel_error: BackendError | None = None
        self.rescheduled: list[dict[str, Any]] = []
        self.cancelled: list[str] = []
        self.due_reminders: list[DueReminder] = []
        self.sent_reminders: list[tuple[str, str]] = []
        self.failed_reminders: list[str] = []
        self.reminder_outcome = ReminderResponse(outcome="CONFIRMED", appointmentId="appt-1", patientId="pat-1")
        self.reminder_responses: list[dict[str, str]] = []

    async def get_consent(self, phone: str) -> ConsentStatus:
        return self.consent_status

    async def accept_consent(self, phone: str, patient_id: str | None = None) -> ConsentStatus:
        return self.consent_status

    async def get_info(self) -> ClinicInfo:
        return self.clinic_info

    async def get_patients(self, phone: str) -> list[BotPatient]:
        return self.patients

    async def verify_patient(self, phone: str, id_number: str) -> BotPatient:
        if id_number not in self.id_numbers:
            raise BackendError(status=404, code=None)
        return self.id_numbers[id_number]

    async def get_specialties(self) -> list[Specialty]:
        if self.specialties_error is not None:
            raise self.specialties_error
        return self.specialties

    async def get_professionals(self, specialty_id: str) -> list[Professional]:
        return self.professionals

    async def get_available_days(self, specialty_id: str, professional_id: str | None = None) -> list[date]:
        return self.available_days

    async def get_slots(
        self, specialty_id: str, day: date, professional_id: str | None = None
    ) -> list[Slot]:
        return [slot for slot in self.slots if professional_id is None or slot.professional_id == professional_id]

    async def book_appointment(
        self,
        phone: str,
        patient_id: str,
        specialty_id: str,
        professional_id: str,
        start_at: datetime,
    ) -> Appointment:
        if self.book_error is not None:
            raise self.book_error
        self.booked.append(
            {
                "phone": phone,
                "patient_id": patient_id,
                "specialty_id": specialty_id,
                "professional_id": professional_id,
                "start_at": start_at,
            }
        )
        professional_name = next(
            item.display_name for item in self.professionals if item.professional_id == professional_id
        )
        return Appointment(
            appointmentId="appt-1",
            specialtyId=specialty_id,
            specialtyName=self.specialties[0].name,
            professionalId=professional_id,
            professionalName=professional_name,
            startAt=start_at,
            status="CONFIRMED",
        )


    async def get_urgent_slots(self) -> UrgentSlots:
        return self.urgent_slots

    async def get_appointments(self, phone: str, patient_id: str) -> list[Appointment]:
        return self.appointments

    async def reschedule_appointment(self, phone: str, appointment_id: str, start_at: datetime) -> Appointment:
        if self.reschedule_error is not None:
            raise self.reschedule_error
        self.rescheduled.append({"phone": phone, "appointment_id": appointment_id, "start_at": start_at})
        return self.appointments[0]

    async def cancel_appointment(self, phone: str, appointment_id: str) -> None:
        if self.cancel_error is not None:
            raise self.cancel_error
        self.cancelled.append(appointment_id)

    async def confirm_appointment(self, phone: str, appointment_id: str) -> None:
        return None

    async def get_due_reminders(self) -> list[DueReminder]:
        return self.due_reminders

    async def mark_reminder_sent(self, reminder_id: str, wa_message_id: str) -> None:
        self.sent_reminders.append((reminder_id, wa_message_id))

    async def mark_reminder_failed(self, reminder_id: str) -> None:
        self.failed_reminders.append(reminder_id)

    async def send_reminder_response(self, wa_message_id: str, phone: str, response: str) -> ReminderResponse:
        self.reminder_responses.append({"wa_message_id": wa_message_id, "phone": phone, "response": response})
        return self.reminder_outcome


class FakeClassifier:
    """Fake implementation of the Classifier protocol: returns a fixed result and records every call."""

    def __init__(self) -> None:
        self.result: Interpretation | None = None
        self.error: Exception | None = None
        self.calls: list[tuple[str, Step, list[str]]] = []

    async def classify(self, text: str, step: Step, recent: list[str]) -> Interpretation | None:
        self.calls.append((text, step, recent))
        if self.error is not None:
            raise self.error
        return self.result


class FakeSender:
    """Fake implementation of Sender protocol that records sent messages."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, OutgoingMessage]] = []
        self.error: Exception | None = None
        self.attempts = 0

    async def send(self, phone: str, message: OutgoingMessage) -> str:
        self.attempts += 1
        if self.error is not None:
            raise self.error
        self.sent.append((phone, message))
        return f"fake-wamid-{len(self.sent)}"
