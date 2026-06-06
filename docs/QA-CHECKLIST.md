# ChronoFlow — QA Checklist

**QA run date:** 2026-06-03
**Environment:** Windows 10 Pro · Python 3.13.3 · Node 20 · Docker installed but daemon not running
**Branch:** main · commit 8747e59

---

## Legend
- `[x]` — Verified and passing in this QA run
- `[ ]` — Not verifiable in this environment (reason noted)
- `[!]` — Issue found and corrected in this QA run

---

## 1. Backend (apps/api — FastAPI + SQLAlchemy async)

### Test suite
- [x] **pytest 76/76 green** — `pytest --tb=short -q` from `apps/api/` using `.venv` and SQLite in-memory (no Postgres required). All tests pass in 2.3 s.
- [x] **Test isolation** — `conftest.py` uses `aiosqlite` in-memory DB per test; patches `AsyncSessionLocal` on all routes and the task manager.
- [x] **Async tests** — `pytest-asyncio` with `asyncio_mode=auto` in `pytest.ini`. No sync/async leaks.

### Linter (ruff)
- [!] **ruff.toml used `[tool.ruff]` / `[tool.ruff.lint]` headers** — Invalid in a standalone `ruff.toml` (correct for `pyproject.toml`). Fixed to top-level `[lint]` section.
- [!] **51 auto-fixable issues** — ruff `--fix` applied: import sort (I001), `timezone.utc` → `datetime.UTC` (UP017), `Callable/Coroutine` from `typing` → `collections.abc` (UP035), unused imports (F401), removed unused `sqlalchemy.event` import from `db/session.py`.
- [!] **4 manual F841 fixes** — Removed unused local variables: `taken_label` in `scheduler.py`, `node_by_id` in `validator.py`, `expected_max` in `test_engine.py`, `ctx` in `test_jsonpath_resolver.py`.
- [!] **F821 false positives** — SQLAlchemy forward-reference type hints (`Mapped[Workflow]`, `Mapped[list[WorkflowRun]]`) suppressed with `# noqa: F821` (already had `# type: ignore[name-defined]` for mypy). These are legitimate ORM patterns.
- [x] **ruff clean** — `ruff check app/ tests/` exits 0 after fixes.

### mypy
- [ ] **mypy not installed** — Not in `requirements.txt`, not in the venv. Cannot run static type checking. Recommend: add `mypy` + `types-*` stubs to dev requirements and run `mypy app/` in CI.

### Schema structure
- [x] **Models separated from schemas** — `app/models/` (SQLAlchemy ORM: `workflow.py`, `run.py`) and `app/schemas/` (Pydantic v2: `graph.py`, `workflow.py`, `run.py`) are separate packages, exactly as required.
- [x] **Pydantic v2** — All schemas use `model_config = ConfigDict(from_attributes=True)`, `BaseModel`, `model_dump()`, `model_validate()`.

### Secrets / config
- [x] **No hardcoded secrets** — All config via `pydantic_settings.BaseSettings` in `app/core/config.py`. DATABASE_URL, CORS_ORIGINS, ENV are environment variables.
- [x] **.env.example present** — Root `.env.example` documents all required environment variables.
- [x] **No .env committed** — Only `.env.example` exists; actual `.env` not in repo.

### Alembic migrations
- [x] **Alembic configured** — `alembic.ini` present, `alembic/env.py` exists, `alembic/versions/001_initial_schema.py` creates all three tables (`workflows`, `workflow_runs`, `execution_events`) with correct JSONB columns, indexes, and `UNIQUE (run_id, sequence)` constraint.
- [ ] **`alembic upgrade head` not verified** — Requires running Postgres. Verifiable via `docker compose up db -d && alembic upgrade head`.

### API /docs
- [x] **FastAPI /docs accessible** — Confirmed via introspection: routes include `/docs`, `/redoc`, `/openapi.json`. `docs_url="/docs"` set in `FastAPI(...)`.

---

## 2. Frontend (apps/web — React + Vite + TypeScript)

### Test suite
- [x] **Vitest 29/29 green** — `npm run test` passes all 4 test files (replayState, client, PayloadInspector, DebugNode) in < 5 s.
- [x] **Tests cover real behavior** — `replayState.test.ts` tests the time-travel core logic; `client.test.ts` tests HTTP error handling; component tests use `@testing-library/react`.

### TypeScript strict mode
- [x] **`strict: true`** in `tsconfig.app.json` — Plus `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`, `noUncheckedIndexedAccess`.
- [x] **`tsc -b` clean** — Production build (`npm run build`) runs `tsc -b` with zero type errors.

### ESLint
- [!] **8 ESLint errors found and fixed:**
  1. `client.ts` lines 66-67: `import.meta.env['VITE_API_URL']` typed as `any` — fixed with explicit `as string | undefined` cast.
  2. `useWorkflows.ts` line 39: floating promise from `qc.invalidateQueries()` — fixed with `void` operator.
  3. `PayloadInspector.tsx` line 32: unnecessary `as EventStatus` cast (already typed) — removed.
  4. `RunDebugger.tsx` line 102: unnecessary `as NodeType` cast (already typed) — removed + unused `NodeType` import removed.
  5. `vitest.config.ts`: not in `ignorePatterns`, triggering tsconfig mismatch error — added to `ignorePatterns` in `.eslintrc.cjs`.
- [x] **ESLint clean** — `npm run lint` exits 0 with `--max-warnings 0`.

### Prettier / formatting
- [ ] **Prettier not run** — `npm run format` script exists (Prettier configured) but not executed in this QA pass. No formatting issues observed manually; recommend running in CI pre-commit hook.

### Production build
- [x] **`npm run build` clean** — `tsc -b && vite build` succeeds: 282 modules transformed, output in `dist/`.

### Loading / Error / Empty states
- [x] **Loading state** — `<LoadingSpinner>` component used in all three pages (Workflows, Editor, RunDebugger).
- [x] **Error state** — `<ErrorBanner>` used on all data-fetch failure paths with `onRetry` callback where applicable.
- [x] **Empty state** — `<EmptyState>` component exists and is imported in `Workflows.tsx`.

### Responsive / viewports
- [ ] **Responsive not verified via Playwright** — Docker daemon was not running; E2E tests could not be executed. Playwright config covers 3 viewports: Desktop Chrome, iPad Pro 11, Pixel 7. Run after `docker compose up --build -d`.

---

## 3. Contract alignment: Backend Pydantic schemas vs Frontend TypeScript types

### Result: FULLY ALIGNED — no desalineaciones found

Compared `apps/api/app/schemas/` against `apps/web/src/types/api.ts` and the contract in `ARCHITECTURE.md §4`:

| Schema / Type | Backend (Pydantic) | Frontend (TypeScript) | Status |
|---|---|---|---|
| `NodeType` | `Literal["start","transform","http","delay","branch","end"]` | `'start'\|'transform'\|'http'\|'delay'\|'branch'\|'end'` | Aligned |
| `RunStatus` | `Literal["pending","running","completed","failed"]` | `'pending'\|'running'\|'completed'\|'failed'` | Aligned |
| `EventStatus` | `Literal["running","completed","failed","skipped"]` | `'running'\|'completed'\|'failed'\|'skipped'` | Aligned |
| `GraphNode` | `id:str, type:NodeType, position:NodePosition, data:NodeData` | `id:string, type:NodeType, position:{x,y}, data:{label,config}` | Aligned |
| `GraphEdge` | `id, source, target, data?:EdgeData(branch?)` | `id, source, target, data?:{branch?}` | Aligned |
| `Graph` | `nodes:list[GraphNode], edges:list[GraphEdge]` | `nodes:GraphNode[], edges:GraphEdge[]` | Aligned |
| `WorkflowIn` | `name:str, description?:str, graph:Graph` | `name:string, description?:string, graph:Graph` | Aligned |
| `WorkflowOut` | `id:UUID, name, description?, graph, created_at, updated_at` | `id:string, name, description?, graph, created_at, updated_at` | Aligned |
| `RunOut` | `id, workflow_id, status, trigger_payload, final_payload?, error?, started_at?, finished_at?` | Same fields, same optionality | Aligned |
| `ExecutionEventOut` | `id, run_id, node_id, sequence, status, input_snapshot, output?, error?, started_at, finished_at?, duration_ms?` | Same fields, same optionality | Aligned |
| `ValidationResult` | `valid:bool, errors:list[str], warnings:list[str]` | `valid:boolean, errors:string[], warnings:string[]` | Aligned |

### API route alignment

| Contract route | Backend route | Frontend call | Status |
|---|---|---|---|
| `GET /api/workflows` | `GET /api/workflows/` | `get('/workflows')` | Aligned |
| `POST /api/workflows` | `POST /api/workflows/` | `post('/workflows', data)` | Aligned |
| `GET /api/workflows/:id` | `GET /api/workflows/{workflow_id}` | `get('/workflows/${id}')` | Aligned |
| `PUT /api/workflows/:id` | `PUT /api/workflows/{workflow_id}` | `put('/workflows/${id}', data)` | Aligned |
| `DELETE /api/workflows/:id` | `DELETE /api/workflows/{workflow_id}` | `del('/workflows/${id}')` | Aligned |
| `POST /api/workflows/:id/validate` | `POST /api/workflows/{workflow_id}/validate` | `post('/workflows/${id}/validate')` | Aligned |
| `POST /api/workflows/:id/run` | `POST /api/workflows/{workflow_id}/run` | `post('/workflows/${id}/run', {trigger_payload})` | Aligned |
| `GET /api/runs?workflow_id=` | `GET /api/runs/` + `workflow_id` query param | `get('/runs?workflow_id=${id}')` | Aligned |
| `GET /api/runs/:id` | `GET /api/runs/{run_id}` | `get('/runs/${id}')` | Aligned |
| `GET /api/runs/:id/events` | `GET /api/runs/{run_id}/events` | `get('/runs/${id}/events')` | Aligned |
| `POST /api/runs/:id/replay` | `POST /api/runs/{run_id}/replay` | `post('/runs/${id}/replay')` | Aligned |
| `WS /api/ws/runs/:id` | `/api/ws/runs/{run_id}` (WebSocket) | `wsUrl('/ws/runs/${runId}')` | Aligned |

### WebSocket protocol alignment
- Backend sends `ExecutionEventOut` JSON per event, then `{"type":"run_finished","status":"..."}` on terminal.
- Frontend `useRunStream.ts` parses each message as `ExecutionEventOut`, deduplicates by `sequence + node_id`, sorts by sequence. It ignores messages that fail JSON parse (which includes the `run_finished` control message) — this is intentional and safe.

---

## 4. E2E (Playwright)

- [ ] **Docker daemon not running** — `docker ps` returns "failed to connect to docker API". `docker compose up --build -d` could not be executed.
- [x] **E2E test written** — `e2e/star-flow.spec.ts` covers the full star flow: `/` → create workflow → Editor → trigger Run modal → `/runs/:id` → wait for `completed` → scrubber visible → step through events → Payload Inspector updates → Replay button present.
- [x] **Playwright config written** — `e2e/playwright.config.ts` covers 3 viewports (Desktop Chrome, iPad Pro 11, Pixel 7), 60s timeout, retry on failure, trace/video/screenshot on failure.

### How to run E2E
```bash
# 1. Start the full stack (from repo root)
docker compose up --build -d

# 2. Wait for services (api health check)
curl http://localhost:8000/health

# 3. Install Playwright browsers (first time)
npx playwright install chromium

# 4. Run E2E
npx playwright test --config e2e/playwright.config.ts

# 5. View report
npx playwright show-report
```

---

## 5. Summary

| Area | Status | Notes |
|---|---|---|
| pytest 76 tests | PASS | 76/76 green |
| ruff linter | PASS (after fixes) | 51 auto-fixed + 4 manual + 2 noqa; now clean |
| mypy | NOT RUN | Not in requirements.txt; recommend adding |
| Vitest 29 tests | PASS | 29/29 green |
| ESLint | PASS (after fixes) | 8 errors fixed; now 0 warnings |
| TypeScript build | PASS | tsc -b + vite build clean |
| Contract alignment | PASS | All schemas and routes aligned; 0 desalineaciones |
| Loading/Error/Empty states | PASS | All three components present and used |
| Secrets in .env | PASS | pydantic-settings + .env.example |
| Alembic migrations | WRITTEN (not executed) | Postgres unavailable; script verified by inspection |
| /docs accessible | PASS | /docs, /redoc, /openapi.json in route list |
| E2E Playwright | WRITTEN (not executed) | Docker daemon not running; test + config in e2e/ |
| Responsive (3 viewports) | NOT RUN | Requires Docker; config targets 3 viewports |

---

## 6. Rutas de demo / smoke-test manual

Guía para validar a mano que todo funciona end-to-end (el README la referencia desde "Probalo en
2 minutos"). El backend siembra 3 workflows al arrancar, así que no hace falta crear nada para A–C.

Web: `:8080` (Docker) o `:5173` (dev). API docs: `:8000/docs`.

### Ruta A — Paralelismo (ready-set scheduler)
1. `/` → abrir **"Parallel Delays Demo"** → **Run** con `{}`.
2. Redirige a `/runs/:id`. Verificar duración total **~3s, no 4s**.
3. Scrubber: `delay-3s` y `delay-1s` arrancan en el mismo instante (paralelismo real).

### Ruta B — Branch + JSONPath + HTTP real
- Abrir **"Branch + Transform + HTTP"** (condición `$.trigger.amount > 100`):
  - Run `{"amount": 150}` → rama **true** → fetch HTTP real (`jsonplaceholder`) + normaliza con JSONPath.
  - Run `{"amount": 50, "note": "low"}` → rama **false** → `skip-transform`; la rama no tomada queda **podada** (`skipped`).

### Ruta C — Time-Travel + Replay
- Abrir **"Simple Pipeline"** → Run `{"user_id": 1, "action": "login"}`.
- En `/runs/:id`: mover el scrubber paso a paso, inspeccionar input/output por nodo (snapshots inmutables).
- Probar **Replay** → corrida idéntica desde el payload de disparo.

### Ruta D — Editor desde cero (regresión del fix v0.2.2)
- `/` → crear workflow nuevo → con la paleta armar `start → transform → end`.
- **Verificar que el nodo `start` aparece en la paleta** (antes faltaba; sin él era imposible pasar la regla 1 del validador).
- **Save** → **Run**. Debe completar.

### Ruta E — Manejo de errores (v0.2.1)
- Workflow sin `start` o vacío → **Run** → `ErrorBanner` con errores legibles (no `[object Object]`), **sin** POST `/run` que ensucie la consola con un `422`.
- Durante un run en vivo: consola del browser **sin** `Uncaught (in promise)` ni storm de reconexión de WebSocket.

### Ruta F — API directa (sin UI)
- `:8000/docs` (Swagger) → `GET /api/workflows` lista los 3 seed → `POST /api/workflows/:id/run` con un `trigger_payload` → `GET /api/runs/:id/events` muestra los `ExecutionEvent` ordenados por `sequence`.
