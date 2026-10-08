# Dominio

- **FACT** Entidades: `User`, `Workflow` (con `owner_id`), `WorkflowRun`, `ExecutionEvent`.
- **FACT** Nodos: `start · transform · http · delay · branch · end`. El validador exige exactamente un `start` y al menos un `end`.
- **FACT** Un nodo del grafo se serializa con `id`, `type`, `position` y `data` (con `config` adentro); sin `position`/`data` la API responde 422.
- **FACT** Al registrarse, cada cuenta recibe 3 workflows sembrados: "Simple Pipeline", "Branch + Transform + HTTP", "Parallel Delays Demo".
- **FACT** Branch usa un evaluador de condiciones propio (sin `eval`); las ramas no tomadas se podan.
