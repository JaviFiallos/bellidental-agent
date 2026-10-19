---
name: clean-code
description: Reglas de código del agente Python de Bellidental. Usar al escribir código.
---
- Nombres claros en inglés (`snake_case`, clases `PascalCase`); nada de abreviaturas ni `data`, `info`, `tmp`.
  Los textos al paciente van en español y solo en `app/messages/`.
- Funciones pequeñas con una sola responsabilidad; sin duplicación. Type hints en todo; modelos con pydantic.
- `async`/`await` de punta a punta (FastAPI, httpx.AsyncClient). Nada bloqueante en el bucle de eventos.
- Secretos solo por variables de entorno (`app/config.py`); `.env.example` sin valores reales. Nunca en el código.
- Privacidad (LOPDP, RNF03): los logs no llevan el texto de los mensajes, la cédula ni el nombre; el teléfono se
  enmascara (`5939****4321`). Al LLM solo va el texto del mensaje y el paso actual, nunca nombre ni cédula.
- Fechas con zona `America/Guayaquil` (`zoneinfo`); formato al paciente en español sin depender del locale del SO.
- Dependencias mínimas: `fastapi`, `uvicorn`, `httpx`, `pydantic`, `pydantic-settings`; dev: `pytest`,
  `pytest-asyncio`. Ninguna otra sin que la tarea lo diga.
- No crear, borrar ni mover carpetas fuera del alcance de la tarea.
