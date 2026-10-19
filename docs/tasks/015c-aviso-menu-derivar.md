# 015c — Aviso de privacidad, menú, información y derivar

## Objetivo
Primera conversación real del bot:
- aviso de privacidad obligatorio (RF10);
- menú principal;
- horarios, precios y formas de pago;
- derivación a recepción (RF14).

Reemplaza el texto fijo del router de la 015b por la máquina de estados base. Aquí todavía no hay NLU: cualquier texto
libre muestra el menú.

## Archivos a tocar
```
app/
  backend/client.py     (sin cambios si ya tiene los endpoints de 015a)
  dialog/
    models.py           Step: + CONSENT, MENU
    router.py           orden de filtros (criterio 1) y despacho por Step / reply_id
    consent.py          (nuevo) aviso, Acepto / No acepto
    menu.py             (nuevo) menú, horarios, precios
    handoff.py          (nuevo) derivar(conversation, info) -> list[OutgoingMessage]
  messages/
    texts.py            aviso, menú, horarios, precios, derivación, "solo texto"
tests/
  fakes.py              FakeBackend con info y consentimiento configurables
  test_menu.py          (nuevo)
```

## Criterios de aceptación
1. **Orden en `router.handle`**:
   1. `kind="unsupported"` → "Por ahora solo puedo leer mensajes de texto." y el menú.
   2. Derivación activa (`handoff_until > ahora`):
      - Si el mensaje es una opción del menú (`reply_id` que empieza por `menu:`) o el texto es "menú" o "menu"
        (sin tildes ni mayúsculas), la derivación termina y se atiende.
      - Cualquier otra cosa → no se responde nada (atiende recepción).
   3. Consentimiento:
      - Si `consent_accepted` es falso, se consulta `get_consent(phone)`.
      - Si no aceptó → aviso con botones *Acepto* / *No acepto* (`consent:yes` / `consent:no`).
      - Hasta que acepte no se procesa ningún otro mensaje: cualquier otro mensaje repite el aviso.
   4. Respuestas de botón o lista → el manejador de ese `reply_id`.
   5. Texto libre → menú. La 016e añade el NLU aquí.
2. **Aviso (RF10)**:
   - Texto breve: qué datos se usan (teléfono, nombre y datos de la cita) y para qué (gestionar citas y
     recordatorios).
   - Nombra a quienes tratan los datos por encargo de la clínica: Meta (WhatsApp), el proveedor del servidor y el
     proveedor de IA que interpreta los mensajes. Indica que se puede pedir la eliminación en recepción.
   - *Acepto* → `accept_consent(phone)`, `consent_accepted=True` y el menú.
   - *No acepto* → "Sin su aceptación no podemos atenderle por este medio. Puede escribir a recepción:
     https://wa.me/<receptionWhatsapp>". No se guarda nada.
3. **Menú**: `ListMessage` con las filas `menu:hours` Horarios · `menu:prices` Precios y pagos · `menu:book` Agendar cita
   · `menu:appointments` Mis citas · `menu:human` Hablar con recepción.
   - Por ahora *Agendar cita* y *Mis citas* derivan; la 016c y la 016d los reemplazan.
4. **Horarios**: dirección y una línea por cada `hours[]` de `/info`, y después el menú.
5. **Precios**:
   - Una línea por precio (`Profilaxis (limpieza dental): $25.00`).
   - Luego las formas de pago y la nota fija "Valores referenciales; el valor definitivo lo da el odontólogo tras la
     valoración."
   - Los montos salen del backend: el agente nunca escribe cifras propias.
6. **Derivar** (`handoff.py`, lo reutilizan todos los flujos):
   - Mensaje con el horario de atención y el enlace `https://wa.me/<receptionWhatsapp>`.
   - `handoff_until = ahora + 4 h`, `step = IDLE`, `selection` vacía.
7. `/info` se pide una vez y se cachea en memoria 10 minutos. Si el backend falla → texto "Tenemos un problema
   técnico; escriba a recepción: https://wa.me/<…>". Si no hay `/info` en caché, se usa `receptionWhatsapp` vacío y
   solo se muestra el texto.

## Tests requeridos
`tests/test_menu.py`, 4 casos, sobre `router.handle` con `FakeBackend`:
1. `test_router_without_consent_sends_notice_and_ignores_other_messages`
2. `test_consent_accept_saves_consent_and_shows_menu`
3. `test_menu_human_sets_handoff_and_next_free_text_gets_no_reply`
4. `test_menu_prices_lists_backend_prices_with_referential_note`

## Prueba manual
Con el número de prueba, desde un número sin consentimiento:
1. "hola" → aviso.
2. *Acepto* → menú.
3. Precios → lista con los montos del catálogo.
4. *Hablar con recepción* → enlace. Después, "hola" no recibe respuesta y "menú" vuelve a mostrar el menú.

## Resultado

## Revisión
