# 016h — Especialidad sin profesionales y salida de la derivación

## Objetivo
Visto en producción: el paciente eligió **Endodoncia**, que aún no tenía profesionales. El bot lo derivó a recepción
sin explicar por qué y después se quedó 4 horas sin responder, que es lo que hace la derivación. El paciente no
sabía que escribiendo `menu` volvía al asistente.
- Especialidad sin profesionales: se avisa y se ofrecen las demás especialidades, sin derivar.
- El mensaje de derivación dice cómo volver al asistente.

## Archivos a tocar
```
app/
  dialog/
    booking.py           show_professionals: caso sin profesionales
  messages/
    texts.py             BOOK_NO_PROFESSIONALS_TEXT; handoff_text con la línea de "menu"
tests/
  fakes.py               (si hace falta) profesionales vacíos para una especialidad
  test_booking.py        1 test
```

## Criterios de aceptación
1. `show_professionals`, cuando `get_professionals` devuelve una lista vacía:
   - Vuelve a pedir las especialidades **excluyendo** la que no tiene profesionales. Construye la lista directamente:
     **no** llama a `show_specialties`, que con una sola especialidad la elige sola y entraría en bucle.
   - Devuelve `[TextMessage(BOOK_NO_PROFESSIONALS_TEXT), <lista de especialidades restantes>]` con
     `conversation.step = Step.BOOK_SPECIALTY`. La pista `specialty` del NLU, si quedaba, se descarta.
   - Si no queda ninguna otra especialidad: `[TextMessage(BOOK_NO_PROFESSIONALS_TEXT), *hand_off_from_backend(...)]`.
2. `BOOK_NO_PROFESSIONALS_TEXT = "Por ahora no hay profesionales disponibles para esa especialidad."`
3. `handoff_text(info)` añade al final una línea: `"Para volver al asistente, escriba *menu*."`
4. Los demás casos de derivación (`BOOK_NO_DAYS_TEXT`, límites del backend) no cambian.

## Tests requeridos
1. `test_booking_specialty_without_professionals_offers_other_specialties`: dos especialidades, la elegida sin
   profesionales → dos mensajes (texto + lista), la lista no contiene la especialidad elegida, paso
   `BOOK_SPECIALTY` y `handoff_until` sigue en `None`.

Reportar la línea de totales literal de `.venv/bin/pytest -q`.

## Prueba manual
Con una especialidad activa sin profesionales en producción: **Agendar cita** → elegirla → mensaje "Por ahora no
hay profesionales…" y la lista de las otras especialidades.

## Resultado

**Archivos modificados:**
- `app/dialog/booking.py`: `show_professionals` llama a `_ask_other_specialty` si la lista está vacía. Esa función descarta la pista `specialty`, excluye la especialidad sin profesionales y devuelve `[TextMessage(BOOK_NO_PROFESSIONALS_TEXT), lista]` con paso `BOOK_SPECIALTY`; si no queda ninguna, deriva con `hand_off_from_backend`. Las filas de especialidades se extraen a `_specialty_rows` y se reutilizan en `show_specialties`. No llama a `show_specialties`.
- `app/messages/texts.py`: `BOOK_NO_PROFESSIONALS_TEXT` y línea "Para volver al asistente, escriba *menu*." al final de `handoff_text`.
- `tests/test_booking.py`: 1 test nuevo (`test_booking_specialty_without_professionals_offers_other_specialties`).

Sin cambios en `tests/fakes.py`: el test usa `FakeBackend` con `professionals = []`.

**Totales de pytest:**
```
28 passed in 5.43s
```

**Supuestos:** ninguno. No se hizo commit.

## Revisión
Estado: APROBADO

- `_ask_other_specialty` construye la lista sin pasar por `show_specialties` (sin bucle), excluye la especialidad
  elegida, descarta la pista `specialty` y deriva solo si no queda ninguna. `handoff_text` termina con la línea de
  `menu`. Cumple los criterios 1–4.
- `.venv/bin/pytest -q` → `28 passed in 5.81s`.
