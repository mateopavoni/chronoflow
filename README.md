# ChronoFlow

> **Motor de workflows event-driven** basado en grafos acíclicos dirigidos (DAG), con
> **ejecución paralela asíncrona**, **expresiones JSONPath** para payloads dinámicos y
> **Time-Travel Debugging**: recorré, auditá y reproducí el estado histórico de cualquier
> ejecución, nodo por nodo.

![stack](https://img.shields.io/badge/stack-React%20Flow%20·%20FastAPI%20·%20PostgreSQL%20·%20asyncio-2b2b2b)  ·  ![license](https://img.shields.io/badge/license-MIT-blue)
<!-- Cuando haya deploy: reemplazar por [![demo](https://img.shields.io/badge/demo-live-brightgreen)](URL_REAL) -->

Stack: **React Flow · FastAPI · PostgreSQL · asyncio**

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

### Features
- **Editor visual de DAG** (React Flow): arrastrá nodos, conectá edges, configurá cada paso.
- **Ejecución paralela asíncrona**: scheduler por *ready-set* — ramas independientes corren a la vez (dos `delay(3s)` y `delay(1s)` en paralelo ⇒ ~3s, no 4s).
- **Nodos**: `start · transform · http · delay · branch · end`.
- **Expresiones JSONPath** para mapear payloads entre nodos + plantillas en URLs/bodies.
- **Branches condicionales** con evaluador propio y **seguro** (sin `eval`).
- **Time-Travel Debugging**: timeline scrubber paso a paso sobre `ExecutionEvent` append-only.
- **Replay**: reproducí una corrida idéntica desde su payload de disparo.
- **Live**: seguimiento en vivo de la corrida por WebSocket.
- **UI "Conductor OS"**: estética Swiss Minimalist / consola industrial, con **tema claro/oscuro** (toggle persistido, respeta `prefers-color-scheme`) e íconos SVG (`lucide-react`).

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

Al levantar, el backend **siembra 3 workflows de ejemplo** automáticamente. No hace falta crear nada
para ver las features clave. Entrá a la web (`:8080` con Docker, `:5173` en dev) y:

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
cd apps/api && pytest        # engine (paralelismo, ciclos, JSONPath, time-travel) + endpoints
cd apps/web && npm run test  # Vitest (componentes + hooks)
```

---

## Limitaciones conocidas
- El task manager es **in-process** (`asyncio.create_task`): ideal para la demo, no sobrevive
  reinicios ni escala multi-worker. En producción se reemplaza por una cola durable (Arq/Celery + Redis).
- El nodo `http` es **no-determinista** en *replay* (depende de un servicio externo).

---

## Changelog
| Versión | Fecha | Cambio |
|---------|-------|--------|
| v0.1.0  | 2026-06-03 | Scaffold del monorepo + arquitectura + documentación inicial |
| v0.1.1  | 2026-06-04 | Fixes de arranque en Docker: path de Alembic, exclusión de tests del build de producción del front, y buffers de header de nginx (cookies grandes de localhost). Stack verificado end-to-end (`docker compose up`) |
| v0.2.0  | 2026-06-06 | Restyle al design system **Conductor OS** (Swiss Minimalist): **tema claro/oscuro** con tokens semánticos (CSS vars), íconos `lucide-react` (sin emojis), tabla de alta densidad, nodos e inspector estilo consola. ESLint con typed-linting de tests. Re-verificado con build fresco + smoke test |
| v0.2.1  | 2026-06-08 | Fixes de UX de errores: el cliente API formatea `detail` estructurado (`{message, errors}`) y errores de Pydantic en vez de mostrar `[object Object]` (p.ej. runear un grafo sin nodos ahora lista los errores de validación reales). Los handlers (`run`/`save`/`validate`/`replay`) capturan la rejección de `mutateAsync` → no más `Uncaught (in promise) ApiError` en consola. **Run ahora guarda el canvas antes de ejecutar** (Run corre el grafo guardado: sin esto se ejecutaba un grafo viejo/vacío y daba un 422 confuso por nodos que sí estaban en pantalla). **Pre-validación en el cliente** (vacío / sin start / sin end) antes de llamar a `/run`: un grafo obviamente no ejecutable muestra el mensaje al instante, sin disparar el POST que ensuciaba la consola con un `422`. WebSocket más robusto: no reinyecta frames de control (`run_finished`/`error`) como eventos —evita corromper el timeline— y no reconecta en cierres de aplicación (`4xxx`, p.ej. run inexistente) —corta el storm de reconexión— |
| v0.2.2  | 2026-06-08 | **Fix: el nodo `start` faltaba en la paleta** del editor → era imposible construir un workflow desde cero (el validador exige exactamente un `start`, pero la UI no dejaba agregarlo; solo funcionaba editando los workflows seed). Agregado a `NodePalette`. Documentación: sección **"Probalo en 2 minutos"** (guía sobre los 3 workflows seed), `LICENSE` MIT y badges de stack/licencia |
| v0.2.3  | 2026-06-08 | **Editor con atajos de teclado**: `Ctrl+Z`/`Ctrl+Shift+Z` (deshacer/rehacer sobre un historial de hasta 50 snapshots), `Ctrl+C`/`Ctrl+X`/`Ctrl+V` (copiar/cortar/pegar nodos + sus edges internos, con ids nuevos y offset) y `Supr`/`Backspace` (borrar selección). Botones Undo/Redo en la toolbar. Lógica de clipboard extraída a `lib/clipboard.ts` (pura, +6 tests). Fix de lint pre-existente en `useRunStream.ts` (aserción `as string` redundante). **UI consolidada 100% en inglés** (mensajes del `precheckGraph` + tooltips Undo/Redo que estaban en español) — convención: UI en inglés, docs en español |
| v0.2.4  | 2026-06-08 | **Borrar workflow ahora es un modal in-app**, no el `window.confirm` del navegador (muestra el nombre, maneja error de borrado y estado pending). **Multi-selección con `Shift`+click** en el canvas (`multiSelectionKeyCode`), unificada con el box-select de `Shift`+arrastre; el Shift+click ya no abre el drawer de config para no pisar el gesto de selección |
| v0.2.5  | 2026-06-08 | **Cambio de tipografía**: se reemplaza el dúo `Inter` + `JetBrains Mono` (el default genérico de mil dashboards) por la superfamilia **IBM Plex Sans + IBM Plex Mono**, más coherente con el aesthetic *industrial console* de Conductor OS y con más carácter propio. Tocado en `index.css` (import de Google Fonts + `body` + `react-flow__edge-text`) y `tailwind.config.js` (`fontFamily.sans`/`.mono`) |

---

## Licencia

[MIT](./LICENSE) © Mateo Pavoni


