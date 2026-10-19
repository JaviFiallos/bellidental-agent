from datetime import date, datetime
from typing import Protocol

from app.backend.models import (
    Appointment,
    BotPatient,
    ClinicInfo,
    ConsentStatus,
    Professional,
    Slot,
    Specialty,
    UrgentSlots,
)
from app.dialog.models import OutgoingMessage
from app.nlu.classifier import Classifier

__all__ = ["Backend", "Classifier", "Sender"]


class Backend(Protocol):
    """Protocol defining methods required from the backend service."""

    async def get_consent(self, phone: str) -> ConsentStatus: ...

    async def accept_consent(self, phone: str, patient_id: str | None = None) -> ConsentStatus: ...

    async def get_info(self) -> ClinicInfo: ...

    async def get_patients(self, phone: str) -> list[BotPatient]: ...

    async def verify_patient(self, phone: str, id_number: str) -> BotPatient: ...

    async def get_specialties(self) -> list[Specialty]: ...

    async def get_professionals(self, specialty_id: str) -> list[Professional]: ...

    async def get_available_days(self, specialty_id: str, professional_id: str | None = None) -> list[date]: ...

    async def get_slots(
        self, specialty_id: str, day: date, professional_id: str | None = None
    ) -> list[Slot]: ...

    async def book_appointment(
        self,
        phone: str,
        patient_id: str,
        specialty_id: str,
        professional_id: str,
        start_at: datetime,
    ) -> Appointment: ...

    async def get_urgent_slots(self) -> UrgentSlots: ...

    async def get_appointments(self, phone: str, patient_id: str) -> list[Appointment]: ...

    async def reschedule_appointment(self, phone: str, appointment_id: str, start_at: datetime) -> Appointment: ...

    async def cancel_appointment(self, phone: str, appointment_id: str) -> None: ...

    async def confirm_appointment(self, phone: str, appointment_id: str) -> None: ...


class Sender(Protocol):
    """Protocol defining message sending capability."""

    async def send(self, phone: str, message: OutgoingMessage) -> str: ...
