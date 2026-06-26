"""Auth routes: register, login, logout, me.

Prefix: /api/auth (mounted in main.py)

Auth is a short-lived JWT carried in an httpOnly cookie (set on login/register,
cleared on logout). The browser sends it automatically; JS never reads it.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, UserOut

router = APIRouter()


# ─── Login rate limit ───────────────────────────────────────────────────────
# ponytail: in-memory sliding window, single-process only. Behind multiple
# workers/replicas move this to Redis. Fine for a portfolio demo.
_LOGIN_MAX_ATTEMPTS = 10
_LOGIN_WINDOW_SECONDS = 60
_login_hits: dict[str, list[float]] = defaultdict(list)


def _rate_limit_login(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = [t for t in _login_hits[ip] if now - t < _LOGIN_WINDOW_SECONDS]
    if len(hits) >= _LOGIN_MAX_ATTEMPTS:
        _login_hits[ip] = hits
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in a minute.",
        )
    hits.append(now)
    _login_hits[ip] = hits


def _set_session_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=create_access_token(user.id),
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


# ─── Register ───────────────────────────────────────────────────────────────


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterIn,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    await session.refresh(user)
    _set_session_cookie(response, user)
    return user


# ─── Login ──────────────────────────────────────────────────────────────────


@router.post("/login", response_model=UserOut)
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    _rate_limit_login(request)
    result = await session.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    # Same generic error whether the email is unknown or the password is wrong.
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    _set_session_cookie(response, user)
    return user


# ─── Logout ─────────────────────────────────────────────────────────────────


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


# ─── Me ─────────────────────────────────────────────────────────────────────


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
