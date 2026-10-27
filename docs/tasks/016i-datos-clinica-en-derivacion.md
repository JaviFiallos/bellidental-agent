# 016i — Datos de la clínica al derivar a recepción

## Objetivo
Cuando el bot deriva a recepción (opción **Hablar con recepción**, `handoff_text`), mostrar la dirección, el
teléfono y el lema de la clínica, como en su perfil de WhatsApp:
```
📍 Edificio Cruz Roja, tercer piso, Baños de Agua Santa
📞 096 219 8909
🦷 Creamos bellas sonrisas
```
- La dirección y el WhatsApp de recepción ya llegan en `GET /api/v1/bot/info` (`address`, `receptionWhatsapp`);
  el backend los cambia en su `application.yml` (`address`, `reception-whatsapp: "593962198909"`).
- El teléfono se muestra a partir de `reception_whatsapp` en formato local (`593962198909` → `096 219 8909`); el
  lema es una constante del agente. Sin cambios en el contrato con el backend.

## Archivos a tocar
```
app/messages/
  texts.py        CLINIC_TAGLINE, _local_phone(e164) y handoff_text con el bloque de datos
```

## Criterios de aceptación
1. `handoff_text(info)` devuelve, en este orden:
   ```
   Le atenderá recepción en el horario de atención:
   <horarios, uno por línea>

   📍 <info.address>
   📞 <teléfono local>
   🦷 Creamos bellas sonrisas

   Escriba a recepción: https://wa.me/<info.reception_whatsapp>
   Para volver al asistente, escriba *menu*.
   ```
   (la última línea ya existe desde la tarea 016h y se conserva).
2. `_local_phone`: si el número empieza con `593` y tiene 12 dígitos → `0` + 9 dígitos agrupados `0XX XXX XXXX`;
   en cualquier otro caso devuelve el valor tal cual. Si `reception_whatsapp` está vacío se omiten la línea 📞 y la
   del enlace.
3. Si `info.address` está vacío se omite la línea 📍.
4. Sin cambios en `hours_text`, `consent_refused_text`, `technical_problem_text` ni en `dialog/`.

## Tests requeridos
Ninguno nuevo (no se prueban textos, `testing/SKILL.md`). Reportar la línea de totales de `.venv/bin/pytest -q`.

## Prueba manual
Tras desplegar backend y agente: `hola` → menú → **Hablar con recepción** → sale el bloque 📍 📞 🦷 y el enlace
`https://wa.me/593962198909` abre el chat de la clínica.

## Resultado

- Archivo modificado: `app/messages/texts.py` (sin tests nuevos).
  - Añadida constante `CLINIC_TAGLINE = "Creamos bellas sonrisas"`.
  - Añadida `_local_phone(e164)`: `593` + 9 dígitos (12 en total) → `0XX XXX XXXX`; otro caso devuelve el valor tal cual.
  - `handoff_text(info)` ahora incluye el bloque 📍 (si hay `address`), 📞 (si hay `reception_whatsapp`) y 🦷 seguido
    de la línea `Escriba a recepción: https://wa.me/...` (solo si hay `reception_whatsapp`); la última línea
    `Para volver al asistente, escriba *menu*.` se conserva.
- Verificado a mano con `ClinicInfo` de ejemplo: la salida coincide con el bloque de Criterios de aceptación 1.
  Sin 📍 ni 📞 ni enlace cuando faltan los datos.
- Sin cambios en `hours_text`, `consent_refused_text`, `technical_problem_text` ni en `dialog/`.
- Línea de totales: `28 passed in 4.98s`

## Revisión
Estado: APROBADO

- `handoff_text` arma el bloque 📍 📞 🦷 en el orden del criterio 1, omite 📍, 📞 y el enlace cuando faltan los
  datos y conserva la línea de `menu` de la 016h. `_local_phone` cumple el criterio 2. Solo cambió `texts.py`.
