# 016f — Aceptar los ids numéricos que envía el backend

## Objetivo
Corregir el fallo visto en producción con el número de prueba de Meta: al elegir **Agendar cita** y confirmar el
paciente, el agente registra `Error processing message ... ValidationError` y no responde.
- Causa (reproducida): el backend envía `specialtyId` como **número** (`Long` en Java: `{"specialtyId": 1, ...}`) y
  los modelos de `app/backend/models.py` lo declaran `str`. Pydantic 2 no convierte `int` → `str` por defecto.
  Los tests no lo vieron porque `tests/fakes.py` construye los modelos con ids de texto (`"spec-1"`).
- Mismo caso en `Appointment.specialty_id` y `UrgentSlots.specialty_id` (ver `docs/BACKEND-API.md`).
- **Segundo fallo, consecuencia del primero:** tras el error la conversación queda trabada. `ConversationStore.get`
  devuelve el mismo objeto que el router muta antes de fallar; `save` no se llama, pero el objeto ya quedó en un paso
  a medias (sin `specialty_id` en `selection`), así que cada mensaje siguiente da `KeyError` y el paciente no recibe
  nada hasta que pasan 30 min (TTL) o se reinicia el contenedor.
- El agente sigue tratando los ids como texto opaco (se reenvían tal cual en query params y en el cuerpo de
  `POST /appointments`; Spring/Jackson acepta `"1"` para un `Long`). No se cambian tipos ni firmas.

## Archivos a tocar
```
app/
  main.py                en el except de process_payload: descartar la conversación y avisar al paciente
  backend/
    models.py            ConfigDict(..., coerce_numbers_to_str=True) en los modelos que reciben ids del backend
  dialog/
    store.py             ConversationStore.discard(phone)
tests/
  fakes.py               los ids de especialidad se crean como el backend los envía: números (1, 99), vía
                         Model.model_validate({...}) con las claves camelCase del JSON real
  test_webhook.py        (o el archivo donde ya se prueba la ruta /webhook) 1 test nuevo
```

## Criterios de aceptación
1. `Specialty.model_validate({"specialtyId": 1, "name": "Ortodoncia", "durationMinutes": 30}).specialty_id == "1"`.
2. Lo mismo para `Appointment` y `UrgentSlots` con `specialtyId` numérico.
3. La opción va en el `model_config` de cada modelo afectado (sin validadores propios ni cambios de tipo).
4. `tests/fakes.py` usa ids numéricos para las especialidades, de modo que la suite existente recorre el flujo de
   agendar con la misma forma de datos que el backend real.
5. Ante cualquier excepción al procesar un mensaje, además del log actual (teléfono enmascarado, solo el tipo de
   excepción): `app_store.discard(phone)` y se envía al paciente `technical_problem_text(...)` con el WhatsApp de
   recepción de la info de la clínica en caché (`peek_clinic_info`), o `""` si no hay caché. Si ese envío también
   falla, solo se registra en el log (no se relanza). El siguiente mensaje del paciente empieza una conversación
   nueva (el consentimiento sigue guardado en el backend).
6. Sin cambios en los flujos de `dialog/` (solo `store.py`), en `client.py` ni en los textos.

## Tests requeridos
1. `test_webhook_handler_error_discards_conversation_and_notifies`: con un fake de backend que lanza en
   `get_specialties`, un mensaje que entra a agendar → el paciente recibe el texto de problema técnico; el
   siguiente mensaje (`hola`) recibe el menú, no un error.

La suite existente, con los fakes de ids numéricos, cubre el flujo de agendar. Reportar la línea de totales de
`.venv/bin/pytest -q`.

## Prueba manual
1. Tras desplegar (push a `main` → CI → VPS), desde el WhatsApp de prueba: `hola` → menú → **Agendar cita** →
   **Sí** (paciente) → debe salir "¿Para qué especialidad?" con la lista.
2. Completar profesional → día → hora → **Confirmar** → "Listo, su cita quedó agendada…" y la cita en Recepción.
3. `docker compose logs agent`: sin `ValidationError`.

## Resultado
- **Archivos modificados:**
  - `app/backend/models.py`: Se añadió `coerce_numbers_to_str=True` en `model_config` para los modelos que reciben IDs del backend (`BotPatient`, `Specialty`, `Professional`, `Slot`, `Appointment`, `UrgentSlots`, `DueReminder`, `ReminderResponse`), permitiendo que Pydantic 2 coaccione números enteros (`Long` en backend) a `str`.
  - `app/dialog/store.py`: Se implementó el método `ConversationStore.discard(phone)` para eliminar de memoria la conversación asociada a un número.
  - `app/main.py`: En el bloque `except` de `process_payload`, se añadió el descarte de la conversación mediante `app_store.discard(incoming.phone)` y el envío del mensaje de problema técnico al paciente (`technical_problem_text(...)` usando el WhatsApp de recepción obtenido de `peek_clinic_info` si está en caché, o `""`), capturando y logueando cualquier fallo en el reenvío sin relanzarlo.
  - `tests/fakes.py`: Se actualizaron las especialidades, citas y slots urgentes para instanciarse vía `model_validate` con IDs numéricos (`specialtyId: 1`, `99`), y se añadió soporte para simular errores en `get_specialties` (`specialties_error`).
  - `tests/test_webhook.py`: Se implementó el test `test_webhook_handler_error_discards_conversation_and_notifies`. Siguiendo las correcciones de revisión: se precarga la caché mediante `asyncio.run(load_clinic_info(backend))` sin acceder a internals privados, se comprueba explícitamente el descarte con `assert store.get(phone).patient_id is None` tras el error, y se eliminó la línea en blanco extra al final del archivo.

- **Totales de pytest:**
```
24 passed, 1 warning in 2.76s
```

- **Problemas encontrados y supuestos tomados:**
  - Ninguno. Las correcciones solicitadas en la revisión fueron aplicadas y la suite pasó limpiamente.

## Revisión

Estado: CORRECCIONES

Código de `app/` correcto (criterios 1–6 cumplidos; `24 passed, 1 warning`). Solo el test nuevo:
1. No tocar internals privados (`_clinic_info_caches`, `cache._info`, `cache._fetched_at`): precargar la caché con la
   función pública, `asyncio.run(load_clinic_info(backend))`, y quitar los imports de `ClinicInfoCache`,
   `_clinic_info_caches`, `datetime` y `timezone`.
2. El test no demuestra el descarte: `hola` devuelve el menú aunque la conversación no se descarte. Tras el primer
   mensaje, añadir `assert store.get(phone).patient_id is None` (la conversación sembrada tenía `"pat-1"`).
3. `tests/test_webhook.py` termina con una línea en blanco de más; dejar un solo `\n` final.

Estado: APROBADO

Correcciones 1–3 aplicadas. Sin la llamada a `discard` el test nuevo falla (comprobado), así que cubre el descarte.
`.venv/bin/pytest -q`: `24 passed, 1 warning`.
