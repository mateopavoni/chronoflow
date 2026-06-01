# ChronoFlow — Arquitectura

> Motor de workflows event-driven basado en **DAG** (grafo acíclico dirigido) con
> **ejecución paralela asíncrona**, **expresiones JSONPath** para payloads dinámicos y
> **Time-Travel Debugging**: cada nodo deja un snapshot inmutable que permite recorrer,
> auditar y reproducir el estado histórico de una ejecución, paso a paso.

Este documento es el **contrato central** del proyecto. Define el modelo de dominio, el
contrato de API y el comportamiento del motor. Tanto el backend como el frontend se construyen
contra esta especificación.

---

## 1. Visión general (componentes)

```
                    ┌─────────────────────────────────────────┐
                    │            apps/web (React + Vite)        │
                    │  ┌──────────┐  ┌────────┐  ┌───────────┐ │
                    │  │ Editor   │  │ Runs   │  │ Time-Travel│ │
                    │  │ React    │  │ list   │  │ Debugger   │ │
                    │  │ Flow     │  │        │  │ (scrubber) │ │
                    │  └──────────┘  └────────┘  └───────────┘ │
                    └───────────────┬───────────────┬──────────┘
                              REST  │           WS   │
                    ┌───────────────▼───────────────▼──────────┐
                    │            apps/api (FastAPI)             │
                    │  routes → services → engine               │
                    │  ┌──────────────────────────────────────┐│
                    │  │ Execution Engine (asyncio scheduler)  ││
                    │  │  · topo-sort + ready-set concurrente  ││
                    │  │  · JSONPath resolver                  ││
                    │  │  · ExecutionEvent (time-travel log)   ││
                    │  └──────────────────────────────────────┘│
                    └───────────────┬───────────────────────────┘
                              async  │ SQLAlchemy 2.x (asyncpg)
                    ┌───────────────▼───────────────────────────┐
                    │            PostgreSQL  (JSONB)             │
                    │  workflows · workflow_runs · exec_events   │
                    └────────────────────────────────────────────┘
```

| Componente | Stack | Carpeta |
|------------|-------|---------|
| Frontend | React 18 + Vite + TypeScript + React Flow + React Query + Tailwind | `apps/web/` |
| Backend | FastAPI + SQLAlchemy 2.x async + asyncpg + Pydantic v2 + jsonpath-ng | `apps/api/` |
| DB | PostgreSQL 16 (columnas JSONB) | vía `docker-compose` |
| Orquestación | docker-compose (db + api + web) | raíz |

---

## 2. Modelo de dominio (DAG)

Un **Workflow** es un grafo `{ nodes, edges }` (formato compatible con React Flow).

### Nodo
```jsonc
{
  "id": "node-1",            // string único dentro del workflow
  "type": "transform",       // ver tipos abajo
  "position": { "x": 0, "y": 0 },  // para React Flow (no afecta ejecución)
  "data": {
    "label": "Normalizar",
    "config": { /* específico del tipo */ }
  }
}
```

### Tipos de nodo (`type`)
| type | Qué hace | `config` | Output |
|------|----------|----------|--------|
| `start` | Punto de entrada. Único por workflow. | `{}` | el `trigger_payload` de la corrida |
| `transform` | Construye un objeto nuevo mapeando rutas JSONPath del contexto. | `{ "mappings": { "outKey": "$.node-x.field", ... } }` | objeto con las claves mapeadas |
| `http` | Request HTTP async real (httpx). Demuestra I/O concurrente. | `{ "method": "GET", "url": "https://...", "headers": {}, "body": {} }` (url/body admiten plantillas JSONPath `${$.node.x}`) | `{ "status": int, "body": <json> }` |
| `delay` | `asyncio.sleep(seconds)`. Demuestra paralelismo (ramas paralelas terminan en el máximo, no en la suma). | `{ "seconds": number }` | `{ "waited": seconds }` |
| `branch` | Evalúa una condición JSONPath y enruta. | `{ "condition": "$.node-x.value > 10" }` | `{ "result": bool }` |
| `end` | Nodo terminal. Recolecta el payload final. | `{}` | el contexto acumulado (o un subset mapeado) |

### Edge
```jsonc
{
  "id": "edge-1",
  "source": "node-1",
  "target": "node-2",
  "data": { "branch": "true" }   // solo en edges que salen de un `branch`: "true" | "false"
}
```

### Reglas de validación del grafo
1. Exactamente **un** nodo `start`.
2. Al menos un nodo `end`.
3. **Acíclico** (DFS / Kahn detecta ciclos → 422).
4. Todos los nodos (salvo `start`) deben ser alcanzables desde `start`.
5. Cada `branch` debe tener edges salientes etiquetados `"true"` y `"false"`.
6. Las referencias JSONPath a nodos deben apuntar a nodos existentes (warning, no error duro).

---

## 3. Motor de ejecución (el corazón)

Archivo: `apps/api/app/engine/`.

### Algoritmo — scheduler asíncrono por ready-set
No se ejecuta "nivel por nivel" (eso serializa ramas desparejas). Se usa un **scheduler basado en
conjunto de listos**:

1. Validar el grafo (ver §2). Construir mapa de predecesores/sucesores e in-degree.
2. `ready = { nodos con in-degree 0 }` (= `start`).
3. Bucle: lanzar **todos** los nodos `ready` como `asyncio.Task` **en paralelo**.
   Esperar con `asyncio.wait(..., FIRST_COMPLETED)`.
4. Cuando un nodo termina: persistir su `ExecutionEvent`, guardar su output en el `context`,
   decrementar in-degree de sus sucesores. Los que llegan a 0 entran a `ready`.
5. **Branch:** al resolver, solo se "satisface" el edge cuyo `data.branch` coincide con el
   resultado. La rama no tomada se **poda**: sus nodos quedan `skipped` (se registra event `skipped`).
6. Termina cuando no quedan nodos `ready` ni en ejecución. Estado final del run = `completed`
   (o `failed` si algún nodo lanzó y no hay manejo).

> Resultado visible en demo: dos ramas con `delay(3s)` y `delay(1s)` en paralelo → el run
> total tarda ~3s, no 4s. Es la prueba tangible del paralelismo asíncrono.

### Contexto y JSONPath
- `context` es un dict: `context[node_id] = output_del_nodo`. Además `context["trigger"]` = payload de disparo.
- Las expresiones JSONPath (`jsonpath-ng`) se evalúan **contra `context`**.
  Ej: `$.fetch-user.body.name`, `$.trigger.amount`.
- Plantillas en strings (`http.url`, `http.body`): `${$.node.field}` se sustituye por el valor resuelto.
- `branch.condition`: extracción JSONPath + operador de comparación. Operadores soportados:
  `> < >= <= == !=` y `&&` / `||`. Evaluador **propio y acotado** (NO `eval`): se parsea la
  expresión, se resuelven los JSONPath y se comparan valores. Defendible y seguro.

### Time-Travel: ExecutionEvent
Cada transición de nodo escribe una fila inmutable (append-only):

```
ExecutionEvent(
  run_id, node_id, sequence,        # sequence = orden global monótono dentro del run
  status,                           # running | completed | failed | skipped
  input_snapshot,                   # copia del context relevante AL EMPEZAR el nodo (JSONB)
  output,                           # output del nodo (JSONB, null si running/failed/skipped)
  error,                            # mensaje si failed
  started_at, finished_at, duration_ms
)
```

- **Auditar:** `GET /runs/{id}/events` devuelve la lista ordenada por `sequence`.
- **Time-travel (scrubber):** el frontend reconstruye el estado del DAG en el instante `k`
  aplicando los eventos `0..k` (qué nodos están done/running/skipped y con qué payload).
  No requiere re-ejecutar: es replay de estado sobre snapshots inmutables.
- **Reproducir:** `POST /runs/{id}/replay` crea una corrida nueva con el **mismo** workflow y
  `trigger_payload`. Determinista para `transform`/`delay`/`branch`; `http` se documenta como
  no-determinista (caveat honesto en README).

### Background tasks
El run se dispara con `asyncio.create_task` (vía `BackgroundTasks`/task manager propio).
La respuesta de `POST .../run` es inmediata (`202` + `run_id`); el progreso llega por
`GET /runs/{id}` (polling) o por WebSocket `/ws/runs/{id}` (push en vivo).

---

## 4. Contrato de API REST  (prefijo `/api`)

### Workflows
| Método | Ruta | Body | Respuesta |
|--------|------|------|-----------|
| GET | `/api/workflows` | — | `WorkflowOut[]` |
| POST | `/api/workflows` | `WorkflowIn` | `WorkflowOut` (201) |
| GET | `/api/workflows/{id}` | — | `WorkflowOut` |
| PUT | `/api/workflows/{id}` | `WorkflowIn` | `WorkflowOut` |
| DELETE | `/api/workflows/{id}` | — | 204 |
| POST | `/api/workflows/{id}/validate` | — | `ValidationResult` |
| POST | `/api/workflows/{id}/run` | `{ "trigger_payload": object }` | `RunOut` (202) |

> **Errores de `/run`:** si el grafo no valida, responde `422` con
> `detail = { "message": string, "errors": string[] }` (no un string plano). El cliente front
> aplana ese shape (y los arrays de error de Pydantic) a texto legible — ver `apps/web/src/api/client.ts`.

### Runs
| Método | Ruta | Body | Respuesta |
|--------|------|------|-----------|
| GET | `/api/runs?workflow_id={id}` | — | `RunOut[]` |
| GET | `/api/runs/{id}` | — | `RunOut` |
| GET | `/api/runs/{id}/events` | — | `ExecutionEventOut[]` (ordenado por sequence) |
| POST | `/api/runs/{id}/replay` | — | `RunOut` (202, nueva corrida) |
| WS | `/api/ws/runs/{id}` | — | stream de `ExecutionEventOut` en vivo |

> **Frames del WS:** además de los `ExecutionEventOut`, el server emite frames de **control** por el
> mismo socket: `{ "type": "run_finished", "status": RunStatus }` al terminar y `{ "error": string }`
> si el run no existe (seguido de cierre con código `4004`). El cliente los distingue por forma y
> **no** los almacena como eventos. Cierres `4xxx` son de aplicación (intencionales) → el cliente no
> reconecta; sólo reintenta ante caídas transitorias (p.ej. `1006`).

### Schemas (Pydantic v2 → tipos TS espejados en `apps/web/src/types`)
```ts
type NodeType = "start" | "transform" | "http" | "delay" | "branch" | "end";
type RunStatus = "pending" | "running" | "completed" | "failed";
type EventStatus = "running" | "completed" | "failed" | "skipped";

interface GraphNode { id: string; type: NodeType; position: {x:number;y:number};
                      data: { label: string; config: Record<string, unknown> }; }
interface GraphEdge { id: string; source: string; target: string;
                      data?: { branch?: "true" | "false" }; }
interface Graph { nodes: GraphNode[]; edges: GraphEdge[]; }

interface WorkflowIn  { name: string; description?: string; graph: Graph; }
interface WorkflowOut { id: string; name: string; description?: string; graph: Graph;
                        created_at: string; updated_at: string; }

interface RunOut { id: string; workflow_id: string; status: RunStatus;
                   trigger_payload: object; final_payload?: object | null;
                   error?: string | null; started_at?: string | null;
                   finished_at?: string | null; }

interface ExecutionEventOut { id: string; run_id: string; node_id: string; sequence: number;
                   status: EventStatus; input_snapshot: object; output?: object | null;
                   error?: string | null; started_at: string; finished_at?: string | null;
                   duration_ms?: number | null; }

interface ValidationResult { valid: boolean; errors: string[]; warnings: string[]; }
```

---

## 5. Esquema de base de datos (SQLAlchemy 2.x async + Alembic)

```
workflows
  id           UUID  PK
  name         TEXT  NOT NULL
  description  TEXT
  graph        JSONB NOT NULL        -- { nodes, edges }
  created_at   TIMESTAMPTZ
  updated_at   TIMESTAMPTZ

workflow_runs
  id              UUID  PK
  workflow_id     UUID  FK -> workflows(id) ON DELETE CASCADE
  status          TEXT  NOT NULL        -- pending|running|completed|failed
  trigger_payload JSONB NOT NULL
  final_payload   JSONB
  error           TEXT
  started_at      TIMESTAMPTZ
  finished_at     TIMESTAMPTZ

execution_events                          -- append-only (time-travel)
  id             UUID  PK
  run_id         UUID  FK -> workflow_runs(id) ON DELETE CASCADE
  node_id        TEXT  NOT NULL
  sequence       INT   NOT NULL           -- orden global dentro del run
  status         TEXT  NOT NULL           -- running|completed|failed|skipped
  input_snapshot JSONB NOT NULL
  output         JSONB
  error          TEXT
  started_at     TIMESTAMPTZ NOT NULL
  finished_at    TIMESTAMPTZ
  duration_ms    INT
  UNIQUE (run_id, sequence)
  INDEX (run_id, sequence)
```

Modelos ORM en `app/models/`, **separados** de los schemas Pydantic en `app/schemas/`.

---

## 6. Frontend (apps/web)

| Ruta | Vista | Contenido |
|------|-------|-----------|
| `/` | Workflows | Lista de workflows (cards) + crear nuevo |
| `/workflows/:id` | Editor | Canvas React Flow, paleta de nodos, drawer de config por nodo, botón **Run** (abre modal de trigger payload) |
| `/runs/:id` | **Time-Travel Debugger** | DAG en React Flow coloreado por estado **en el instante k**; timeline scrubber (◀ paso a paso ▶); inspector de input/output del nodo seleccionado; modo "live" vía WebSocket mientras la corrida está `running`; botón **Replay** |

- **Estado servidor:** React Query (cache, polling de runs `running`).
- **WebSocket:** hook `useRunStream(runId)` que mergea eventos en vivo al store de la vista.
- **Estados:** loading / error / vacío en toda vista con datos.
- **Tipos:** `apps/web/src/types/api.ts` espeja los schemas de §4 (fuente de verdad: el backend).

---

## 7. Decisiones y trade-offs (defendibilidad)

| Decisión | Por qué | Trade-off |
|----------|---------|-----------|
| Scheduler por **ready-set** (no por niveles) | Paralelismo real en ramas desparejas | Más complejo que un topo-sort plano |
| **Time-travel sobre snapshots inmutables** (no re-ejecución) | Auditoría barata y determinista; el scrubber es O(eventos) | Costo de almacenamiento JSONB por evento |
| Evaluador de condiciones **propio** (no `eval`) | Seguridad: nunca ejecutar strings arbitrarios | Subset acotado de expresiones |
| **SQLAlchemy async + asyncpg** | Coherente con el motor asyncio; no bloquea el event loop | API async de SQLAlchemy 2.x tiene curva |
| **JSONB** para graph/payloads | Flexibilidad de esquema + consultable en Postgres | Menos integridad referencial que tablas normalizadas |
| Background con `asyncio.create_task` (in-process) | Simple, suficiente para demo; el motor ya es async | No sobrevive reinicios / no escala a multi-worker (caveat: en prod iría Celery/Arq) |
| Monorepo `apps/web` + `apps/api` | Un repo, contratos cerca, demo end-to-end | Tooling mixto (npm + pip) |

> **Caveat de producción honesto:** el task manager es in-process (para la demo). En producción
> se reemplazaría por una cola durable (Arq/Celery + Redis). Está documentado, no escondido.

---

## 8. Cómo se comunica todo (flujo end-to-end)

1. Usuario diseña el DAG en el **Editor** (React Flow) → `POST /api/workflows`.
2. Dispara una corrida con un payload → `POST /api/workflows/{id}/run` → `202 { run_id }`.
3. El backend lanza el run como `asyncio.Task`; el **engine** ejecuta nodos por ready-set,
   resolviendo JSONPath y escribiendo un `ExecutionEvent` por transición.
4. El frontend abre `/runs/{id}`: recibe eventos en vivo por **WebSocket** y, al terminar,
   permite **time-travel** con el scrubber sobre los `ExecutionEvent` persistidos.
5. **Replay** crea una corrida nueva e idéntica para reproducir el estado.
