# 033b — Horarios por especialidad (menú)

Depende de la tarea 033 del backend (`GET /bot/schedule`).

## Objetivo
Hoy *Horarios* solo muestra el horario general de la clínica. Ahora, desde el menú:
```
Horarios → lista:  Horario de atención (general) · Ortodoncia · Endodoncia · Odontología general …
  especialidad → texto con el horario de cada profesional de esa especialidad, próximos 7 días
               → botones [Ver horas libres] [Semana siguiente] [Menú]
```
- El horario es por profesional, no por especialidad: un doctor con varias especialidades aparece con el mismo
  horario en cada una (es correcto, atiende cualquiera de ellas en esas horas).
- *Semana siguiente* muestra los días 7 a 13 y ya no se ofrece más (límite de 14 días del backend).
- *Ver horas libres* entra al flujo de agendar con la especialidad ya elegida (pista `specialty`) y llega a los
  días con huecos (`/availability/days`), como ya hace el texto libre "quiero cita de ortodoncia".
- Ids **sin estado** (no hay pasos nuevos): todo lo necesario va en el id de la fila o del botón.

## Archivos a tocar
```
app/
  backend/
    models.py            Shift, ScheduleDay, ProfessionalSchedule
    client.py            get_schedule(from_day, to_day, specialty_id=None, professional_id=None)
  dialog/
    dependencies.py      Backend.get_schedule
    hours.py             nuevo: show_hours_menu, answer_hours (ids "hours:")
    menu.py              HOURS_ID → hours.show_hours_menu
    router.py            reply_id con prefijo "hours:" → hours.answer_hours
  messages/
    texts.py             títulos y texto del horario semanal
docs/BACKEND-API.md      fila de GET /schedule (033)
tests/
  fakes.py               FakeBackend.get_schedule
  test_hours.py          2 tests
```

## Criterios de aceptación
1. Cliente: `GET /api/v1/bot/schedule` con `from`, `to` (ISO) y los filtros opcionales; devuelve
   `list[ProfessionalSchedule]` (`professional_id`, `professional_name`, `days: [ScheduleDay(date, shifts:
   [Shift(start_time, end_time)])]`, alias camelCase).
2. `show_hours_menu` (menú → *Horarios* y la intención `HOURS` sin datos, que ya llama a `answer_menu(HOURS_ID)`):
   `ListMessage` con `hours:general` ("Horario de atención") y una fila `hours:spec:{specialty_id}:0` por
   especialidad de `get_specialties`, máximo 10 filas en total.
3. `answer_hours(reply_id, conversation, backend)`:
   - `hours:general` → `hours_text(info)` (el de ahora) + menú.
   - `hours:spec:{id}:{week}` (`week` 0 o 1; otro valor → 0): `get_schedule(hoy + 7·week, hoy + 7·week + 6,
     specialty_id=id)` → `[TextMessage(horario), ButtonsMessage(pregunta corta, botones)]`. El horario va en un
     `TextMessage` aparte porque el cuerpo de los botones admite solo 1024 caracteres.
     Botones: `hours:book:{id}` "Ver horas libres", `hours:spec:{id}:1` "Semana siguiente" (solo si `week == 0`),
     `menu:home` "Menú".
   - `hours:book:{id}` → nombre de la especialidad desde `get_specialties` → `booking.start(hints={"specialty":
     nombre})`. Especialidad que ya no existe → `show_hours_menu`.
   - Sin profesionales o sin turnos en la semana → texto "No hay horarios registrados para esa especialidad en esas
     fechas." + los mismos botones.
4. Formato (en `messages/`, sin depender del locale), un bloque por profesional separado por una línea en blanco:
   ```
   *Ortodoncia* · del jue 5 al mié 11 de nov.

   Dra. Ana P.
   jue 5: 08:00–12:00 · 14:00–18:00
   vie 6: no atiende
   ```
   Fechas con `WEEKDAYS_SHORT`/`MONTHS_SHORT` de `messages/dates.py`; "hoy" en `America/Guayaquil`.
5. `router`: un `reply_id` que empieza por `hours:` fuera de un flujo va a `hours.answer_hours` (igual que los de
   `menu:`). Dentro de un flujo no cambia nada.

## Tests requeridos
1. `test_hours_specialty_shows_week_and_buttons`: dos profesionales en la especialidad, uno sin turnos un día →
   `TextMessage` con los dos nombres y "no atiende", y botones con `hours:book:{id}` y `hours:spec:{id}:1`.
2. `test_hours_next_week_has_no_next_button`: `hours:spec:{id}:1` → `get_schedule` recibe `from = hoy + 7` y los
   botones no incluyen "Semana siguiente".

Reportar la línea de totales literal de `.venv/bin/pytest -q`.

## Prueba manual
Menú → *Horarios* → *Ortodoncia* → horario semanal de sus profesionales → *Semana siguiente* → *Ver horas libres* →
"¿La cita es para…?" → días con huecos de ortodoncia.

## Resultado
- Archivos creados o modificados:
  - `app/backend/models.py`: añadidos los modelos `Shift`, `ScheduleDay` y `ProfessionalSchedule`.
  - `app/backend/client.py`: implementado `get_schedule(from_day, to_day, specialty_id=None, professional_id=None)` con llamada a `GET /api/v1/bot/schedule`.
  - `app/dialog/dependencies.py`: agregado método `get_schedule` al protocolo `Backend`.
  - `app/messages/texts.py`: agregadas constantes de horarios y la función `weekly_schedule_text`.
  - `app/dialog/hours.py`: creado módulo con `show_hours_menu` y `answer_hours` para gestionar la consulta de horarios general y por especialidad.
  - `app/dialog/menu.py`: enrutado `HOURS_ID` hacia `hours.show_hours_menu`.
  - `app/dialog/router.py`: enrutados los `reply_id` con prefijo `hours:` hacia `hours.answer_hours`.
  - `docs/BACKEND-API.md`: agregada la fila del contrato para `GET /schedule`.
  - `tests/fakes.py`: implementado `FakeBackend.get_schedule` con registro en `schedule_calls`.
  - `tests/test_hours.py`: creados los 2 tests requeridos (`test_hours_specialty_shows_week_and_buttons` y `test_hours_next_week_has_no_next_button`).
- Copia literal de pytest:
  `34 passed in 2.86s`
- Problemas encontrados y supuestos tomados:
  - Ninguno. Se verificaron tanto la navegación de semana siguiente como los accesos directos al agendamiento.

## Revisión
Estado: APROBADO

- Ids sin estado, texto y botones separados (límite de 1024), semana 1 sin "Semana siguiente". 34 passed.
- Para 033c (no bloquea aquí): la rama `hours:spec:` de `answer_hours` es larga y 033c necesita la misma vista
  para un profesional → extraer una función común; `weekly_schedule_text` debe recibir un título en lugar de
  `specialty_name`; horas con `strftime("%H:%M")` en vez de `str(...)[:5]`. `menu.py` ↔ `hours.py` se importan
  mutuamente (funciona porque se usa el atributo al llamar); no añadir más imports cruzados.
