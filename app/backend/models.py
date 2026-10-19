from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConsentStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    accepted: bool
    notice_version: str = Field(alias="noticeVersion")


class PublicPrice(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str
    name: str
    price: float


class ClinicInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    clinic_name: str = Field(alias="clinicName")
    address: str
    hours: list[str]
    payment_methods: list[str] = Field(alias="paymentMethods")
    reception_whatsapp: str = Field(alias="receptionWhatsapp")
    after_hours_phone: str = Field(alias="afterHoursPhone")
    prices: list[PublicPrice] = Field(default_factory=list)


class BotPatient(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    patient_id: str = Field(alias="patientId")
    display_name: str = Field(alias="displayName")


class BackendError(Exception):
    """Exception raised when a backend request returns an error HTTP status."""

    def __init__(self, status: int, code: str | None = None) -> None:
        self.status = status
        self.code = code
        super().__init__(f"Backend returned status {status} (code: {code})")


class Specialty(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    specialty_id: str = Field(alias="specialtyId")
    name: str
    duration_minutes: int = Field(alias="durationMinutes")


class Professional(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    professional_id: str = Field(alias="professionalId")
    display_name: str = Field(alias="displayName")


class Slot(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    professional_id: str = Field(alias="professionalId")
    professional_name: str = Field(alias="professionalName")
    start_at: datetime = Field(alias="startAt")
    end_at: datetime = Field(alias="endAt")


class Appointment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    appointment_id: str = Field(alias="appointmentId")
    specialty_id: str = Field(alias="specialtyId")
    specialty_name: str = Field(alias="specialtyName")
    professional_id: str = Field(alias="professionalId")
    professional_name: str = Field(alias="professionalName")
    start_at: datetime = Field(alias="startAt")
    status: str


class UrgentSlots(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    specialty_id: str = Field(alias="specialtyId")
    no_slots_today: bool = Field(alias="noSlotsToday")
    slots: list[Slot] = Field(default_factory=list)


class DueReminder(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reminder_id: str = Field(alias="reminderId")
    appointment_id: str = Field(alias="appointmentId")
    phone: str
    patient_first_name: str = Field(alias="patientFirstName")
    professional_name: str = Field(alias="professionalName")
    start_at: datetime = Field(alias="startAt")


class ReminderResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    outcome: str
    appointment_id: str = Field(alias="appointmentId")
    patient_id: str = Field(alias="patientId")
