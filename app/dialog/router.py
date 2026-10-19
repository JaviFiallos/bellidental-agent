from app.dialog.dependencies import Backend
from app.dialog.models import Conversation, IncomingMessage, OutgoingMessage, TextMessage
from app.messages.texts import WELCOME_PLACEHOLDER


async def handle(
    incoming: IncomingMessage,
    conversation: Conversation,
    backend: Backend,
) -> list[OutgoingMessage]:
    """Handles an incoming message, updates conversation state, and returns outgoing messages."""
    if incoming.text:
        conversation.history.append(incoming.text)
        conversation.history = conversation.history[-6:]

    return [TextMessage(text=WELCOME_PLACEHOLDER)]
