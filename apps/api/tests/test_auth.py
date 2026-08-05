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
async def test_login_401_message_is_identical_but_carries_clear_email_hint(client):
    """Wrong password vs unknown email: same user-facing text, different UX hint.

    `clear_email` is what the login form uses to decide whether to keep the typed
    email (wrong password) or wipe it (no such account) — it must never change
    the message the user actually reads.
    """
    await client.post("/api/auth/register", json=CREDS)
    client.cookies.clear()

    wrong_password = await client.post(
        "/api/auth/login", json={"email": CREDS["email"], "password": "wrong-password"}
    )
    unknown_email = await client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": CREDS["password"]}
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401

    wp_detail = wrong_password.json()["detail"]
    ue_detail = unknown_email.json()["detail"]
    assert wp_detail["message"] == ue_detail["message"] == "Invalid email or password"
    assert wp_detail["clear_email"] is False
    assert ue_detail["clear_email"] is True


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
    auth_route._login_limiter._hits.clear()
    await client.post("/api/auth/register", json=CREDS)
    client.cookies.clear()

    last = None
    for _ in range(auth_route._login_limiter.max_attempts + 2):
        last = await client.post(
            "/api/auth/login", json={"email": CREDS["email"], "password": "wrong"}
        )
    assert last is not None and last.status_code == 429
    auth_route._login_limiter._hits.clear()


@pytest.mark.asyncio
async def test_guest_creates_session_with_seeded_workflows(client):
    r = await client.post("/api/auth/guest")
    assert r.status_code == 201
    assert r.json()["email"].startswith("guest-")
    assert auth_route.settings.AUTH_COOKIE_NAME in r.cookies

    me = await client.get("/api/auth/me")
    assert me.status_code == 200

    workflows = await client.get("/api/workflows/")
    assert workflows.status_code == 200
    assert len(workflows.json()) == 3


@pytest.mark.asyncio
async def test_guest_rate_limited(client):
    auth_route._guest_limiter._hits.clear()
    last = None
    for _ in range(auth_route._guest_limiter.max_attempts + 2):
        client.cookies.clear()
        last = await client.post("/api/auth/guest")
    assert last is not None and last.status_code == 429
    auth_route._guest_limiter._hits.clear()


@pytest.mark.asyncio
async def test_register_rate_limited(client):
    auth_route._register_limiter._hits.clear()

    last = None
    for i in range(auth_route._register_limiter.max_attempts + 2):
        last = await client.post(
            "/api/auth/register",
            json={"email": f"flood{i}@example.com", "password": "supersecret1"},
        )
        client.cookies.clear()
    assert last is not None and last.status_code == 429
    auth_route._register_limiter._hits.clear()
