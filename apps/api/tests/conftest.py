"""Pytest configuration and shared fixtures.

Database strategy:
  We use SQLite in-memory (aiosqlite) for tests. This avoids the need for
  a running Postgres instance in CI and makes tests fast and hermetic.

  Trade-off: JSONB columns are declared with SQLAlchemy's generic `JSON` type,
  which maps to JSONB in Postgres and TEXT-serialized JSON in SQLite.
  All CRUD and engine logic works identically because SQLAlchemy abstracts
  the serialization. What we lose: JSONB-specific Postgres operators (e.g.
  @> containment queries) — but ChronoFlow doesn't use those in its queries.

  UUID columns: SQLAlchemy's UUID(as_uuid=True) maps to TEXT in SQLite.
  We patch the dialect for tests so UUID primary keys work as UUIDs.

  Note: The Alembic migration uses postgresql.JSONB and postgresql.UUID directly.
  For the test DB we create tables via Base.metadata.create_all() instead of
  running migrations, so we avoid Postgres-specific DDL.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import app

# ─── SQLite async engine for tests ───────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create a fresh in-memory SQLite engine per test."""
    eng = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # share the same connection across async tasks
    )
    # Create all tables from ORM metadata (bypasses Alembic for test speed)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture(scope="function")
async def session_factory(engine):
    """Return an async_sessionmaker bound to the test engine."""
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return factory


@pytest_asyncio.fixture(scope="function")
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test AsyncSession."""
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(engine, session_factory) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient for the FastAPI app wired to the test database.

    Overrides get_session dependency so all route handlers use the in-memory DB.
    """

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    # Also patch AsyncSessionLocal used by task_manager and routes for background tasks
    import app.api.routes.runs as runs_routes
    import app.api.routes.workflows as wf_routes
    import app.db.engine as db_engine_module

    original_factory = db_engine_module.AsyncSessionLocal
    db_engine_module.AsyncSessionLocal = session_factory
    wf_routes.AsyncSessionLocal = session_factory
    runs_routes.AsyncSessionLocal = session_factory

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # Restore overrides
    app.dependency_overrides.pop(get_session, None)
    db_engine_module.AsyncSessionLocal = original_factory
    wf_routes.AsyncSessionLocal = original_factory
    runs_routes.AsyncSessionLocal = original_factory
