# Flujo de trabajo — Agente WhatsApp Bellidental

- Claude: planifica y revisa. No escribe código salvo correcciones mínimas.
- Gemini (`gemini -p "..."`): ejecuta tareas, escribe código y tests, verifica y hace commit tras la aprobación.
- Qué es este repo: el agente Python (FastAPI) del bot de WhatsApp. Atiende el webhook de Meta, conversa con el
  paciente (máquina de estados + NLU con LLM) y llama a la API interna del backend Java (`/api/v1/bot/*`).
  **Nunca accede a la base de datos** ni decide reglas de negocio: Java valida y escribe (D-19).
- Contrato con el backend: `docs/BACKEND-API.md`. Diseño completo: `../bellidental-backend/docs/IMPLEMENTATION-PLAN.md`
  §4.11 y `../bellidental-backend/docs/WHATSAPP-SETUP.md` (solo para Claude; las tareas copian lo necesario).

## Ciclo
1. Claude crea `docs/tasks/NNN-nombre.md` con la numeración del plan del backend (015b, 015c, 016c…).
   `## Archivos a tocar` como árbol de `app/`, según `architecture/SKILL.md`. Tests según `testing/SKILL.md`.
2. Ejecutar: `gemini -p "Ejecuta docs/tasks/NNN-nombre.md siguiendo GEMINI.md."`
3. Claude revisa Resultado y `git diff --stat`; corre `.venv/bin/pytest -q` una vez y lee solo la línea de totales.
4. Claude escribe `## Revisión`: `Estado: CORRECCIONES` + lista numerada, o `Estado: APROBADO`.
5. Commit: `gemini -p "Haz commit de la tarea docs/tasks/NNN-nombre.md siguiendo GEMINI.md."`
6. Claude verifica con `git log -1 --stat`.

## Formato de tarea
`## Objetivo` · `## Archivos a tocar` · `## Criterios de aceptación` · `## Tests requeridos` · `## Prueba manual`
(opcional, la hace el desarrollador con el número de prueba de Meta) · `## Resultado` (Gemini) · `## Revisión` (Claude)

Reglas: @.agents/skills/architecture/SKILL.md · @.agents/skills/clean-code/SKILL.md · @.agents/skills/testing/SKILL.md
Ahorrar tokens: mensajes breves, no leer código innecesario, confiar en el Resultado.
