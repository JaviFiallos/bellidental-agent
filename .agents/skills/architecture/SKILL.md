---
name: architecture
description: Estructura del agente Python de Bellidental. Usar al crear o mover archivos.
---
Principio: **la IA interpreta, el código decide**. El agente nunca accede a la BD; toda escritura la hace el backend
Java por `/api/v1/bot/*`, y solo después de que el paciente pulse *Confirmar*.

```
app/
  main.py        FastAPI: rutas /webhook y /health, arranque (lifespan). Sin lógica de conversación.
  config.py      Settings (pydantic-settings) desde variables de entorno. Único lugar que lee el entorno.
  whatsapp/      Meta: verificar firma, convertir el JSON del webhook en IncomingMessage, enviar OutgoingMessage
                 por Graph API. Única carpeta que conoce el formato de Meta.
  backend/       cliente httpx de /api/v1/bot/* (X-Bot-Key) y sus modelos pydantic. Única carpeta que conoce la API.
  dialog/        conversación: models.py (IncomingMessage, OutgoingMessage, Conversation, Step), store.py
                 (memoria con TTL), router.py (punto de entrada), un módulo por flujo (consent.py, menu.py,
                 booking.py…).
  nlu/           interfaz Classifier + adaptadores por proveedor. Solo devuelve intención y datos.
  messages/      textos al paciente (español) y formato de fechas. Ningún texto al paciente fuera de aquí.
  reminders/     job periódico de recordatorios.
tests/           fakes.py (backend, WhatsApp y clasificador falsos) + un archivo por tarea
```

Reglas:
- `dialog/` es lógica pura y asíncrona: recibe `IncomingMessage` + `Conversation` y devuelve
  `list[OutgoingMessage]`. No importa `httpx`, `fastapi` ni nada de `whatsapp/`. Recibe el backend y el clasificador
  como dependencias (`typing.Protocol`), para probarla con fakes.
- `whatsapp/` traduce `OutgoingMessage` (texto, botones, lista, plantilla) al JSON de Graph API; `dialog/` no
  conoce ese JSON.
- `nlu/` nunca llama al backend ni escribe; su salida pasa siempre por la máquina de estados.
- Sin más carpetas ni capas (`services/`, `utils/`, `repositories/`). Una clase por archivo no es obligatoria.
- Estado en memoria, una sola instancia (sin Redis ni BD propia).
