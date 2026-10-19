"""Patient-facing text constants in Spanish."""

from app.backend.models import ClinicInfo

UNSUPPORTED_MESSAGE = "Por ahora solo puedo leer mensajes de texto."

CONSENT_NOTICE = (
    "Antes de atenderle necesitamos su permiso. Para gestionar sus citas y recordatorios usamos su número "
    "de teléfono, su nombre y los datos de sus citas. Los tratan por encargo de la clínica Meta (WhatsApp), "
    "el proveedor del servidor y el proveedor de inteligencia artificial que interpreta sus mensajes. "
    "Puede pedir la eliminación de sus datos en recepción.\n\n¿Acepta?"
)
CONSENT_YES_TITLE = "Acepto"
CONSENT_NO_TITLE = "No acepto"

MENU_TEXT = "¿En qué le podemos ayudar?"
MENU_BUTTON_TEXT = "Ver opciones"
MENU_SECTION_TITLE = "Opciones"
MENU_ROW_HOURS = "Horarios"
MENU_ROW_PRICES = "Precios y pagos"
MENU_ROW_BOOK = "Agendar cita"
MENU_ROW_APPOINTMENTS = "Mis citas"
MENU_ROW_HUMAN = "Hablar con recepción"

PRICES_NOTE = "Valores referenciales; el valor definitivo lo da el odontólogo tras la valoración."


def _wa_link(reception_whatsapp: str) -> str:
    return f"https://wa.me/{reception_whatsapp}"


def consent_refused_text(reception_whatsapp: str) -> str:
    base = "Sin su aceptación no podemos atenderle por este medio."
    if not reception_whatsapp:
        return base
    return f"{base} Puede escribir a recepción: {_wa_link(reception_whatsapp)}"


def technical_problem_text(reception_whatsapp: str) -> str:
    base = "Tenemos un problema técnico."
    if not reception_whatsapp:
        return base
    return f"{base} Escriba a recepción: {_wa_link(reception_whatsapp)}"


def handoff_text(info: ClinicInfo) -> str:
    hours = "\n".join(info.hours)
    return (
        f"Le atenderá recepción en el horario de atención:\n{hours}\n"
        f"Escriba a recepción: {_wa_link(info.reception_whatsapp)}"
    )


def hours_text(info: ClinicInfo) -> str:
    hours = "\n".join(info.hours)
    return f"Dirección: {info.address}\nHorario de atención:\n{hours}"


def prices_text(info: ClinicInfo) -> str:
    price_lines = "\n".join(f"{price.name}: ${price.price:.2f}" for price in info.prices)
    payment_methods = ", ".join(info.payment_methods)
    return f"{price_lines}\n\nFormas de pago: {payment_methods}\n\n{PRICES_NOTE}"
