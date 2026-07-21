"""Auth routes: register, login, logout, me.

Prefix: /api/auth (mounted in main.py)

Auth is a short-lived JWT carried in an httpOnly cookie (set on login/register,
cleared on logout). The browser sends it automatically; JS never reads it.
"""

from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import RateLimiter
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, UserOut
from app.services.seed import seed_workflows_for_user

router = APIRouter()


# ─── Rate limits (per client IP) ────────────────────────────────────────────
_login_limiter = RateLimiter(10, 60, "Too many login attempts. Try again in a minute.")
# Registration is cheaper to abuse than login (no password to guess) but each
# hit creates a DB row + seeds 3 workflows, so keep it tighter than login.
_register_limiter = RateLimiter(5, 60, "Too many registration attempts. Try again in a minute.")
# Same cost as register (row + 3 seeded workflows) but one click, no form —
# needs its own budget so it can't be used to bypass the register limiter.
_guest_limiter = RateLimiter(5, 60, "Too many demo logins. Try again in a minute.")


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


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
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    _register_limiter.check(_client_ip(request))
    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    await session.refresh(user)
    # Give every new account its own copy of the 3 example workflows to explore.
    # Workflows are owned per-user (see app/models/workflow.py) so this can't be
    # a shared global seed anymore — see app/services/seed.py.
    await seed_workflows_for_user(session, user.id)
    _set_session_cookie(response, user)
    return user


# ─── Guest ──────────────────────────────────────────────────────────────────


@router.post("/guest", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def guest(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """One-click demo account: throwaway email/password, seeded workflows.

    Same shape as /register minus the form — for portfolio visitors who don't
    want to type an email to see the product.
    """
    _guest_limiter.check(_client_ip(request))
    email = f"guest-{uuid.uuid4().hex[:12]}@chronoflow.demo"
    user = User(email=email, password_hash=hash_password(secrets.token_urlsafe(24)))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await seed_workflows_for_user(session, user.id)
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
    _login_limiter.check(_client_ip(request))
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
