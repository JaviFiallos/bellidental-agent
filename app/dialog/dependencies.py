from typing import Protocol

from app.backend.models import BotPatient, ClinicInfo, ConsentStatus
from app.dialog.models import OutgoingMessage


class Backend(Protocol):
    """Protocol defining methods required from the backend service."""

    async def get_consent(self, phone: str) -> ConsentStatus: ...

    async def accept_consent(self, phone: str, patient_id: str | None = None) -> ConsentStatus: ...

    async def get_info(self) -> ClinicInfo: ...

    async def get_patients(self, phone: str) -> list[BotPatient]: ...

    async def verify_patient(self, phone: str, id_number: str) -> BotPatient: ...


class Sender(Protocol):
    """Protocol defining message sending capability."""

    async def send(self, phone: str, message: OutgoingMessage) -> str: ...
