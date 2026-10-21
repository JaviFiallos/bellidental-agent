# 018b — Imagen Docker del agente y CI/CD

## Objetivo
Dejar el agente listo para producción en el VPS de Contabo (D-17): imagen endurecida en GHCR y despliegue con un
`git push` a `main`. El compose de producción y el `Caddyfile` están en el backend (018a): Caddy publica solo
`https://bot.<dominio>/webhook` → `agent:8000`; `/health` queda interno.
Pasos manuales (crear el repo en GitHub, secretos, webhook de Meta): `../bellidental-backend/docs/DEPLOY-SETUP.md`.

**Estado del entorno (2026-10-21):** el VPS ya está en línea (backend 018e): `/opt/bellidental` con el compose,
el `Caddyfile` y el `.env`; db, backend, frontend y caddy corriendo; `https://bot.bellidentalv1.site/webhook` da 502
porque falta este contenedor. El pipeline del backend **no** levanta el agente: lo hace este repo.
- Flujo de ramas: este repo aún no tiene remoto. El desarrollador crea `JaviFiallos/bellidental-agent` y sube
  `main`; luego crea `develop` y trabaja ahí. `deploy` solo corre con push a `main` (PR `develop` → `main`).
- El agente arranca con los `WA_*` y `LLM_*` vacíos (valores por defecto en `app/config.py`); el webhook de Meta y
  los recordatorios se activan después (`DEPLOY-SETUP.md` §7).

**Restricción clave**: el estado de las conversaciones, los locks por teléfono y la deduplicación viven en memoria
(`app/dialog/store.py`, `app/main.py`). Debe correr **un solo proceso** (1 worker, 1 réplica).

## Archivos a tocar
```
Dockerfile                    ajustar
.dockerignore                 (nuevo)
.github/workflows/
  ci-cd.yml                   (nuevo)
app/                          sin cambios
```

## Criterios de aceptación

**Dockerfile**
1. Base `python:3.13-slim` (se mantiene). Añadir `ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
   PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1`.
2. Instalar dependencias en una capa que no cambie con el código: copiar `pyproject.toml` y `README.md`, instalar
   solo las dependencias de `[project.dependencies]`, y después copiar `app/` e instalar el paquete
   (`pip install --no-deps .`). Cambiar un `.py` no debe reinstalar FastAPI.
3. Usuario no root (se mantiene `appuser`).
4. `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1",
   "--proxy-headers", "--forwarded-allow-ips", "*"]` (detrás de Caddy, red interna).
5. `HEALTHCHECK` sin instalar curl:
   `python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"`.
6. La imagen final pesa menos de 250 MB.
7. `.dockerignore`: `.venv/`, `tests/`, `.pytest_cache/`, `*.egg-info/`, `__pycache__/`, `.git/`, `docs/`,
   `.agents/`, `.env`, `.env.*` (incluye `.env.example`: no va en la imagen).

**`.github/workflows/ci-cd.yml`** — misma forma que backend 018a y frontend 022
8. Disparadores: `pull_request` y `push` a `main` y `develop` (`branches: [main, develop]`, como el backend).
   `permissions` mínimos (`contents: read`; `packages: write` solo en `image`).
9. Job `test` (siempre): `actions/checkout`, `actions/setup-python` (3.13, `cache: pip`), `pip install -e ".[dev]"`,
   `pytest -q`.
10. Job `image` (`if: github.ref == 'refs/heads/main' && github.event_name == 'push'`, `needs: test`): buildx, login a `ghcr.io` con `GITHUB_TOKEN`, etiquetas
    `latest` y `type=sha,prefix=sha-`, caché `type=gha`, `linux/amd64`. Imagen: `ghcr.io/javifiallos/bellidental-agent`.
11. Job `deploy` (mismo `if` que `image`, `needs: image`, `environment: production`,
    `concurrency: { group: deploy-production, cancel-in-progress: false }`), con la misma forma que el del backend:
    paso "Preparar claves SSH" (`VPS_SSH_KEY` → `~/.ssh/id_ed25519` con `chmod 600`, `VPS_KNOWN_HOSTS` →
    `~/.ssh/known_hosts`, ambos por `env:` y `printf '%s\n'`) y paso "Desplegar en el VPS" con
    `ssh "$VPS_USER@$VPS_HOST" 'bash -s' <<'REMOTE'` y `set -euo pipefail`:
    - si no existe `/opt/bellidental/docker-compose.yml`: aviso y `exit 0` (lo instala el backend 018a);
    - `cd /opt/bellidental && docker compose pull agent && docker compose up -d agent`;
    - esperar hasta 60 s (12 × 5 s) a que el contenedor de `agent` esté `healthy`; si no,
      `docker compose logs --tail=80 agent` y `exit 1`;
    - `docker image prune -f`.
    Sin `scp` ni otros servicios del compose.
12. Ningún secreto en los logs.

## Tests requeridos
Ninguno nuevo (la suite pytest existente corre en el pipeline). Gemini anota en Resultado:
1. `docker build -t bellidental-agent .` y el tamaño;
2. `docker run --rm -p 8000:8000 --env-file .env.example bellidental-agent` → `curl localhost:8000/health` = 200
   y `docker inspect` muestra `healthy` tras unos segundos;
3. tocar un `.py` y reconstruir: la capa de dependencias sale de caché;
4. `.venv/bin/pytest -q` (línea de totales).

## Prueba manual (desarrollador)
1. Crear el repo privado `JaviFiallos/bellidental-agent`, `git remote add origin …` y `git push -u origin main`
   (`DEPLOY-SETUP.md` §4.1); crear `develop` y subirlo.
2. En el repo: Settings → Environments → `production` (ese nombre exacto): secrets `VPS_HOST`, `VPS_USER`,
   `VPS_SSH_KEY`, `VPS_KNOWN_HOSTS` (mismos valores que en el backend).
3. GHCR: tras el primer `image`, en el paquete `bellidental-agent` → Package settings → visibilidad **Public**
   (como backend y frontend; el VPS no tiene `docker login`). Si se deja privado, `deploy` falla en `pull`: hacer
   público el paquete y re-ejecutar `deploy`.
4. PR `develop` → `main` y merge: `test` → `image` → `deploy` en verde; en el VPS `docker compose ps agent` →
   `healthy` y `https://bot.bellidentalv1.site/webhook` deja de dar 502.
5. Tras el webhook de Meta (`DEPLOY-SETUP.md` §7): escribir al número del bot →
   responde con el aviso de privacidad / menú.

## Resultado

**Archivos:** `Dockerfile` (modificado), `.dockerignore` (nuevo), `.github/workflows/ci-cd.yml` (nuevo).
`app/` sin cambios (`git status`: solo estos archivos y la propia tarea).

**Verificación del YAML:** `python3 -c "import yaml; yaml.safe_load(...)"` → `YAML OK jobs: ['test', 'image', 'deploy']`.

**Tests requeridos**
1. Build: `docker build -t bellidental-agent .` → `Successfully tagged bellidental-agent:latest`.
   Tamaño: `docker images` → `SIZE=205MB` (< 250 MB).
2. Run con `.env.example`: **FALLO en el código de la app, no en la imagen.** Con `docker run ... --env-file .env.example`
   el contenedor queda `unhealthy` y `curl localhost:8000/health` devuelve HTTP 000. Causa en los logs:
   `NameError: name 'DueReminder' is not defined` (`/app/app/backend/client.py`, línea 191), y tras corregirlo en una
   copia temporal, `NameError: name 'ReminderResponse' is not defined` (línea 205). `app/backend/client.py` usa
   `DueReminder` y `ReminderResponse` en anotaciones sin importarlos desde `app.backend.models`. En el `.venv` local
   (Python 3.14) no falla porque las anotaciones se evalúan de forma diferida; en la imagen (Python 3.13) sí. Mismo
   fallo previsible en CI (`test` usa Python 3.13). Corrección necesaria (fuera del alcance de 018b, no aplicada):
   añadir `DueReminder` y `ReminderResponse` al `from app.backend.models import (...)` de `client.py`.
   Verificación del Dockerfile con una copia temporal fuera del repo con esos dos imports añadidos:
   `HEALTH=healthy`, `HTTP 200` en `/health`, log `GET /health HTTP/1.1" 200 OK`. Contenedores y copia de prueba eliminados.
3. Caché: se añadió `# probe cache` a `app/main.py` y se reconstruyó. El paso
   `RUN python -c "import tomllib..." && pip install -r ...` salió `Using cache`; solo se reconstruyeron `COPY app/`
   y las capas siguientes. Después se revirtió con `git checkout -- app/main.py`.
4. `.venv/bin/pytest -q` → `23 passed, 1 warning in 0.57s`

**Supuestos y notas**
- El job `deploy` no incluye `actions/checkout` (no hace falta: no hay `scp`).
- `setup-python@v5` con `cache: pip` toma la clave de `pyproject.toml`.
- Sin `docker login` para el build local; el workflow usa `GITHUB_TOKEN`.

## Revisión
Estado: APROBADO

1. Corrección mínima aplicada por Claude: `app/backend/client.py` usaba `DueReminder` y `ReminderResponse` en
   anotaciones sin importarlos (`NameError` en Python 3.13; en 3.14 pasaba por evaluación diferida). Import añadido.
2. Verificado en la imagen final: `/health` = 200, contenedor `healthy`, 205 MB; `pytest -q` → `23 passed, 1 warning in 0.63s`.
3. Nota: el `.venv` local es Python 3.14 y el CI/imagen usan 3.13; el CI lo detectaría ahora en `test`.
