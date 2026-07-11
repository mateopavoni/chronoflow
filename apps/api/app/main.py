"""ChronoFlow API — FastAPI application entry point.

Mounts:
  /api/workflows  → workflow CRUD + validate + run
  /api/runs       → run status + events + replay
  /api/ws         → WebSocket live streaming

Startup (lifespan):
  - Seeds example workflows (idempotent).
  Run Alembic migrations separately before starting: `alembic upgrade head`
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chronoflow")


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: runs before first request and on shutdown.

    Note: example workflows used to be seeded here, globally, once. That no
    longer fits the ownership model (workflows are per-user, see
    app/models/workflow.py `owner_id`) — each new account now gets its own
    copy of the 3 examples on POST /api/auth/register instead (see
    app/services/seed.py + app/api/routes/auth.py).
    """
    logger.info("Startup complete.")
    yield  # Application runs here
    logger.info("Shutting down ChronoFlow API.")


# ─── App factory ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="ChronoFlow API",
    description=(
        "DAG-based workflow engine with async parallel execution, "
        "JSONPath expressions, and Time-Travel Debugging."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Security headers ──────────────────────────────────────────────────────────


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Baseline security headers. HSTS only in prod (https)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not settings.is_dev:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ─── Routers ──────────────────────────────────────────────────────────────────

from app.api.routes import (  # noqa: E402
    auth,
    runs,
    workflows,
    ws,  # noqa: E402
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(ws.router, prefix="/api/ws", tags=["websocket"])


# ─── Health check ─────────────────────────────────────────────────────────────


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "chronoflow-api"}
