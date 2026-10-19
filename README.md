# Agente WhatsApp Bellidental

Agente conversacional en Python (FastAPI) para Bellidental.

## Instalación

Requiere Python ≥ 3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Variables de entorno

Copiar el archivo de plantilla y configurar los valores necesarios:

```bash
cp .env.example .env
```

Variables disponibles:
- `WA_VERIFY_TOKEN`: Token de verificación configurado en el panel de Meta.
- `WA_APP_SECRET`: Secreto de la aplicación en Meta para verificar HMAC-SHA256 del webhook.
- `WA_ACCESS_TOKEN`: Token de acceso del sistema para la WhatsApp Graph API.
- `WA_PHONE_NUMBER_ID`: Identificador del número de teléfono en WhatsApp Cloud API.
- `WA_GRAPH_VERSION`: Versión de Graph API (por defecto `v23.0`).
- `BACKEND_URL`: URL base del backend Java (por defecto `http://localhost:8080`).
- `BOT_API_KEY`: Clave de autenticación para endpoints internos `/api/v1/bot/*`.
- `CLINIC_ZONE`: Zona horaria de la clínica (por defecto `America/Guayaquil`).
- `CONVERSATION_TTL_MINUTES`: Minutos de inactividad antes de reiniciar conversación (por defecto `30`).

## Ejecución

Iniciar el servidor de desarrollo:

```bash
uvicorn app.main:app --reload
```

## Túnel para desarrollo local

Para exponer el webhook a Meta en desarrollo local:

```bash
cloudflared tunnel --url http://localhost:8000
```

Configurar en Meta la URL del webhook: `https://<dominio-del-tunel>/webhook`.

## Tests

```bash
.venv/bin/pytest -q
```
