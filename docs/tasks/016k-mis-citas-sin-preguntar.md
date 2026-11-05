# 016k — "Mis citas" sin preguntar para quién es

## Objetivo
Visto en pruebas: tras aceptar el aviso, "Quiero ver mis citas" responde "¿La cita es para Juan P.?". Esa pregunta
tiene sentido al **agendar**, no al consultar las propias citas.
- No existe una intención para *ver* citas: el LLM la mete en otra (BOOK/RESCHEDULE…).
- `start_identification` pregunta Sí/No con un solo paciente en todos los flujos, también en "Mis citas".

Comportamiento nuevo en "Mis citas" (ver, reprogramar, cancelar, confirmar; por menú o texto libre):
- **1 paciente** en el número → se consultan sus citas directamente, sin preguntar.
- **Varios pacientes** (familia con el mismo celular) → se pide la cédula, como ahora.
- **Pide las citas de otra persona** ("las citas de mi hermano"): si el número tiene un solo paciente → texto fijo
  de privacidad + menú, sin llamar a `get_appointments`. Si tiene varios → se pide la cédula de esa persona
  (`verify_patient` solo acepta pacientes de ese número).
- Agendar no cambia: sigue preguntando "¿La cita es para…?".

## Archivos a tocar
```
app/
  nlu/
    models.py            Intent.APPOINTMENTS; Interpretation.other_person: bool = False
    prompt.py            APPOINTMENTS, other_person y ejemplos
  dialog/
    identify.py          start_identification(..., confirm_single: bool = True)
    appointments.py      start(..., other_person: bool = False)
    free_text.py         Intent.APPOINTMENTS → appointments.start; other_person en RESCHEDULE/CANCEL/CONFIRM
  messages/
    texts.py             APPOINTMENTS_OTHER_PERSON_TEXT
tests/
  test_appointments.py   3 tests nuevos; ajustar los que pasaban por IDENTIFY_CONFIRM en "Mis citas"
```

## Criterios de aceptación
1. `Intent.APPOINTMENTS` = ver o consultar citas propias ("quiero ver mis citas", "qué citas tengo", "tengo cita
   agendada?"). `other_person: true` cuando el mensaje habla de las citas de otra persona (hijo, hermano, mamá…),
   en APPOINTMENTS, RESCHEDULE, CANCEL o CONFIRM. Ejemplos en el prompt:
   - `"quiero ver mis citas"` → `{"intent": "APPOINTMENTS"}`
   - `"qué citas tengo agendadas"` → `{"intent": "APPOINTMENTS"}`
   - `"quiero ver las citas de mi hermano"` → `{"intent": "APPOINTMENTS", "other_person": true}`
   - `"cancela la cita de mi hijo"` → `{"intent": "CANCEL", "other_person": true}`
   La forma del JSON del prompt incluye `"other_person": false`.
2. `start_identification(conversation, backend, then, carry=None, confirm_single=True)`: con un solo paciente y
   `confirm_single=False` llama directamente a `_set_patient` (sin `IDENTIFY_CONFIRM`). 0 y varios pacientes: igual
   que ahora.
3. `appointments.start(conversation, backend, action=None, other_person=False)`:
   - Siempre `confirm_single=False`.
   - Con `other_person=True`: borra `conversation.patient_id` y `patient_name` (hay que identificar a esa persona);
     si `get_patients` devuelve 0 o 1 paciente → `[TextMessage(APPOINTMENTS_OTHER_PERSON_TEXT), *show_menu]`, paso
     `MENU`, sin llamar a `get_appointments`. Con varios → `start_identification` (pide cédula).
4. `free_text._act`: `APPOINTMENTS` → `appointments.start(action=None, other_person=…)`; `RESCHEDULE`, `CANCEL` y
   `CONFIRM` pasan también `other_person`.
5. `APPOINTMENTS_OTHER_PERSON_TEXT = "Por privacidad solo puedo mostrar las citas de los pacientes registrados con
   este número. La otra persona puede escribirnos desde su propio número o contactar a recepción."`
6. Los tests existentes de "Mis citas" que pulsaban *Sí* en `IDENTIFY_CONFIRM` se ajustan al nuevo recorrido (no se
   borran). Los de agendar siguen igual.

## Tests requeridos
1. `test_appointments_single_patient_lists_without_confirm`: texto con APPOINTMENTS, un paciente → `ListMessage`
   de citas, paso `APPT_CHOOSE`.
2. `test_appointments_other_person_single_patient_refuses`: APPOINTMENTS con `other_person`, un paciente → primer
   mensaje `APPOINTMENTS_OTHER_PERSON_TEXT`, paso `MENU`, `patient_id` en `None`.
3. `test_appointments_other_person_several_patients_asks_id`: igual con dos pacientes → paso `IDENTIFY_ID`.

Reportar la línea de totales literal de `.venv/bin/pytest -q`.

## Prueba manual
Número con un paciente: "Quiero ver mis citas" → lista de citas sin pregunta previa. "Quiero ver las citas de mi
hermano" → texto de privacidad y menú. "Quiero agendar" → sigue preguntando "¿La cita es para…?".

## Resultado
- Archivos modificados:
  - `app/nlu/models.py`: agregado `Intent.APPOINTMENTS` y campo `other_person: bool = False` en `Interpretation`.
  - `app/nlu/prompt.py`: incorporada intención `APPOINTMENTS`, explicación de `other_person` y ejemplos de consulta y citas de otra persona.
  - `app/dialog/identify.py`: añadido parámetro `confirm_single: bool = True` a `start_identification` para asociar directamente el paciente con `confirm_single=False` cuando hay 1 paciente registrado.
  - `app/dialog/appointments.py`: `start` ahora recibe `other_person`, usa `confirm_single=False`, limpia la identificación previa y devuelve `APPOINTMENTS_OTHER_PERSON_TEXT` + menú si hay 0 o 1 paciente.
  - `app/dialog/free_text.py`: enrutada `Intent.APPOINTMENTS` hacia `appointments.start`, enviando `other_person` en `APPOINTMENTS`, `RESCHEDULE`, `CANCEL` y `CONFIRM`.
  - `app/messages/texts.py`: definida constante `APPOINTMENTS_OTHER_PERSON_TEXT`.
  - `tests/test_appointments.py`: adaptados tests previos que pasaban por `ident:yes` en "Mis citas" y agregados los 3 tests requeridos.
- Copia literal de pytest:
  `32 passed in 3.54s`
- Problemas encontrados y supuestos tomados:
  - Ninguno. Los tests pasaron en verde y el flujo de agendamiento mantiene su confirmación "¿La cita es para...?".

## Revisión
Estado: APROBADO

- `confirm_single=False` en todo "Mis citas" (menú y texto libre); agendar sigue igual. `other_person` limpia el
  paciente y bloquea con 0–1 pacientes; con varios pide cédula. 34 passed.
