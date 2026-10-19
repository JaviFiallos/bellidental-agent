"""Date formatting for patients, in Spanish and in the clinic time zone (no OS locale)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

CLINIC_ZONE = "America/Guayaquil"

WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
WEEKDAYS_SHORT = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
MONTHS_SHORT = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def _to_clinic_zone(value: datetime) -> datetime:
    return value.astimezone(ZoneInfo(CLINIC_ZONE))


def format_long(value: datetime) -> str:
    """Formats like 'martes 21 de octubre, 10:30'."""
    local = _to_clinic_zone(value)
    return f"{WEEKDAYS[local.weekday()]} {local.day} de {MONTHS[local.month - 1]}, {local.strftime('%H:%M')}"


def format_day(value: date) -> str:
    """Formats like 'mar 21 oct'."""
    return f"{WEEKDAYS_SHORT[value.weekday()]} {value.day} {MONTHS_SHORT[value.month - 1]}"


def format_time(value: datetime) -> str:
    """Formats like '10:30'."""
    return _to_clinic_zone(value).strftime("%H:%M")


def format_day_time(value: datetime) -> str:
    """Formats like 'mar 21 oct 10:30'."""
    return f"{format_day(_to_clinic_zone(value).date())} {format_time(value)}"
