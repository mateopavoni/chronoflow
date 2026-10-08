# Arquitectura (resumen; detalle en /ARCHITECTURE.md)

- **FACT** Monorepo: `apps/web` (editor + debugger), `apps/api` (REST `/api/*`, WebSocket `/api/ws/runs/{id}`, engine), `e2e/` (Playwright).
- **FACT** Engine: scheduler por *ready-set* (no por niveles). Dos `delay` de 3s y 1s en paralelo terminan en ~3s; medido 3.2s contra el stack real.
- **FACT** Time-travel: log `ExecutionEvent` append-only; el scrubber reconstruye estado desde snapshots, no re-ejecuta.
- **FACT** Live: la API publica eventos por pub/sub in-process (`services/task_manager.py`) y el WS los reenvía; suscribe antes de leer la DB para no perder eventos.
- **FACT** Rutas: `/api/auth/{register,guest,login,logout,me}`, `/api/workflows/*` (CRUD, validate, run), `/api/runs/*` (get, events, replay), `/health`.
- **FACT** Las migraciones corren al arrancar el contenedor de la API (`alembic upgrade head` en el CMD del Dockerfile).
