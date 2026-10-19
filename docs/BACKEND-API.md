# Contrato con el backend — `/api/v1/bot/*`

API interna del backend Java (tareas 015a, 016a, 016b y 017a del backend). Solo el agente la usa, por la red interna
de Docker; Caddy no la expone a internet.

- Autenticación: header `X-Bot-Key: <BOT_API_KEY>`. Sin él → 401.
- Toda respuesta va envuelta: `{"success": bool, "message": str?, "code": str?, "data": ...}`.
- `phone` = número tal como lo manda WhatsApp (`wa_id`, p. ej. `593987654321`).
- Fechas: `startAt`/`endAt` en ISO-8601 con offset (`2026-10-20T10:30:00-05:00`); días como `2026-10-20`.
- Errores que el agente debe distinguir:
  - `404` → no existe o no pertenece a ese teléfono;
  - `409` con `code` → ver la tabla de códigos;
  - cualquier otro error, o un timeout de más de 10 s → derivar a recepción.

| Código 409 | Significa | Qué hace el agente |
|---|---|---|
| `APPOINTMENT_OVERLAP` | el hueco se ocupó mientras el paciente elegía | avisar y ofrecer otras horas |
| `BOT_LIMIT_REACHED` | ya tiene una cita activa en esa especialidad, o el teléfono llegó al máximo (D-9) | explicar y derivar |
| `BOT_TOO_LATE` | faltan menos de 2 h para la cita (D-10) | derivar |

## 015a — base
| Método y ruta | Cuerpo | `data` |
|---|---|---|
| `GET /consents?phone=` | — | `{accepted: bool, noticeVersion: str}` |
| `POST /consents` | `{phone, patientId?}` | igual (201) |
| `GET /info` | — | `{clinicName, address, hours: [str], paymentMethods: [str], receptionWhatsapp, afterHoursPhone, prices: [{code, name, price}]}` |
| `GET /patients?phone=` | — | `[{patientId, displayName}]` (`"Juan P."`) |
| `POST /patients/verify` | `{phone, idNumber}` | `{patientId, displayName}` o 404 |

## 016a — consultas de agenda
| Método y ruta | `data` |
|---|---|
| `GET /specialties` | `[{specialtyId, name, durationMinutes}]` |
| `GET /professionals?specialtyId=` | `[{professionalId, displayName}]` |
| `GET /availability/days?specialtyId=&professionalId=` (profesional opcional) | `["2026-10-20", …]`: próximos 14 días con huecos |
| `GET /availability?specialtyId=&professionalId=&date=` (profesional opcional) | `[{professionalId, professionalName, startAt, endAt}]`: máx. 10 |
| `GET /urgent-slots` | `{specialtyId, noSlotsToday: bool, slots: [slot]}`: máx. 3, hoy o mañana |
| `GET /appointments?phone=&patientId=` | `[{appointmentId, specialtyId, specialtyName, professionalId, professionalName, startAt, status}]`: solo las activas futuras |

## 016b — escrituras de agenda (solo tras *Confirmar*)
| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| `POST /appointments` | `{phone, patientId, specialtyId, professionalId, startAt}` | 201, cita (forma de `GET /appointments`) |
| `POST /appointments/{id}/reschedule` | `{phone, startAt}` | 200, cita nueva |
| `POST /appointments/{id}/cancel` | `{phone}` | 200 |
| `POST /appointments/{id}/confirm` | `{phone}` | 200 |

## 017a — recordatorios
| Método y ruta | Cuerpo | `data` |
|---|---|---|
| `GET /reminders/due` | — | `[{reminderId, appointmentId, phone, patientFirstName, professionalName, startAt}]`: máx. 50 |
| `POST /reminders/{id}/sent` | `{waMessageId}` | — |
| `POST /reminders/{id}/failed` | — | — |
| `POST /reminders/response` | `{waMessageId, phone, response: CONFIRMED\|CANCELLED\|RESCHEDULED}` | `{outcome: CONFIRMED\|CANCELLED\|RESCHEDULE_REQUESTED\|TOO_LATE, appointmentId, patientId}` |
