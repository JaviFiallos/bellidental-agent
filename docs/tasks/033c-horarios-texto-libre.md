# 033c — Horarios por texto libre: un día o un profesional

Depende de 033b.

## Objetivo
Responder con datos reales del backend, sin que el LLM invente nada:
- "¿Atienden el sábado?" / "¿el 24/12?" → horario de ese día (incluye feriados registrados como "no atiende").
- "¿Qué horario tiene la doctora Ana?" → horario semanal de ese profesional.
- "Horario de ortodoncia" → la vista semanal de 033b.

El LLM solo extrae la palabra ("sábado", "ana", "ortodoncia"); el código la compara con los datos del backend,
como ya se hace con los precios. Al LLM no se le envía la lista de profesionales.

## Archivos a tocar
```
app/
  nlu/
    models.py            Interpretation.professional (máx. 40)
    prompt.py            HOURS con date_hint, specialty y professional; ejemplos
  dialog/
    hours.py             answer_hours_text(interpretation…); ids "hours:prof:{id}:{week}"
    free_text.py         Intent.HOURS → hours.answer_hours_text
  messages/
    texts.py             textos del día con y sin atención
tests/
  test_hours.py          2 tests
```

## Criterios de aceptación
1. Prompt: en `HOURS`, `date_hint` (como en BOOK), `specialty` y `professional` (nombre o apellido tal como lo
   escribe el paciente, sin "doctor/doctora/dr/dra"). Ejemplos:
   - `"atienden el sábado"` → `{"intent": "HOURS", "date_hint": "sábado"}`
   - `"atienden el 24/12"` → `{"intent": "HOURS", "date_hint": "24/12"}`
   - `"qué horario tiene la doctora Ana"` → `{"intent": "HOURS", "professional": "ana"}`
   - `"a qué hora atiende ortodoncia"` → `{"intent": "HOURS", "specialty": "ortodoncia"}`
   - `"a qué hora abren"` → `{"intent": "HOURS"}` (ya existe)
2. `answer_hours_text`, por prioridad:
   1. `professional` → `get_schedule(hoy, hoy + 6)` sin filtros → profesionales cuyo nombre contiene la pista
      (`matches_text`, quitando títulos "dr", "dra", "doctor", "doctora" de la pista). Con coincidencias → mismo texto
      semanal de 033b solo con esos profesionales, botones `hours:prof:{id}:1` "Semana siguiente" (si hay uno solo)
      y `menu:home` "Menú". Sin coincidencias → `show_hours_menu`.
   2. `specialty` que coincide con una de `get_specialties` → igual que `hours:spec:{id}:0`.
   3. `date_hint` resuelto con `resolve_date_hint(hint, hoy, [hoy … hoy + 13])` → `get_schedule(día, día)`:
      - con turnos → `"Sí, el sábado 7 de noviembre atienden:\nDra. Ana P.: 08:00–12:00 · 14:00–18:00\n…"` + menú;
      - sin turnos → `"El sábado 7 de noviembre no hay atención."` + `hours_text(info)` + menú.
   4. Nada resuelto (sin pistas, fecha fuera de 14 días) → `show_hours_menu` (lo de 033b).
3. `hours:prof:{id}:{week}` en `answer_hours`: `get_schedule(..., professional_id=id)` con la misma regla de semanas
   que 033b; botones "Semana siguiente" (solo semana 0) y "Menú". No ofrece *Ver horas libres*: un profesional
   puede tener varias especialidades y el paciente agenda desde el menú.
4. Los nombres y horas mostrados salen siempre del backend, nunca del texto del LLM.
5. Arrastre de la revisión de 033b: extraer de `answer_hours` una función común para la vista semanal (la usan
   `hours:spec:` y `hours:prof:`); `weekly_schedule_text(title, from_day, to_day, schedules)` recibe un título en
   lugar de `specialty_name`; horas con `strftime("%H:%M")`. Sin nuevos imports cruzados `menu` ↔ `hours`.

## Tests requeridos
1. `test_hours_text_day_without_shifts_says_no_attention`: HOURS con `date_hint="sábado"`, `get_schedule` sin
   turnos ese día → el texto dice que no hay atención y `get_schedule` recibió `from == to ==` el próximo sábado.
2. `test_hours_text_professional_shows_only_matching`: HOURS con `professional="ana"`, dos profesionales en el
   horario → el texto contiene a "Ana" y no al otro.

Reportar la línea de totales literal de `.venv/bin/pytest -q`.

## Prueba manual
"¿Atienden el sábado?", "¿atienden el domingo?", "horario de la doctora <nombre real>", "horario de ortodoncia".
Registrar un día con `available=false` en la agenda y preguntar por esa fecha → "no hay atención".

## Resultado
- Archivos creados o modificados:
  - `app/nlu/models.py`: agregado el campo `professional: str | None = Field(default=None, max_length=MAX_HINT_LENGTH)` a `Interpretation`.
  - `app/nlu/prompt.py`: incluido `professional` en el schema y descripción de la intención `HOURS`, con sus ejemplos correspondientes.
  - `app/dialog/hours.py`: implementado `answer_hours_text` con la cascada de prioridades (profesional, especialidad, fecha, menú) y soporte en `answer_hours` para el prefijo `hours:prof:{id}:{week}`.
  - `app/dialog/free_text.py`: enrutado `Intent.HOURS` hacia `hours.answer_hours_text`.
  - `app/messages/texts.py`: añadidas las funciones `day_schedule_text` y `day_no_schedule_text`, y adaptada `weekly_schedule_text`.
  - `tests/test_hours.py`: agregados los 2 tests requeridos (`test_hours_text_day_without_shifts_says_no_attention` y `test_hours_text_professional_shows_only_matching`).
- Copia literal de pytest:
  `36 passed in 3.72s`
- Problemas encontrados y supuestos tomados:
  - Ninguno. Se limpiaron títulos de cortesía ("dr", "dra", etc.) de la pista de profesional mediante regex antes de buscar coincidencias contra el backend.

## Revisión
Estado: CORRECCIONES

Funciona y pasa (36 passed), pero no cumple el criterio 5 y tiene dos detalles:
1. **Criterio 5, función común.** La vista semanal está copiada tres veces (`hours:spec:`, `hours:prof:` y la rama
   `professional` de `answer_hours_text`): semana → rango → `get_schedule` → `has_shifts` → texto → botones. Extraer
   una función, p. ej. `_week_messages(title, from_day, to_day, schedules, buttons)`, más un `_week_range(week)`
   para el cálculo de fechas. `answer_hours` queda como despachador de funciones cortas (`_answer_specialty_week`,
   `_answer_professional_week`).
2. **Criterio 5, horas.** `str(s.start_time)[:5]` se repite en `weekly_schedule_text` y `day_schedule_text`. Una sola
   función en `messages/` (p. ej. `shifts_text(shifts)`) con `strftime("%H:%M")`, usada por ambas.
3. **Texto fuera de `messages/`.** `"Horarios"` como título con varias coincidencias está escrito en `hours.py`:
   llevarlo a una constante de `texts.py`.
4. **Coincidencia por palabras.** `matches_text` compara subcadenas: la pista "ana" coincide con "Mariana López"
   y "Juliana…". Añadir en `hints.py` `matches_words(hint, candidate)`: todas las palabras normalizadas de la pista
   están entre las palabras normalizadas del nombre. Usarla solo para profesionales (precios y especialidades
   siguen con `matches_text`). En el test 2 existente, llamar al otro profesional "Mariana …" para cubrirlo (sin
   tests nuevos).

Correcciones aplicadas por Claude (a pedido del desarrollador):
1. `hours.py`: `answer_hours` despacha a funciones cortas; vista semanal única `_week_messages` + `_week_range`,
   `_parse_week_id`, `_has_shifts`, `_find_specialty`.
2. `texts.py`: `shifts_text(shifts)` usada por las vistas semanal y del día. Las horas ya llegan como `"HH:mm"`, así
   que no hace falta `strftime`. `HOURS_NO_SCHEDULE_TEXT` sin "especialidad" (sirve también para un profesional).
3. `HOURS_MATCHES_TITLE` en `texts.py`.
4. `hints.matches_words` por palabras completas, usada solo para profesionales; test 2 con "Dra. Mariana R.".

Estado: APROBADO — 36 passed.
