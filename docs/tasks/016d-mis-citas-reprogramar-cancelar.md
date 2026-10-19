# 016d — Mis citas: reprogramar, cancelar y confirmar

## Objetivo
Desde *Mis citas*, el paciente ve sus citas próximas y puede reprogramarlas (RF15), cancelarlas o confirmarlas.
- Cada escritura va solo tras un botón de confirmación.
- La regla de "hasta 2 h antes" (D-10) la aplica Java; el agente reacciona al `code`.
- El inicio de la reprogramación se deja reutilizable: la 017b lo usa desde el botón del recordatorio.

Reemplaza la derivación temporal de `menu:appointments` (015c). Endpoints: `docs/BACKEND-API.md` §016a y §016b.

## Archivos a tocar
```
app/
  backend/client.py     + get_appointments, reschedule_appointment, cancel_appointment, confirm_appointment
  dialog/
    models.py           Step: + APPT_CHOOSE, APPT_ACTION, RESCHEDULE_DAY, RESCHEDULE_SLOT, RESCHEDULE_CONFIRM,
                        CANCEL_CONFIRM
    appointments.py     (nuevo) lista, acciones, cancelar, confirmar
                        + start_reschedule(conversation, appointment, backend) (pública, la usa la 017b)
    router.py           despacha los nuevos Step y prefijos
  messages/texts.py     + textos del flujo
tests/
  fakes.py              + citas y errores configurables en reschedule/cancel
  test_appointments.py  (nuevo)
```

## Criterios de aceptación
1. *Mis citas*:
   - Se identifica al paciente (`identify.py`, `then="appointments"`) y se llama a `get_appointments(phone, patientId)`.
   - 0 citas → "No tiene citas próximas." con los botones *Agendar* (`menu:book`) y *Menú*.
   - 1 o más → lista con la fecha y hora (`format_day` + hora) como título y la especialidad · profesional como
     descripción.
2. Elegida una cita → resumen y botones:
   - *Reprogramar* (`appt:reschedule`);
   - *Cancelar cita* (`appt:cancel`);
   - *Confirmar* (`appt:confirm`), solo si está `PENDING`.
3. **Reprogramar** (`start_reschedule`):
   - días de `get_available_days(specialtyId, professionalId)` de esa cita → horas (`slot_picker.py` de la 016c) →
     resumen "De martes 21 de octubre, 10:30 a jueves 23 de octubre, 16:00" con *Confirmar* / *Cancelar*;
   - *Confirmar* → `reschedule_appointment(id, phone, startAt)` → "Su cita quedó para …".
4. **Cancelar**: "¿Seguro que desea cancelar la cita del …?" con *Sí, cancelar* / *No*. Si responde que sí →
   `cancel_appointment` → "Su cita fue cancelada." y el menú.
5. **Confirmar** → `confirm_appointment` → "Gracias, su cita queda confirmada."
6. **Errores**:
   - `BOT_TOO_LATE` → "Faltan menos de 2 horas para su cita; para cambios, recepción le ayuda" y derivar;
   - `APPOINTMENT_OVERLAP` → se ofrecen de nuevo las horas del día;
   - `404` u otro error → derivar.
7. Las respuestas fuera de lugar y "menú" se tratan igual que en la 016c. Al terminar: `step=IDLE` y `selection`
   vacía.

## Tests requeridos
`tests/test_appointments.py`, 3 casos, con `FakeBackend`:
1. `test_reschedule_full_path_calls_reschedule_with_new_slot`
2. `test_cancel_too_late_explains_and_derives`
3. `test_my_appointments_none_offers_booking`

## Prueba manual
Con una cita agendada por el bot:
1. *Mis citas* → reprogramar a otra hora: en el frontend, la original queda `RESCHEDULED` y aparece la nueva.
2. Cancelar la nueva: queda `CANCELLED`.

## Resultado
Correcciones de la Revisión (ronda 1), las 2 aplicadas:
1. `app/backend/client.py` (`_unwrap`): si la respuesta 2xx no tiene cuerpo (`response.content` vacío), devuelve
   `None` en vez de llamar a `response.json()`. Así `cancel` y `confirm` no fallan tras haber escrito.
2. Límites de fila definidos una vez en `app/dialog/models.py` (`MAX_ROWS = 10`, `MAX_ROW_TITLE = 24`,
   `MAX_ROW_DESCRIPTION = 72`), usados también en los `Field` de `ListRow`. Se borran las copias de `booking.py`,
   `slot_picker.py` y `appointments.py`, que ahora importan de ahí. `MAX_PROFESSIONAL_ROWS = 9` sigue local a
   `booking.py`.

Archivos tocados en esta ronda: `app/backend/client.py`, `app/dialog/models.py`, `app/dialog/booking.py`,
`app/dialog/slot_picker.py`, `app/dialog/appointments.py`.

Ronda 0 (ya revisada): `app/backend/client.py`, `app/backend/models.py` (sin cambios), `app/dialog/dependencies.py`,
`app/dialog/models.py`, `app/dialog/router.py`, `app/dialog/menu.py`, `app/dialog/appointments.py` (nuevo),
`app/messages/texts.py`, `app/messages/dates.py` (`format_day_time`), `tests/fakes.py`,
`tests/test_appointments.py` (nuevo, 3 tests).

- **Totales pytest**:
  ```
  15 passed, 1 warning in 0.55s
  ```
- Sin commit.

## Revisión
Estado: APROBADO

Ronda 1 (CORRECCIONES: 2xx sin cuerpo → `None`, límites de fila centralizados en `dialog/models.py`): aplicadas y
verificadas. Pendiente para la prueba manual: confirmar con el backend real la respuesta de `cancel`/`confirm`.
