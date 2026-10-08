# Problemas conocidos

- **FACT** El task manager es in-process (`asyncio.create_task`): no sobrevive reinicios ni escala a multi-worker.
- **FACT** El nodo `http` es no-determinista en *replay*.
- **FACT** Abrir la web en `localhost` en vez de `127.0.0.1` rompe la sesión (cookie `SameSite=Lax` entre sitios distintos).
- **FACT** El pub/sub es por proceso. **INFERENCE** el rate limiter también (su docstring menciona workers/réplicas).
- **INFERENCE** Sin cola durable, un run en curso se pierde si el contenedor de la API se reinicia.
- **FACT** GitHub puede conservar secrets `DOKKU_*` del deploy anterior; no se borraron (no autorizado).
