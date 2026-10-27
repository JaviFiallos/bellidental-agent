"""Patient-facing text constants in Spanish."""

from app.backend.models import ClinicInfo, PublicPrice

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
CLINIC_TAGLINE = "Creamos bellas sonrisas"


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


BOOK_NO_PROFESSIONALS_TEXT = "Por ahora no hay profesionales disponibles para esa especialidad."


def _local_phone(e164: str) -> str:
    if e164.startswith("593") and len(e164) == 12:
        national = "0" + e164[3:]
        return f"{national[:3]} {national[3:6]} {national[6:]}"
    return e164


def handoff_text(info: ClinicInfo) -> str:
    hours = "\n".join(info.hours)
    contact_lines = []
    if info.address:
        contact_lines.append(f"📍 {info.address}")
    if info.reception_whatsapp:
        contact_lines.append(f"📞 {_local_phone(info.reception_whatsapp)}")
    contact_lines.append(f"🦷 {CLINIC_TAGLINE}")
    contact = "\n".join(contact_lines)
    closing = "Para volver al asistente, escriba *menu*."
    if info.reception_whatsapp:
        closing = f"Escriba a recepción: {_wa_link(info.reception_whatsapp)}\n{closing}"
    return (
        f"Le atenderá recepción en el horario de atención:\n{hours}\n\n"
        f"{contact}\n\n"
        f"{closing}"
    )


def hours_text(info: ClinicInfo) -> str:
    hours = "\n".join(info.hours)
    return f"Dirección: {info.address}\nHorario de atención:\n{hours}"


def prices_text(info: ClinicInfo) -> str:
    price_lines = "\n".join(f"{price.name}: ${price.price:.2f}" for price in info.prices)
    payment_methods = ", ".join(info.payment_methods)
    return f"{price_lines}\n\nFormas de pago: {payment_methods}\n\n{PRICES_NOTE}"

FIRST_APPOINTMENT_TEXT = "Para su primera cita, recepción le registrará."
IDENTIFY_ASK_ID_TEXT = "Escriba la cédula del paciente."
IDENTIFY_ID_RETRY_TEXT = "No encontramos esa cédula. Inténtelo de nuevo."
IDENTIFY_YES_TITLE = "Sí"
IDENTIFY_NO_TITLE = "No"

LIST_BUTTON_TEXT = "Elegir"
BOOK_SPECIALTY_TEXT = "¿Para qué especialidad?"
BOOK_PROFESSIONAL_TEXT = "¿Con qué profesional?"
BOOK_DAY_TEXT = "¿Qué día le viene bien?"
BOOK_SLOT_TEXT = "¿A qué hora?"
BOOK_FIRST_AVAILABLE_TITLE = "Primero disponible"
BOOK_NO_DAYS_TEXT = "No hay horarios libres en los próximos 14 días."
BOOK_NO_SLOTS_TEXT = "No hay horas libres ese día. Elija otro día."
BOOK_OVERLAP_TEXT = "Esa hora acaba de ocuparse. Elija otra hora."
BOOK_LIMIT_TEXT = "Ya tiene una cita próxima en esta especialidad; para otra, recepción le ayuda."
BOOK_CONFIRM_TITLE = "Confirmar"
BOOK_CHANGE_TITLE = "Cambiar hora"
BOOK_CANCEL_TITLE = "Cancelar"


APPOINTMENTS_LIST_TEXT = "Estas son sus citas próximas. Elija una."
NO_APPOINTMENTS_TEXT = "No tiene citas próximas."
APPOINTMENTS_BOOK_TITLE = "Agendar"
APPOINTMENTS_HOME_TITLE = "Menú"
RESCHEDULE_TITLE = "Reprogramar"
APPOINTMENT_CANCEL_TITLE = "Cancelar cita"
CANCEL_YES_TITLE = "Sí, cancelar"
CANCEL_NO_TITLE = "No"
APPOINTMENT_CANCELLED_TEXT = "Su cita fue cancelada."
APPOINTMENT_CONFIRMED_TEXT = "Gracias, su cita queda confirmada."
REMINDER_CONFIRMED_TEXT = "¡Gracias! Su cita queda confirmada."
REMINDER_TOO_LATE_TEXT = "Faltan menos de 2 horas para su cita; recepción le ayuda."
APPOINTMENT_TOO_LATE_TEXT = "Faltan menos de 2 horas para su cita; para cambios, recepción le ayuda."


def cancel_ask_text(when: str) -> str:
    return f"¿Seguro que desea cancelar la cita del {when}?"


def reschedule_summary_text(old_when: str, new_when: str) -> str:
    return f"De {old_when} a {new_when}"


def reschedule_success_text(when: str) -> str:
    return f"Su cita quedó para {when}."


def identify_confirm_text(patient_name: str) -> str:
    return f"¿La cita es para {patient_name}?"


def booking_summary_text(specialty_name: str, when: str, professional_name: str, patient_name: str) -> str:
    return f"{specialty_name} · {when} · {professional_name} · para {patient_name}"


def booking_success_text(when: str) -> str:
    return f"Listo, su cita quedó agendada para {when}. Le enviaremos un recordatorio el día anterior."


def fit_length(text: str, limit: int) -> str:
    """Trims text to at most `limit` characters, ending with an ellipsis when it is cut (WhatsApp list limits)."""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


URGENT_EMERGENCY_TEXT = (
    "Si tiene hinchazón que le dificulte respirar o tragar, fiebre alta o un sangrado que no se detiene, "
    "acuda a emergencias o llame al 911."
)
URGENT_SLOTS_TEXT = "Estos son los primeros huecos de urgencia. Elija uno."
URGENT_SPECIALTY_LABEL = "Urgencia"
OFF_TOPIC_TEXT = "Solo puedo ayudarle con citas e información de Bellidental."


def single_price_text(price: PublicPrice) -> str:
    return f"{price.name}: ${price.price:.2f}\n\n{PRICES_NOTE}"


def urgent_after_hours_text(phone: str) -> str:
    return f"Fuera de horario puede llamar a la doctora: {phone}"


def urgent_no_slots_text(phone: str) -> str:
    base = "No hay huecos de urgencia hoy ni mañana."
    if not phone:
        return base
    return f"{base} Puede llamar a la doctora: {phone}"


def urgent_slot_title(is_today: bool, time_text: str) -> str:
    day = "Hoy" if is_today else "Mañana"
    return f"{day} {time_text}"


def payment_text(info: ClinicInfo) -> str:
    methods = ", ".join(info.payment_methods)
    return (
        "Por WhatsApp no recibimos pagos. Puede pagar en la clínica "
        f"({methods}); recepción le indica cómo."
    )
