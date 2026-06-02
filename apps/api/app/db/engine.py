"""Async SQLAlchemy engine and session factory.

Using SQLAlchemy 2.x with asyncpg driver. All I/O is non-blocking.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# echo=True in dev so all SQL is visible in logs — helps with debugging and demos
_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.is_dev,
    pool_pre_ping=True,  # detect stale connections before use
)

AsyncSessionLocal = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # avoid lazy-load errors after commit in async context
)


def get_engine():
    """Return the engine (used by Alembic env.py and tests)."""
    return _engine
