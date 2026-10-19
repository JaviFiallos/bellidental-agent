from app.backend.models import BotPatient, ClinicInfo, ConsentStatus, PublicPrice
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

    async def get_consent(self, phone: str) -> ConsentStatus:
        return self.consent_status

    async def accept_consent(self, phone: str, patient_id: str | None = None) -> ConsentStatus:
        return self.consent_status

    async def get_info(self) -> ClinicInfo:
        return self.clinic_info

    async def get_patients(self, phone: str) -> list[BotPatient]:
        return self.patients

    async def verify_patient(self, phone: str, id_number: str) -> BotPatient:
        return self.patients[0]


class FakeSender:
    """Fake implementation of Sender protocol that records sent messages."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, OutgoingMessage]] = []

    async def send(self, phone: str, message: OutgoingMessage) -> str:
        self.sent.append((phone, message))
        return f"fake-wamid-{len(self.sent)}"
