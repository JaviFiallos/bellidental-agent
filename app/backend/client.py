from datetime import date, datetime
from typing import Any

import httpx

from app.backend.models import (
    Appointment,
    BackendError,
    BotPatient,
    ClinicInfo,
    ConsentStatus,
    Professional,
    Slot,
    Specialty,
)


class BackendClient:
    """Async HTTP client for Bellidental internal backend bot API (/api/v1/bot/*)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = client

    def _headers(self) -> dict[str, str]:
        return {
            "X-Bot-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _unwrap(self, response: httpx.Response) -> Any:
        if response.is_error:
            code: str | None = None
            try:
                body = response.json()
                if isinstance(body, dict):
                    code = body.get("code")
            except Exception:
                pass
            raise BackendError(status=response.status_code, code=code)

        response_body = response.json()
        if isinstance(response_body, dict) and "data" in response_body:
            return response_body["data"]
        return response_body

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        headers = self._headers()

        try:
            if self._client is not None:
                response = await self._client.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers=headers,
                    timeout=self.timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method,
                        url,
                        params=params,
                        json=json_body,
                        headers=headers,
                        timeout=self.timeout,
                    )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise BackendError(status=0, code=None) from exc

        return self._unwrap(response)

    async def get_consent(self, phone: str) -> ConsentStatus:
        consent_payload = await self._request("GET", "/api/v1/bot/consents", params={"phone": phone})
        return ConsentStatus.model_validate(consent_payload)

    async def accept_consent(self, phone: str, patient_id: str | None = None) -> ConsentStatus:
        body: dict[str, Any] = {"phone": phone}
        if patient_id is not None:
            body["patientId"] = patient_id
        consent_payload = await self._request("POST", "/api/v1/bot/consents", json_body=body)
        return ConsentStatus.model_validate(consent_payload)

    async def get_info(self) -> ClinicInfo:
        clinic_payload = await self._request("GET", "/api/v1/bot/info")
        return ClinicInfo.model_validate(clinic_payload)

    async def get_patients(self, phone: str) -> list[BotPatient]:
        patients_payload = await self._request("GET", "/api/v1/bot/patients", params={"phone": phone})
        return [BotPatient.model_validate(item) for item in patients_payload]

    async def verify_patient(self, phone: str, id_number: str) -> BotPatient:
        patient_payload = await self._request(
            "POST",
            "/api/v1/bot/patients/verify",
            json_body={"phone": phone, "idNumber": id_number},
        )
        return BotPatient.model_validate(patient_payload)

    async def get_specialties(self) -> list[Specialty]:
        specialties_payload = await self._request("GET", "/api/v1/bot/specialties")
        return [Specialty.model_validate(item) for item in specialties_payload]

    async def get_professionals(self, specialty_id: str) -> list[Professional]:
        professionals_payload = await self._request(
            "GET", "/api/v1/bot/professionals", params={"specialtyId": specialty_id}
        )
        return [Professional.model_validate(item) for item in professionals_payload]

    async def get_available_days(self, specialty_id: str, professional_id: str | None = None) -> list[date]:
        days_payload = await self._request(
            "GET",
            "/api/v1/bot/availability/days",
            params=_availability_params(specialty_id, professional_id),
        )
        return [date.fromisoformat(item) for item in days_payload]

    async def get_slots(
        self,
        specialty_id: str,
        day: date,
        professional_id: str | None = None,
    ) -> list[Slot]:
        params = _availability_params(specialty_id, professional_id)
        params["date"] = day.isoformat()
        slots_payload = await self._request("GET", "/api/v1/bot/availability", params=params)
        return [Slot.model_validate(item) for item in slots_payload]

    async def book_appointment(
        self,
        phone: str,
        patient_id: str,
        specialty_id: str,
        professional_id: str,
        start_at: datetime,
    ) -> Appointment:
        body: dict[str, Any] = {
            "phone": phone,
            "patientId": patient_id,
            "specialtyId": specialty_id,
            "professionalId": professional_id,
            "startAt": start_at.isoformat(),
        }
        appointment_payload = await self._request("POST", "/api/v1/bot/appointments", json_body=body)
        return Appointment.model_validate(appointment_payload)


def _availability_params(specialty_id: str, professional_id: str | None) -> dict[str, str]:
    params = {"specialtyId": specialty_id}
    if professional_id is not None:
        params["professionalId"] = professional_id
    return params
