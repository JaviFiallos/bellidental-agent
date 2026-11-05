# 016j — Logs de httpx sin el teléfono del paciente

## Objetivo
Visto en producción tras la 016g: `logging.basicConfig(level=INFO)` también activa los logs INFO de `httpx` (cliente
del backend y de Meta) y de `httpx2` (lo usa el SDK `anthropic`). Esos logs imprimen la URL completa de cada petición,
y algunas llevan el teléfono sin enmascarar:
```
INFO httpx: HTTP Request: GET http://backend:8080/api/v1/bot/consents?phone=5939XXXXXXXX "HTTP/1.1 200 OK"
```
Incumple la regla de privacidad (LOPDP, RNF03: el teléfono se enmascara). Se silencian esos dos loggers por debajo de
WARNING; los logs propios del agente (`app.*`) siguen en INFO.

## Archivos a tocar
```
app/
  main.py          tras logging.basicConfig: loggers "httpx" y "httpx2" en WARNING
tests/
  test_webhook.py  1 test
```

## Criterios de aceptación
1. Justo después de `logging.basicConfig(...)` en `create_app`, `logging.getLogger("httpx")` y
   `logging.getLogger("httpx2")` quedan con nivel `logging.WARNING` (un bucle o dos líneas; sin función nueva si no
   hace falta).
2. Los logs propios no cambian: siguen la línea INFO por mensaje (`Message from ... kind=... step=... replies=...`),
   `LLM intent=...` y los errores con `status`/`code`.
3. Sin cambios en `dialog/`, `nlu/`, `whatsapp/`, `backend/` ni en las dependencias.

## Tests requeridos
1. `test_webhook_app_created_http_client_logs_silenced`: tras `create_app(...)` (con los fakes, como los demás tests
   del archivo), `logging.getLogger("httpx").getEffectiveLevel()` y el de `"httpx2"` son `>= logging.WARNING`.

Reportar la línea de totales literal de `.venv/bin/pytest -q`.

## Prueba manual
Tras desplegar: escribir `hola` al bot y en `docker compose logs agent` no aparece ninguna línea `HTTP Request:`;
sí la línea `Message from 5939****XXXX kind=... step=... replies=...`.

## Resultado

- Modificado `app/main.py`: tras `logging.basicConfig(...)` en `create_app`, los loggers `httpx` y `httpx2` quedan en `WARNING`.
- Modificado `tests/test_webhook.py`: añadido `test_webhook_app_created_http_client_logs_silenced` (y `import logging`).
- Totales (`.venv/bin/pytest -q`): `29 passed in 8.24s`
- Supuestos: se usa `setLevel` en un bucle sobre los dos nombres; no hay cambios en `dialog/`, `nlu/`, `whatsapp/`, `backend/` ni dependencias.

## Revisión
Estado: APROBADO

- `httpx` y `httpx2` quedan en WARNING justo tras `basicConfig`; los logs `app.*` siguen en INFO. Solo cambió
  `main.py` y el test pedido. `.venv/bin/pytest -q` → `29 passed in 10.95s`.
