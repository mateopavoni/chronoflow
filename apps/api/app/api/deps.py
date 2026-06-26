"""Shared FastAPI dependencies — current authenticated user from the session cookie."""

from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.user import User

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
)


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    # Cookie name must match settings.AUTH_COOKIE_NAME; FastAPI needs a literal
    # alias, so we read the default name here and keep them in sync.
    chronoflow_session: str | None = Cookie(default=None, alias="chronoflow_session"),
) -> User:
    """Resolve the logged-in user or raise 401. Use as a route dependency."""
    assert settings.AUTH_COOKIE_NAME == "chronoflow_session"  # guard against drift
    if not chronoflow_session:
        raise _UNAUTHORIZED
    user_id = decode_access_token(chronoflow_session)
    if user_id is None:
        raise _UNAUTHORIZED
    user = await session.get(User, user_id)
    if user is None:
        raise _UNAUTHORIZED
    return user
