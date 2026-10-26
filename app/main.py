import asyncio
from contextlib import asynccontextmanager, suppress
import json
import logging
from typing import Any
import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse

from app.backend.client import BackendClient
from app.config import Settings
from app.dialog import router
from app.dialog.dependencies import Backend, Classifier, Sender
from app.dialog.models import TextMessage
from app.dialog.store import ConversationStore, ProcessedMessages, peek_clinic_info
from app.messages.texts import technical_problem_text
from app.nlu.classifier import DisabledClassifier
from app.nlu.openai_compatible import OpenAICompatibleClassifier
from app.reminders import job as reminder_job
from app.whatsapp.client import WhatsAppClient
from app.whatsapp.signature import is_valid_signature
from app.whatsapp.webhook import parse_webhook

logger = logging.getLogger(__name__)


def mask_phone(phone: str) -> str:
    """Masks phone number for privacy compliance (LOPDP/RNF03)."""
    if len(phone) >= 8:
        return f"{phone[:4]}****{phone[-4:]}"
    return "****"


def build_classifier(settings: Settings, client: httpx.AsyncClient | None) -> Classifier:
    """Uses the LLM only when LLM_API_KEY is set; otherwise the bot runs with the menu alone."""
    if not settings.llm_api_key:
        return DisabledClassifier()
    return OpenAICompatibleClassifier(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout=settings.llm_timeout_seconds,
        client=client,
    )


def create_app(
    sender: Sender | None = None,
    backend: Backend | None = None,
    store: ConversationStore | None = None,
    processed_messages: ProcessedMessages | None = None,
    settings: Settings | None = None,
    classifier: Classifier | None = None,
) -> FastAPI:
    """Creates and configures the FastAPI application with injectable dependencies."""
    app_settings = settings or Settings()
    app_store = store or ConversationStore(ttl_minutes=app_settings.conversation_ttl_minutes)
    app_processed_messages = processed_messages or ProcessedMessages()

    shared_http_client: httpx.AsyncClient | None = None
    if sender is None or backend is None:
        shared_http_client = httpx.AsyncClient(timeout=10.0)

    app_backend = backend or BackendClient(
        base_url=app_settings.backend_url,
        api_key=app_settings.bot_api_key,
        client=shared_http_client,
        timeout=10.0,
    )
    app_sender = sender or WhatsAppClient(
        access_token=app_settings.wa_access_token,
        phone_number_id=app_settings.wa_phone_number_id,
        graph_version=app_settings.wa_graph_version,
        client=shared_http_client,
        timeout=10.0,
    )

    llm_http_client: httpx.AsyncClient | None = None
    if app_settings.llm_api_key:
        llm_http_client = httpx.AsyncClient(timeout=app_settings.llm_timeout_seconds)
    app_classifier = classifier or build_classifier(app_settings, llm_http_client)

    phone_locks: dict[str, asyncio.Lock] = {}

    def get_lock(phone: str) -> asyncio.Lock:
        if phone not in phone_locks:
            phone_locks[phone] = asyncio.Lock()
        return phone_locks[phone]

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        reminder_task: asyncio.Task[None] | None = None
        if app_settings.reminders_enabled:
            reminder_task = asyncio.create_task(
                reminder_job.run_forever(app_backend, app_sender, app_settings)
            )
        yield
        if reminder_task is not None:
            reminder_task.cancel()
            with suppress(asyncio.CancelledError):
                await reminder_task
        if shared_http_client is not None:
            await shared_http_client.aclose()
        if llm_http_client is not None:
            await llm_http_client.aclose()

    app = FastAPI(title="Bellidental WhatsApp Agent", lifespan=lifespan)

    async def process_payload(payload: dict[str, Any]) -> None:
        messages = parse_webhook(payload)
        for incoming in messages:
            if app_processed_messages.has(incoming.message_id):
                continue
            app_processed_messages.add(incoming.message_id)

            lock = get_lock(incoming.phone)
            async with lock:
                try:
                    conversation = app_store.get(incoming.phone)
                    outgoing_messages = await router.handle(
                        incoming, conversation, app_backend, app_classifier
                    )
                    for outgoing in outgoing_messages:
                        await app_sender.send(incoming.phone, outgoing)
                    app_store.save(conversation)
                except Exception as exc:
                    masked_phone = mask_phone(incoming.phone)
                    logger.error(
                        "Error processing message for phone %s: %s",
                        masked_phone,
                        type(exc).__name__,
                    )
                    app_store.discard(incoming.phone)
                    try:
                        info = peek_clinic_info(app_backend)
                        reception_whatsapp = info.reception_whatsapp if info is not None else ""
                        await app_sender.send(
                            incoming.phone,
                            TextMessage(text=technical_problem_text(reception_whatsapp)),
                        )
                    except Exception as send_exc:
                        logger.error(
                            "Error sending technical problem message for phone %s: %s",
                            masked_phone,
                            type(send_exc).__name__,
                        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/webhook")
    async def verify_webhook(
        mode: str | None = Query(None, alias="hub.mode"),
        token: str | None = Query(None, alias="hub.verify_token"),
        challenge: str | None = Query(None, alias="hub.challenge"),
    ) -> Response:
        if (
            app_settings.wa_verify_token
            and mode == "subscribe"
            and token == app_settings.wa_verify_token
        ):
            return PlainTextResponse(content=challenge or "", status_code=200)
        raise HTTPException(status_code=403, detail="Verification failed")

    @app.post("/webhook")
    async def post_webhook(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        raw_body = await request.body()
        signature_header = request.headers.get("X-Hub-Signature-256")
        if not is_valid_signature(raw_body, signature_header, app_settings.wa_app_secret):
            raise HTTPException(status_code=401, detail="Invalid signature")

        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            payload = {}

        background_tasks.add_task(process_payload, payload)
        return Response(status_code=200, content="OK")

    return app


app = create_app()
