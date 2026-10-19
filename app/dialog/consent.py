from app.dialog.dependencies import Backend
from app.dialog.menu import show_menu
from app.dialog.models import ButtonAction, ButtonsMessage, Conversation, OutgoingMessage, Step, TextMessage
from app.dialog.store import load_clinic_info
from app.messages.texts import (
    CONSENT_NO_TITLE,
    CONSENT_NOTICE,
    CONSENT_YES_TITLE,
    consent_refused_text,
)

CONSENT_YES_ID = "consent:yes"
CONSENT_NO_ID = "consent:no"


def build_notice(conversation: Conversation) -> list[OutgoingMessage]:
    conversation.step = Step.CONSENT
    return [
        ButtonsMessage(
            text=CONSENT_NOTICE,
            buttons=[
                ButtonAction(id=CONSENT_YES_ID, title=CONSENT_YES_TITLE),
                ButtonAction(id=CONSENT_NO_ID, title=CONSENT_NO_TITLE),
            ],
        )
    ]


async def is_accepted(conversation: Conversation, backend: Backend) -> bool:
    """Checks consent with the backend until it is accepted, then remembers it for this conversation."""
    if not conversation.consent_accepted:
        status = await backend.get_consent(conversation.phone)
        conversation.consent_accepted = status.accepted
    return conversation.consent_accepted


async def answer_consent(reply_id: str, conversation: Conversation, backend: Backend) -> list[OutgoingMessage]:
    if reply_id == CONSENT_NO_ID:
        info = await load_clinic_info(backend)
        reception_whatsapp = info.reception_whatsapp if info is not None else ""
        return [TextMessage(text=consent_refused_text(reception_whatsapp))]
    await backend.accept_consent(conversation.phone)
    conversation.consent_accepted = True
    return await show_menu(conversation)
