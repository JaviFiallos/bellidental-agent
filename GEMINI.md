# Instrucciones para Gemini — Agente Bellidental

Lee la tarea asignada en `docs/tasks/`.
Sigue @.agents/skills/architecture/SKILL.md, @.agents/skills/clean-code/SKILL.md y @.agents/skills/testing/SKILL.md.
Crea los archivos exactamente en las carpetas que indica `## Archivos a tocar`.
El contrato con el backend está en `docs/BACKEND-API.md`: no inventes endpoints ni campos.

## Entorno
- Python ≥ 3.12. Entorno virtual en `.venv`: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`.
- Tests: `.venv/bin/pytest -q` (o solo los de la tarea: `.venv/bin/pytest -q tests/<archivo>.py`).
- Nunca llamadas reales a Meta, al backend ni al LLM en los tests.

## Ejecutar una tarea
1. Si la tarea tiene `## Revisión` con `Estado: CORRECCIONES`, aplica solo esas correcciones.
2. Implementa únicamente lo que pide la tarea, en los archivos indicados.
3. Escribe solo los tests de `## Tests requeridos`, ni uno más (ver `testing/SKILL.md`).
4. Al final, una vez: `.venv/bin/pytest -q`.
5. Llena (o reemplaza) la sección Resultado con:
   - Qué hiciste (archivos creados o modificados).
   - **Copia literal** de la línea de totales de pytest (p. ej. `12 passed in 0.80s`). Nunca escribas totales que
     no salieron en la consola.
   - Problemas encontrados y supuestos tomados.

No hagas commit al ejecutar una tarea.
No cambies el alcance, la arquitectura ni el backend. Si la API del backend no tiene lo que la tarea necesita,
detente y anótalo en Resultado.

## Hacer commit (solo cuando se pida)
1. Verifica que `## Revisión` diga `Estado: APROBADO`; si no, detente y no hagas nada.
2. Corre `.venv/bin/pytest -q`; si falla, no hagas commit y anótalo en Resultado.
3. `git add` solo los archivos de la tarea y el propio `docs/tasks/NNN-*.md`. Nunca `.venv/`, `__pycache__/`,
   `.env` ni secretos.
4. Un commit en Conventional Commits: `<tipo>(<carpeta>): <resumen> (tarea NNN)`.
5. No hagas push ni cambies de rama.
