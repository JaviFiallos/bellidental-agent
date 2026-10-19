# 016c — Identificación del paciente y agendar cita

## Objetivo
El paciente agenda una cita desde WhatsApp (RF12) con botones y listas: especialidad → profesional → día → hora →
*Confirmar*.
- Antes se identifica quién es el paciente por el teléfono (y la cédula si hace falta).
- La cita solo se crea al pulsar *Confirmar*.
- Java valida horario, cruce y límites (D-9). El agente solo muestra lo que devuelve el backend.

Reemplaza la derivación temporal de `menu:book` (015c). Endpoints: `docs/BACKEND-API.md` §015a, §016a y §016b.

## Archivos a tocar
```
app/
  backend/client.py     + get_specialties, get_professionals, get_available_days, get_slots, book_appointment
  backend/models.py     + Specialty, Professional, Slot, Appointment
  dialog/
    models.py           Step: + IDENTIFY_CONFIRM, IDENTIFY_ID, BOOK_SPECIALTY, BOOK_PROFESSIONAL, BOOK_DAY,
                        BOOK_SLOT, BOOK_CONFIRM
    identify.py         (nuevo) start_identification(conversation, then: str) y sus respuestas
    slot_picker.py      (nuevo) listas de días y de horas reutilizables (las usa la 016d)
    booking.py          (nuevo) flujo de agendar
    router.py           despacha los nuevos Step y prefijos de reply_id
  messages/
    dates.py            (nuevo) format_long(dt) "martes 21 de octubre, 10:30", format_day(date) "mar 21 oct",
                        format_time(dt) "10:30"; en CLINIC_ZONE, nombres en español sin locale del sistema
    texts.py            + textos del flujo
tests/
  fakes.py              FakeBackend + pacientes, especialidades, días, huecos, error configurable en book
  test_booking.py       (nuevo)
```

## Criterios de aceptación
1. **Identificación** (`identify.py`, reutilizable):
   - Si `conversation.patient_id` ya está puesto, se salta.
   - `get_patients(phone)`:
     - 0 pacientes → derivar con el texto "Para su primera cita, recepción le registrará."
     - 1 paciente → "¿La cita es para Juan P.?" con *Sí* / *No*. *No* → derivar.
     - Varios → "Escriba la cédula del paciente". `verify_patient`; si falla, un intento más; si vuelve a fallar →
       derivar.
   - Al terminar, `patient_id` queda en la conversación y se sigue con el flujo indicado en `then`.
   - En el paso `IDENTIFY_ID` el texto se trata solo como cédula: no pasa por el NLU (016e) ni se guarda en
     `history`.
2. **Agendar**:
   - **Especialidad**: lista de `get_specialties`. Si solo hay una, se salta el paso.
   - **Profesional**: lista con *Primero disponible* y los profesionales de esa especialidad. Si solo hay uno, se
     salta.
   - **Día**: lista de hasta 10 días de `get_available_days` (`format_day`). Si no hay días → "No hay horarios
     libres en los próximos 14 días" y derivar.
   - **Hora**: lista de `get_slots` del día. Cada fila tiene la hora como título y el profesional como descripción.
   - **Confirmar**: resumen "Odontología general · martes 21 de octubre, 10:30 · Odontóloga Principal · para
     Juan P." con *Confirmar* / *Cambiar hora* / *Cancelar*.
     - *Confirmar* → `book_appointment(...)` → "Listo, su cita quedó agendada para …. Le enviaremos un recordatorio
       el día anterior."
     - *Cambiar hora* → vuelve a la lista de horas.
     - *Cancelar* → menú.
3. **Errores del backend** (por `code`):
   - `APPOINTMENT_OVERLAP` → "Esa hora acaba de ocuparse" y la lista de horas del mismo día, de nuevo;
   - `BOT_LIMIT_REACHED` → "Ya tiene una cita próxima en esta especialidad; para otra, recepción le ayuda" y
     derivar;
   - otro error → derivar.
4. **Respuestas fuera de lugar**:
   - Un `reply_id` que no corresponde al `Step` actual (por ejemplo, de una lista vieja) o un texto libre a mitad
     del flujo repiten la pregunta actual. La 016e añade los cambios de intención.
   - "menú" o "menu" cancela el flujo.
   - Los `reply_id` llevan prefijo y valor: `spec:1`, `prof:any`, `prof:<uuid>`, `day:2026-10-21`,
     `slot:<uuid>|<startAt>`, `book:confirm`. Todos tienen como mucho 200 caracteres.
5. Al terminar o cancelar: `step=IDLE` y `selection` vacía. `patient_id` se conserva mientras viva la conversación.

## Tests requeridos
`tests/test_booking.py`, 4 casos, con `FakeBackend`:
1. `test_booking_single_patient_full_path_confirm_books_selected_slot`:
   - "primero disponible", día y hora elegidos;
   - `book_appointment` recibe el `professionalId` y el `startAt` del hueco.
2. `test_booking_confirm_overlap_reoffers_hours_of_same_day`
3. `test_identification_two_patients_wrong_id_twice_derives`
4. `test_booking_limit_reached_explains_and_derives`

## Prueba manual
Con el backend local y un paciente cuyo teléfono es tu número de prueba:
1. Menú → *Agendar cita* → completar el flujo → la cita aparece en la agenda del frontend con origen BOT.
2. Repetir en la misma especialidad → mensaje de límite.

## Resultado

## Revisión
