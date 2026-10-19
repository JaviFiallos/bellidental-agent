from datetime import date, datetime
from typing import Any

from app.backend.models import (
    Appointment,
    BackendError,
    BotPatient,
    ClinicInfo,
    ConsentStatus,
    Professional,
    PublicPrice,
    Slot,
    Specialty,
)
from app.dialog.models import OutgoingMessage


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
            Specialty(specialtyId="spec-1", name="Odontología general", durationMinutes=30)
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
        self.book_error: BackendError | None = None
        self.booked: list[dict[str, Any]] = []

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


class FakeSender:
    """Fake implementation of Sender protocol that records sent messages."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, OutgoingMessage]] = []

    async def send(self, phone: str, message: OutgoingMessage) -> str:
        self.sent.append((phone, message))
        return f"fake-wamid-{len(self.sent)}"
