# Roadmap (si se retoma)

1. Cola durable para runs (Arq/Celery + Redis) en lugar de `asyncio.create_task`.
2. Pub/sub y rate limit compartidos (Redis) para multi-worker.
3. Correr Playwright en CI contra el stack de compose.
4. Nodos adicionales (p. ej. `loop`, `webhook` trigger).
5. Replay determinista del nodo `http` (grabar/reproducir respuestas).
