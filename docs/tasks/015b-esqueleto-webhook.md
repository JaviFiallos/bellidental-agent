# 015b — Esqueleto del agente y webhook de WhatsApp

## Objetivo
Arrancar el repo del agente.
- Una app FastAPI recibe el webhook de WhatsApp Cloud API, verifica que viene de Meta, convierte cada mensaje en un
  `IncomingMessage` y lo procesa en segundo plano.
- Envía las respuestas por Graph API.
- Incluye el cliente del backend (endpoints de la 015a) y el almacén de conversaciones en memoria.
- La conversación real llega en la 015c: por ahora el router responde un texto fijo de bienvenida.

Contexto: `CLAUDE.md`, `docs/BACKEND-API.md` §015a. El backend Java ya expone esos endpoints.

## Archivos a tocar
```
pyproject.toml          proyecto "bellidental-agent", Python >=3.12; deps y extra [dev] de clean-code/SKILL.md;
                        [tool.pytest.ini_options] asyncio_mode = "auto"
.env.example            todas las variables de config.py, sin valores reales
.gitignore              .venv/, __pycache__/, .env, .pytest_cache/
Dockerfile              python:3.13-slim, usuario no root, uvicorn app.main:app --host 0.0.0.0 --port 8000
README.md               instalar, correr (uvicorn --reload), túnel (cloudflared tunnel --url http://localhost:8000),
                        variables
app/
  __init__.py
  main.py               create_app(dependencies) + app = create_app(dependencias reales)
  config.py             Settings (ver criterio 7)
  whatsapp/
    signature.py        is_valid_signature(raw_body: bytes, header: str | None, app_secret: str) -> bool
    webhook.py          parse_webhook(payload: dict) -> list[IncomingMessage]
    client.py           WhatsAppClient.send(phone, message: OutgoingMessage) -> str (wamid)
  backend/
    models.py           ConsentStatus, ClinicInfo, PublicPrice, BotPatient
    client.py           BackendClient (endpoints de 015a) + BackendError(status, code)
  dialog/
    models.py           IncomingMessage, OutgoingMessage (TextMessage, ButtonsMessage, ListMessage), Step,
                        Conversation
    dependencies.py     Protocol Backend (métodos de BackendClient) y Protocol Sender (send)
    store.py            ConversationStore (TTL) y ProcessedMessages (deduplicación)
    router.py           async handle(incoming, conversation, backend) -> list[OutgoingMessage]; texto fijo
  messages/
    texts.py            WELCOME_PLACEHOLDER
tests/
  fakes.py              FakeBackend, FakeSender (guarda lo enviado)
  test_webhook.py
```

## Criterios de aceptación
1. **Verificación del webhook**: `GET /webhook?hub.mode=subscribe&hub.verify_token=…&hub.challenge=…` → `200` con el
   `challenge` en texto plano si el token coincide con `WA_VERIFY_TOKEN`; si no → `403`.
2. **Firma**:
   - `POST /webhook` lee el cuerpo crudo y valida `X-Hub-Signature-256: sha256=<hex>`, que es HMAC-SHA256 del
     cuerpo con `WA_APP_SECRET`, con `hmac.compare_digest`.
   - Firma ausente o inválida → `401` y no se procesa nada.
   - Firma válida → `200` inmediato. El procesamiento va en `BackgroundTasks`, porque Meta reintenta si tarda.
3. **Parser** (`parse_webhook`). Recorre `entry[].changes[].value.messages[]` e ignora `statuses`. Cada mensaje →
   `IncomingMessage(phone=from, message_id=id, kind, text, reply_id, context_message_id=context.id)`:
   - `text` → `kind="text"`, `text=text.body`;
   - `interactive.button_reply` → `kind="button"`, `reply_id=id`;
   - `interactive.list_reply` → `kind="list"`, `reply_id=id`;
   - `button` (botón de plantilla, se usa en la 017b) → `kind="template_button"`, `reply_id=button.payload`;
   - cualquier otro tipo (audio, imagen, ubicación…) → `kind="unsupported"`.
4. **Procesamiento**:
   - Los `message_id` ya vistos se ignoran (guardar los últimos 1000).
   - Un `asyncio.Lock` por teléfono procesa en orden los mensajes del mismo paciente.
   - Por cada mensaje: `store.get(phone)` → `router.handle(...)` → `sender.send` de cada `OutgoingMessage` →
     `store.save(conversation)`.
   - Una excepción se registra en el log (teléfono enmascarado, sin texto) y no tumba la app.
5. **Envío** (`WhatsAppClient`): `POST https://graph.facebook.com/{WA_GRAPH_VERSION}/{WA_PHONE_NUMBER_ID}/messages`
   con `Authorization: Bearer {WA_ACCESS_TOKEN}`. Formatos:
   - `TextMessage` → `type=text`;
   - `ButtonsMessage` → `interactive.type=button`, de 1 a 3 botones con título ≤ 20 caracteres;
   - `ListMessage` → `interactive.type=list`:
     - texto del botón ≤ 20 caracteres;
     - máximo 10 filas en total;
     - título de fila ≤ 24 caracteres;
     - descripción ≤ 72 caracteres.

   `dialog/models.py` valida esos límites con pydantic, para que un texto largo falle en los tests y no en Meta.
   `send` devuelve `messages[0].id`.
6. **Backend** (`BackendClient`, httpx asíncrono, `X-Bot-Key`, timeout 10 s):
   - `get_consent`, `accept_consent`, `get_info`, `get_patients`, `verify_patient`, según `docs/BACKEND-API.md`.
   - Desenvuelve `data`.
   - Ante 4xx/5xx lanza `BackendError(status, code)`.
7. **Configuración** (`config.py`, pydantic-settings, lee `.env`):
   - WhatsApp: `WA_VERIFY_TOKEN`, `WA_APP_SECRET`, `WA_ACCESS_TOKEN`, `WA_PHONE_NUMBER_ID`,
     `WA_GRAPH_VERSION` (por defecto `v23.0`);
   - backend: `BACKEND_URL` (por defecto `http://localhost:8080`), `BOT_API_KEY`;
   - otros: `CLINIC_ZONE` (por defecto `America/Guayaquil`), `CONVERSATION_TTL_MINUTES` (por defecto 30).
8. **Conversación** (`Conversation`): `phone`, `step: Step` (por ahora `IDLE`), `consent_accepted: bool`,
   `patient_id`, `selection: dict`, `history: list[str]` (últimos 6 textos), `handoff_until`, `unknown_count`,
   `updated_at`. Caduca a los `CONVERSATION_TTL_MINUTES` sin mensajes.
9. **Health**: `GET /health` → `{"status": "ok"}`.
10. `create_app` recibe las dependencias (`sender`, `backend`, `store`, `settings`) para que los tests usen fakes.

## Tests requeridos
`tests/test_webhook.py`, 4 casos, con `TestClient` y fakes:
1. `test_webhook_valid_signature_replies_to_text`: un POST firmado con un mensaje de texto → 200 y `FakeSender`
   recibió el texto de bienvenida para ese teléfono.
2. `test_webhook_invalid_signature_returns_401_and_sends_nothing`
3. `test_webhook_duplicate_message_id_processed_once`
4. `test_parse_webhook_button_list_and_template_replies_set_reply_id`: tres mensajes, uno por tipo, con su `reply_id`
   y `context_message_id`.

## Prueba manual
1. Correr con el `.env` del número de prueba.
2. Abrir el túnel y configurar el webhook en Meta (`WHATSAPP-SETUP.md` paso 7).
3. Enviar "hola" desde tu número registrado: llega el texto de bienvenida.

## Resultado

## Revisión
