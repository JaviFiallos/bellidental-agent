import asyncio
import logging

from app.backend.models import DueReminder
from app.config import Settings
from app.dialog.dependencies import Backend, Sender
from app.dialog.models import TemplateMessage
from app.dialog.reminder_reply import CANCEL_PAYLOAD, CONFIRM_PAYLOAD, RESCHEDULE_PAYLOAD
from app.messages.dates import format_long_date, format_time

logger = logging.getLogger(__name__)

SEND_ATTEMPTS = 2


def build_reminder_template(reminder: DueReminder, settings: Settings) -> TemplateMessage:
    return TemplateMessage(
        name=settings.wa_reminder_template,
        language=settings.wa_template_language,
        body_parameters=[
            reminder.patient_first_name,
            format_long_date(reminder.start_at),
            format_time(reminder.start_at),
            reminder.professional_name,
        ],
        button_payloads=[CONFIRM_PAYLOAD, CANCEL_PAYLOAD, RESCHEDULE_PAYLOAD],
    )


async def run_once(backend: Backend, sender: Sender, settings: Settings) -> None:
    """Sends every due reminder. A failing reminder never stops the others."""
    for reminder in await backend.get_due_reminders():
        try:
            await _send_reminder(reminder, backend, sender, settings)
        except Exception as exc:
            logger.error("Reminder %s could not be processed: %s", reminder.reminder_id, type(exc).__name__)


async def run_forever(backend: Backend, sender: Sender, settings: Settings) -> None:
    """Runs run_once every REMINDER_INTERVAL_SECONDS. Errors are logged and the loop goes on."""
    while True:
        try:
            await run_once(backend, sender, settings)
        except Exception as exc:
            logger.error("Reminder cycle failed: %s", type(exc).__name__)
        await asyncio.sleep(settings.reminder_interval_seconds)


async def _send_reminder(
    reminder: DueReminder,
    backend: Backend,
    sender: Sender,
    settings: Settings,
) -> None:
    message = build_reminder_template(reminder, settings)
    for attempt in range(1, SEND_ATTEMPTS + 1):
        try:
            wa_message_id = await sender.send(reminder.phone, message)
        except Exception as exc:
            logger.warning(
                "Reminder %s send attempt %d failed: %s", reminder.reminder_id, attempt, type(exc).__name__
            )
            continue
        await backend.mark_reminder_sent(reminder.reminder_id, wa_message_id)
        return
    await backend.mark_reminder_failed(reminder.reminder_id)
