# 017b — Envío de recordatorios y respuesta a sus botones

## Objetivo
Cada 5 minutos el agente pide al backend los recordatorios vencidos (RF13).
- Envía la plantilla aprobada `recordatorio_cita` con los botones *Confirmar / Cancelar / Reprogramar* y reporta el
  resultado.
- Cuando el paciente pulsa un botón, el agente informa la respuesta al backend (que siempre la guarda, D-2) y actúa
  según el `outcome`.

Java decide qué se envía (solo citas activas y pacientes con consentimiento). Endpoints: `docs/BACKEND-API.md` §017a.

## Archivos a tocar
```
app/
  config.py             + WA_REMINDER_TEMPLATE (recordatorio_cita), WA_TEMPLATE_LANGUAGE (es),
                          REMINDER_INTERVAL_SECONDS (300), REMINDERS_ENABLED (true)
  dialog/models.py      + TemplateMessage(name, language, body_parameters, button_payloads)
  whatsapp/client.py    + envío de TemplateMessage
  backend/client.py     + get_due_reminders, mark_reminder_sent, mark_reminder_failed, send_reminder_response
  reminders/
    job.py              (nuevo) run_once(backend, sender, settings) y bucle periódico
  dialog/
    reminder_reply.py   (nuevo) respuesta a los botones de la plantilla
    router.py           kind="template_button" → reminder_reply (criterio 4)
  main.py               en el lifespan, si REMINDERS_ENABLED, lanza el bucle como asyncio.Task y lo cancela al
                        apagar
  messages/texts.py     + textos de respuesta
tests/
  fakes.py              + recordatorios vencidos, fallo configurable en send, outcome configurable
  test_reminders.py     (nuevo)
```

## Criterios de aceptación
1. **Plantilla**:
   - `type=template`, `name=WA_REMINDER_TEMPLATE`, `language.code=WA_TEMPLATE_LANGUAGE`.
   - Parámetros del cuerpo, en orden: `patientFirstName`, fecha (`martes 21 de octubre`), hora (`10:30`) y
     `professionalName`.
   - Tres componentes `button` `quick_reply` con índices `0`, `1` y `2`, y payloads `reminder:confirm`,
     `reminder:cancel` y `reminder:reschedule`, en el orden de la plantilla aprobada.
2. **Job** (`run_once`):
   - Llama a `get_due_reminders()` y, por cada uno, envía la plantilla.
   - Si el envío lanza excepción, reintenta una vez.
   - Éxito → `mark_reminder_sent(id, wamid)`; segundo fallo → `mark_reminder_failed(id)`.
   - Un recordatorio que falla no detiene a los demás.
3. **Bucle**:
   - Llama a `run_once` cada `REMINDER_INTERVAL_SECONDS`.
   - Cualquier excepción se registra en el log (sin datos personales) y el bucle sigue.
   - Una sola instancia.
4. **Respuesta**:
   - `kind="template_button"` se atiende siempre, incluso con derivación activa: va en el router antes de ese
     filtro.
   - Llama a `send_reminder_response(waMessageId=context_message_id, phone, response)`, donde `reminder:confirm` →
     `CONFIRMED`, `reminder:cancel` → `CANCELLED` y `reminder:reschedule` → `RESCHEDULED`.
   - Según el `outcome`:
     - `CONFIRMED` → "¡Gracias! Su cita queda confirmada.";
     - `CANCELLED` → "Su cita fue cancelada." y el menú;
     - `RESCHEDULE_REQUESTED` → `conversation.patient_id = patientId`; se busca la cita con
       `get_appointments(phone, patientId)` y se llama a `start_reschedule(...)` (016d);
     - `TOO_LATE` → "Faltan menos de 2 horas para su cita; recepción le ayuda" y derivar;
     - `404` → menú.

## Tests requeridos
`tests/test_reminders.py`, 4 casos, con fakes:
1. `test_job_sends_template_and_marks_sent_with_wamid`
2. `test_job_send_fails_twice_marks_failed`
3. `test_reminder_confirm_button_posts_response_with_context_id_and_thanks`
4. `test_reminder_reschedule_outcome_starts_reschedule_flow`: la respuesta contiene la lista de días.

## Prueba manual
Requiere la plantilla `recordatorio_cita` aprobada en Meta (`WHATSAPP-SETUP.md` paso 8).
1. Crear una cita para pasado mañana para un paciente con tu número de prueba y con consentimiento.
2. Al día siguiente, después de las 09:00, llega el recordatorio en el siguiente ciclo del job.
3. Pulsar *Confirmar*: la cita pasa a `CONFIRMED` en el frontend.

## Resultado

**Archivos creados:** `app/dialog/reminder_reply.py`, `app/reminders/__init__.py`, `app/reminders/job.py`,
`tests/test_reminders.py`.

**Archivos modificados:** `app/config.py` (WA_REMINDER_TEMPLATE, WA_TEMPLATE_LANGUAGE, REMINDER_INTERVAL_SECONDS,
REMINDERS_ENABLED), `app/backend/models.py` (DueReminder, ReminderResponse), `app/backend/client.py` (get_due_reminders,
mark_reminder_sent, mark_reminder_failed, send_reminder_response), `app/dialog/dependencies.py` (mismos métodos en el
Protocol `Backend`), `app/dialog/models.py` (TemplateMessage), `app/whatsapp/client.py` (payload `template` con cuerpo
y 3 botones quick_reply), `app/dialog/router.py` (template_button antes del filtro de derivación), `app/messages/dates.py`
(format_long_date), `app/messages/texts.py` (REMINDER_CONFIRMED_TEXT, REMINDER_TOO_LATE_TEXT), `app/main.py` (tarea
del bucle en el lifespan, cancelada al apagar), `tests/fakes.py` (recordatorios, fallo configurable en send, outcome
configurable).

`.venv/bin/pytest -q` →
23 passed, 1 warning in 0.58s

**Supuestos y problemas:**
- La fecha de la plantilla es `miércoles 21 de octubre` (el 2026-10-21 es miércoles; el ejemplo de la tarea decía martes).
- Un `template_button` sin `context_message_id` o con payload desconocido muestra el menú (no hay wamid que reportar).
- `RESCHEDULE_REQUESTED` sin cita coincidente en `get_appointments` muestra el menú.
- `TOO_LATE` usa el texto nuevo REMINDER_TOO_LATE_TEXT ("...; recepción le ayuda.") y deriva.
- El envío reintenta una vez; un fallo de `mark_reminder_sent` también queda aislado por recordatorio (se registra).
- Log sin teléfono ni nombre: solo id del recordatorio y nombre de la excepción.
- `.env.example` no incluye las 4 variables nuevas (no estaban en "Archivos a tocar"); los valores por defecto cubren el caso.
- No se hizo commit.

## Revisión
Estado: APROBADO

Correcciones mínimas de Claude:
1. `reminder_reply.py`: una respuesta a un recordatorio borra `handoff_until`. Sin esto, con una derivación activa,
   `RESCHEDULE_REQUESTED` mostraba los días y la elección del paciente se descartaba en silencio. `TOO_LATE` vuelve
   a derivar.
2. `.env.example`: añadidas `WA_REMINDER_TEMPLATE`, `WA_TEMPLATE_LANGUAGE`, `REMINDER_INTERVAL_SECONDS` y
   `REMINDERS_ENABLED` (015b: todas las variables de `config.py`).

Aceptados: payload desconocido o sin `context` → menú; cita no encontrada → menú; `REMINDER_TOO_LATE_TEXT`.
Pendiente: prueba manual con la plantilla aprobada en Meta.
