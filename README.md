# ChronoFlow

> **Motor de workflows event-driven** basado en grafos acíclicos dirigidos (DAG), con
> **ejecución paralela asíncrona**, **expresiones JSONPath** para payloads dinámicos y
> **Time-Travel Debugging**: recorré, auditá y reproducí el estado histórico de cualquier
> ejecución, nodo por nodo.

[![demo](https://img.shields.io/badge/demo-live-brightgreen)](https://chronoflow.mateopavoni.com.ar/)
![stack](https://img.shields.io/badge/stack-React%20Flow%20·%20FastAPI%20·%20PostgreSQL%20·%20asyncio-2b2b2b)  ·  ![license](https://img.shields.io/badge/license-proprietary-red)

Stack: **React Flow · FastAPI · PostgreSQL · asyncio**

### 🔗 Demo en vivo

**[chronoflow.mateopavoni.com.ar](https://chronoflow.mateopavoni.com.ar/)** — registrate con cualquier
email (no hay verificación, es una demo) y tu cuenta arranca con **3 workflows de ejemplo** ya
cargados para explorar las features sin armar nada desde cero. Deployado en un VPS propio vía
**Dokku** (`apps/api` y `apps/web` como apps separadas), con deploy automático en cada push a
`main` (`.github/workflows/deploy.yml`).

### UI — "Conductor OS" (tema claro / oscuro)

| Time-Travel Debugger | Editor de DAG |
|---|---|
| ![Time-Travel Debugger](./docs/screenshots/debugger-dark.png) | ![Editor de DAG](./docs/screenshots/editor-dark.png) |

| Workflows Hub (oscuro) | Workflows Hub (claro) |
|---|---|
| ![Workflows oscuro](./docs/screenshots/workflows-dark.png) | ![Workflows claro](./docs/screenshots/workflows-light.png) |

---

## ¿Qué resuelve?

Las herramientas de automatización (Zapier, n8n, Airflow) ejecutan grafos de tareas, pero
depurar *por qué* una corrida produjo cierto resultado suele ser opaco. **ChronoFlow** trata
cada ejecución como una secuencia de **snapshots inmutables**: podés rebobinar la corrida y ver,
en cada instante, qué nodos corrieron, en qué orden (incluido el **paralelismo**) y con qué
payload de entrada/salida. Es un "debugger con viaje en el tiempo" para workflows.

**No es un CRUD con formularios.** El valor está en tres piezas de ingeniería real:

1. **Paralelismo real, no simulado** — el scheduler corre por *ready-set* (no por niveles): dos
   ramas independientes con `delay(3s)` y `delay(1s)` terminan en **~3s, no 4s**. Comprobable en
   la demo con un cronómetro.
2. **Time-Travel Debugging** sobre un log `ExecutionEvent` **append-only** — el scrubber no
   re-ejecuta nada, reconstruye el estado del DAG en cualquier instante a partir de snapshots
   inmutables. La función que lo hace es pura y está testeada.
3. **Seguridad tratada como feature, no como afterthought**: evaluador de condiciones propio
   (nunca `eval`), autorización por recurso con `owner_id` (un IDOR real se encontró y se cerró,
   documentado sin vueltas), guard anti-SSRF en el nodo `http`, rate limiting. Ver [`ARCHITECTURE.md`](./ARCHITECTURE.md) §7.

### Features
- **Editor visual de DAG** (React Flow): arrastrá nodos, conectá edges, configurá cada paso. Undo/redo, copy/paste, import/export JSON, auto-arrange.
- **Ejecución paralela asíncrona**: scheduler por *ready-set* — ramas independientes corren a la vez (dos `delay(3s)` y `delay(1s)` en paralelo ⇒ ~3s, no 4s).
- **Time-Travel Debugging**: timeline scrubber paso a paso sobre `ExecutionEvent` append-only.
- **Replay**: reproducí una corrida idéntica desde su payload de disparo.
- **Live**: seguimiento en vivo de la corrida por WebSocket.
- **Nodos**: `start · transform · http · delay · branch · end`.
- **Expresiones JSONPath** para mapear payloads entre nodos + plantillas en URLs/bodies.
- **Branches condicionales** con evaluador propio y **seguro** (sin `eval`).
- **Auth + multi-tenant**: registro/login con JWT en cookie httpOnly; cada cuenta ve solo sus propios workflows/runs (autorización por recurso, no solo gate de UI).
- **SSRF guard + rate limiting**: el nodo `http` bloquea IPs privadas/loopback/metadata de cloud; login/registro/runs están rate-limiteados.
- **UI "Conductor OS"**: estética Swiss Minimalist / consola industrial, con **tema claro/oscuro** (toggle persistido, respeta `prefers-color-scheme`) e íconos SVG (`lucide-react`).

### En números
**154 tests** (108 backend + 46 frontend) · **11 pull requests** mergeadas con revisión propia
(historial real, no un solo commit gigante) · deploy en producción con CI/CD propio · 0
desalineaciones en la auditoría de contrato front↔back.

---

## Arquitectura (resumen)

Monorepo de 3 componentes. El detalle —modelo de dominio, contrato de API, algoritmo del
scheduler y decisiones técnicas— está en **[`ARCHITECTURE.md`](./ARCHITECTURE.md)**.

```
chronoflow/
├── apps/
│   ├── web/   # React + Vite + TS + React Flow   (UI: editor + debugger)
│   └── api/   # FastAPI + SQLAlchemy 2.x async    (engine + REST + WS)
├── docker-compose.yml   # db + api + web
├── ARCHITECTURE.md      # contrato central
└── docs/                # capturas, diagramas
```

---

## Cómo correr

### Opción A — Docker (todo junto, recomendado)
```bash
cp .env.example .env
docker compose up --build
# web  → http://localhost:8080
# api  → http://localhost:8000/docs  (Swagger)
# db   → localhost:5432
```

### Opción B — Local (dev)
```bash
# Backend
cd apps/api
python -m venv .venv && .venv\Scripts\activate   # Unix: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload      # http://localhost:8000/docs

# Frontend (otra terminal)
cd apps/web
npm install
npm run dev                        # http://localhost:5173
```

---

## Probalo en 2 minutos

Andá a **[chronoflow.mateopavoni.com.ar](https://chronoflow.mateopavoni.com.ar/)** (o `:8080`/`:5173`
en local) y **registrate** con cualquier email — no hay verificación, es una demo. Al crear la
cuenta el backend **siembra 3 workflows de ejemplo** automáticamente. No hace falta armar nada
para ver las features clave:

**1. Paralelismo real** — abrí **"Parallel Delays Demo"** → **Run** con payload `{}`.
Dos `delay` (3s y 1s) corren a la vez: la corrida termina en **~3s, no 4s**. En `/runs/:id` movés
el **scrubber** y ves ambos nodos arrancar en el mismo instante.

**2. Branch + JSONPath + HTTP** — abrí **"Branch + Transform + HTTP"** (condición `$.trigger.amount > 100`):
| Payload de disparo | Qué pasa |
|---|---|
| `{"amount": 150}` | rama **true** → fetch HTTP real + normaliza con JSONPath |
| `{"amount": 50, "note": "low"}` | rama **false** → pasa derecho (ves la **poda** de la rama no tomada) |

**3. Time-Travel** — abrí **"Simple Pipeline"** → **Run** con `{"user_id": 1, "action": "login"}`.
En `/runs/:id` recorré los **snapshots inmutables** por nodo (input/output en cada paso) y probá **Replay**.

**4. Editor desde cero** — desde el hub creás un workflow y armás el grafo con la paleta de la izquierda:
`start → … → end`. Recordá la regla del validador: **exactamente un `start`** y al menos un `end`.

> Guía de pruebas exhaustiva (rutas de smoke-test, errores esperados, WS en vivo): **[`docs/QA-CHECKLIST.md`](./docs/QA-CHECKLIST.md)**.

---

## Tests
```bash
cd apps/api && pytest        # 108 tests: engine (paralelismo, ciclos, JSONPath, time-travel),
                              # auth, autorización (IDOR), SSRF guard, endpoints
cd apps/web && npm run test  # 46 tests: Vitest (lib puras, cliente API, componentes)
npx playwright test --config e2e/playwright.config.ts  # crear → run → time-travel, 3 viewports (requiere stack levantado)
```

---

## Limitaciones conocidas
- El task manager es **in-process** (`asyncio.create_task`): ideal para la demo, no sobrevive
  reinicios ni escala multi-worker. En producción se reemplaza por una cola durable (Arq/Celery + Redis).
- El nodo `http` es **no-determinista** en *replay* (depende de un servicio externo).

---

## Licencia

© 2026 Mateo Pavoni. Todos los derechos reservados. Software propietario, publicado solo con
fines de evaluación/portfolio. Prohibida su copia, redistribución o reuso sin autorización
escrita. Ver [LICENSE](./LICENSE).


