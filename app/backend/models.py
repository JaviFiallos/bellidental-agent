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
