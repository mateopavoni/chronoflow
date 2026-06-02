"""FastAPI dependency that provides an async DB session per request."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import AsyncSessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession, guaranteed to close after the request."""
    async with AsyncSessionLocal() as session:
        yield session
