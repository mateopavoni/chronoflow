# Decisiones

- **FACT** Scheduler por ready-set en vez de por niveles: ramas independientes no se bloquean entre sí.
- **FACT** Log de eventos append-only: el debugger no depende de re-ejecutar (el nodo `http` es no-determinista).
- **FACT** Evaluador de condiciones propio, nunca `eval`.
- **FACT** Autorización por recurso (`owner_id`) en cada ruta REST y en el WS; recurso ajeno responde 404 indistinguible de inexistente.
- **FACT** Guard anti-SSRF en el nodo `http`: bloquea IPs privadas/loopback/metadata (verificado: `169.254.169.254` → run `failed`, "non-public address — blocked").
- **FACT** Sesión por JWT en cookie `httponly`, `SameSite=Lax`; con `ENV!=dev` la app no arranca con el `JWT_SECRET` por defecto.
- **FACT** Postgres no se publica al host en compose; los servicios tienen `mem_limit` (db 256m, api 384m, web 64m) pensando en máquinas con poca RAM.
