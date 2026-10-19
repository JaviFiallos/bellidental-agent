---
name: testing
description: Reglas de tests del agente Python de Bellidental. Usar al escribir o correr tests.
---
Principio: pocos tests y solo los esenciales. La verificación de punta a punta la hace el desarrollador con el número
de prueba de Meta (`## Prueba manual`); los tests automáticos cubren lo que es caro de ver a mano.

- Quién: Gemini escribe y corre los tests de cada tarea, en la misma tarea.
- Escribir solo los tests listados en `## Tests requeridos`; nunca añadir otros por iniciativa propia. **Máximo 4 por
  tarea.**
- Qué se prueba: la máquina de estados (`dialog/`), la verificación de firma y el parser del webhook, y el job de
  recordatorios. No se prueban textos exactos, modelos pydantic, `config.py` ni el cliente httpx en sí.
- Siempre con fakes de `tests/fakes.py` (backend, WhatsApp, clasificador) que implementan los mismos `Protocol`;
  nunca llamadas reales a Meta, al backend ni al LLM. Sin librerías de mocking extra.
- `pytest` + `pytest-asyncio` (modo `auto` en `pyproject.toml`). Rutas FastAPI con `fastapi.testclient.TestClient`.
- Nombre: `test_<flujo>_<condicion>_<resultado_esperado>`.
- Correr: `.venv/bin/pytest -q`. Reportar la línea de totales literal. Un test que falla no se borra ni se salta:
  se reporta en Resultado. Los tests existentes no se borran salvo en una tarea dedicada.
