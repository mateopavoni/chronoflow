# Proyecto

- **FACT** Motor de workflows event-driven sobre DAG, con ejecución paralela asíncrona, expresiones JSONPath y Time-Travel Debugging (replay de snapshots por nodo).
- **FACT** Stack: React + Vite + TS + React Flow (`apps/web`), FastAPI + SQLAlchemy 2 async + Alembic (`apps/api`), PostgreSQL 16.
- **FACT** Estado: **archivado** (2026-10-08). El deploy en Dokku/VPS fue dado de baja; se corre en local con `docker compose up --build` (web `127.0.0.1:8080`, API `127.0.0.1:8000`).
- **FACT** Autor: Mateo Pavoni (`mateopavoni`). Licencia propietaria, solo evaluación/portfolio.
- **INFERENCE** Pensado como pieza de portfolio: el valor está en el scheduler, el time-travel y la seguridad, no en el CRUD.
