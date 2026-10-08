# Estado actual (2026-10-08)

- **FACT** `pytest`: 118 pasan (un test dependía de DNS real a `example.com`; ahora mockea `getaddrinfo`).
- **FACT** Frontend: 47 tests pasan; el build de producción compila.
- **FACT** Stack real (compose): web 200, `/docs` 200. Registro + 3 workflows sembrados; "Parallel Delays Demo" completa en 3.2s.
- **FACT** IDOR: usuario B recibe 404 al leer/borrar workflow, run y events de A. Sin sesión: `/me` → 401.
- **FACT** Rate limit de login: 10 intentos fallidos devuelven 401, del 11º en adelante 429.
- **FACT** Playwright e2e no se re-ejecutó en esta pasada (no se verificó).
