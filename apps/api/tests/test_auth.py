"""Auth flow tests: register, login, logout, me, IDOR-free session, rate limit."""

from __future__ import annotations

import pytest

from app.api.routes import auth as auth_route

CREDS = {"email": "alice@example.com", "password": "supersecret1"}


@pytest.mark.asyncio
async def test_register_sets_cookie_and_me_works(client):
    r = await client.post("/api/auth/register", json=CREDS)
    assert r.status_code == 201
    assert r.json()["email"] == "alice@example.com"
    assert auth_route.settings.AUTH_COOKIE_NAME in r.cookies

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email_conflicts(client):
    await client.post("/api/auth/register", json=CREDS)
    r = await client.post("/api/auth/register", json={**CREDS, "password": "another-one"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_me_without_cookie_is_401(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_wrong_password_is_401(client):
    await client.post("/api/auth/register", json=CREDS)
    # Clear the session cookie set by register so we test login in isolation.
    client.cookies.clear()
    r = await client.post(
        "/api/auth/login", json={"email": CREDS["email"], "password": "wrong-password"}
    )
    assert r.status_code == 401
    # Generic message — must not reveal whether the email exists.
    assert "Invalid email or password" in r.text


@pytest.mark.asyncio
async def test_login_then_logout_clears_session(client):
    await client.post("/api/auth/register", json=CREDS)
    client.cookies.clear()

    ok = await client.post("/api/auth/login", json=CREDS)
    assert ok.status_code == 200
    assert (await client.get("/api/auth/me")).status_code == 200

    out = await client.post("/api/auth/logout")
    assert out.status_code == 204
    assert (await client.get("/api/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limited(client):
    auth_route._login_hits.clear()
    await client.post("/api/auth/register", json=CREDS)
    client.cookies.clear()

    last = None
    for _ in range(auth_route._LOGIN_MAX_ATTEMPTS + 2):
        last = await client.post(
            "/api/auth/login", json={"email": CREDS["email"], "password": "wrong"}
        )
    assert last is not None and last.status_code == 429
    auth_route._login_hits.clear()
