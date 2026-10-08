# Convenciones

- **FACT** Todo local: `docker compose up --build`. Sin JDK/Python/Node asumidos en el host para correr tests; se usaron contenedores (`python:3.11-slim`, `node:20-alpine`).
- **FACT** Tests: `apps/api` → `pytest` (118); `apps/web` → `npm test` (47) y `npm run build`; e2e → `npx playwright test --config e2e/playwright.config.ts` (requiere stack levantado).
- **FACT** CI: `.github/workflows/ci.yml` (api + web). Existe además `guard-coauthor.yml`.
- **FACT** Commits como `Mateo Pavoni <mateopavoni905@gmail.com>`, sin trailers de Claude.
- **FACT** Mensajes de commit estilo convencional (`fix:`, `feat:`, `docs:`, `chore:`).
