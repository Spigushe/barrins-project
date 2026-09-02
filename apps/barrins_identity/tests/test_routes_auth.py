"""Tests for /api/v1/auth/* — token, refresh, register, me, logout.

Negative cases follow tests.md §3.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, create_refresh_token, hash_password
from app.models.user import User, UserRole


def _claims(user: User) -> dict[str, str | int]:
    return {
        "sub": str(user.id),
        "role": user.role.value,
        "email": user.email,
        "tkv": user.token_version,
    }


def _access_token_for(user: User) -> str:
    return create_access_token(_claims(user))


def _refresh_token_for(user: User) -> str:
    return create_refresh_token(_claims(user))


@pytest.fixture()
async def admin_user(db_session) -> User:
    user = User(
        email="admin@test.com",
        username="admin",
        hashed_password=hash_password("Admin#Pass1word"),
        role=UserRole.admin,
        is_active=True,
        is_verified=True,
        token_version=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def regular_user(db_session) -> User:
    user = User(
        email="user@test.com",
        username="user",
        hashed_password=hash_password("User#Pass1word"),
        role=UserRole.user,
        is_active=True,
        is_verified=True,
        token_version=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def inactive_user(db_session) -> User:
    user = User(
        email="inactive@test.com",
        username="inactive",
        hashed_password=hash_password("Inactive#Pass1"),
        role=UserRole.user,
        is_active=False,
        is_verified=True,
        token_version=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# POST /auth/token
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_valid_credentials_returns_token_pair(
        self, client: AsyncClient, regular_user: User
    ):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "user@test.com", "password": "User#Pass1word"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_wrong_password_returns_401(
        self, client: AsyncClient, regular_user: User
    ):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "user@test.com", "password": "WrongPass#1word"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["message"] == "Invalid credentials."

    async def test_unknown_email_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "nobody@example.com", "password": "AnyPass#1word"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["message"] == "Invalid credentials."

    async def test_inactive_account_returns_401_same_message(
        self, client: AsyncClient, inactive_user: User
    ):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "inactive@test.com", "password": "Inactive#Pass1"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["message"] == "Invalid credentials."

    async def test_all_failure_branches_same_message(
        self, client: AsyncClient, inactive_user: User
    ):
        """Unknown email, wrong password, inactive account: identical message."""
        detail_unknown = (
            await client.post(
                "/api/v1/auth/token",
                data={"username": "x@x.com", "password": "Dummy#Pass1"},
            )
        ).json()["error"]["message"]
        detail_wrong_pw = (
            await client.post(
                "/api/v1/auth/token",
                data={"username": "inactive@test.com", "password": "Wrong#Pass1"},
            )
        ).json()["error"]["message"]
        detail_inactive = (
            await client.post(
                "/api/v1/auth/token",
                data={"username": "inactive@test.com", "password": "Inactive#Pass1"},
            )
        ).json()["error"]["message"]
        assert detail_unknown == detail_wrong_pw == detail_inactive


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------


class TestGetMe:
    async def test_authenticated_returns_profile(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "user@test.com"
        assert body["username"] == "user"
        assert body["role"] == "user"
        assert "hashed_password" not in body

    async def test_no_token_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"}
        )
        assert resp.status_code == 401

    async def test_refresh_token_rejected_as_access(
        self, client: AsyncClient, regular_user: User
    ):
        refresh = _refresh_token_for(regular_user)
        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"}
        )
        assert resp.status_code == 401

    async def test_revoked_token_returns_401(
        self, client: AsyncClient, db_session, regular_user: User
    ):
        token = _access_token_for(regular_user)
        regular_user.token_version = 1
        db_session.add(regular_user)
        await db_session.commit()

        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    async def test_inactive_user_token_rejected(
        self, client: AsyncClient, inactive_user: User
    ):
        token = _access_token_for(inactive_user)
        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    async def test_nonexistent_user_token_rejected(self, client: AsyncClient):
        token = create_access_token(
            {
                "sub": str(uuid.uuid4()),
                "role": UserRole.user.value,
                "email": "ghost@example.com",
                "tkv": 0,
            }
        )
        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_admin_creates_user(self, client: AsyncClient, admin_user: User):
        token = _access_token_for(admin_user)
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "NewUser#Pass1",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "newuser@example.com"
        assert body["username"] == "newuser"
        assert body["role"] == "user"
        assert "hashed_password" not in body

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, admin_user: User, regular_user: User
    ):
        token = _access_token_for(admin_user)
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "username": "dupreg",
                "password": "AnyValid#1pass",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    async def test_duplicate_username_returns_409(
        self, client: AsyncClient, admin_user: User, regular_user: User
    ):
        token = _access_token_for(admin_user)
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "fresh@example.com",
                "username": "user",
                "password": "AnyValid#1pass",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409
        assert "username" in resp.json()["error"]["message"].lower()

    async def test_missing_username_returns_422(
        self, client: AsyncClient, admin_user: User
    ):
        token = _access_token_for(admin_user)
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "nouser@example.com", "password": "AnyValid#1pass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_non_admin_returns_403(self, client: AsyncClient, regular_user: User):
        token = _access_token_for(regular_user)
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "x@x.com",
                "username": "noadmin",
                "password": "SomeValid#1pass",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "x@x.com",
                "username": "noauth",
                "password": "SomeValid#1pass",
            },
        )
        assert resp.status_code == 401

    async def test_extra_field_returns_422(self, client: AsyncClient, admin_user: User):
        token = _access_token_for(admin_user)
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "x2@x.com",
                "username": "injectt",
                "password": "SomeValid#1pass",
                "injected_field": "evil",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_weak_password_returns_422(
        self, client: AsyncClient, admin_user: User
    ):
        token = _access_token_for(admin_user)
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@x.com",
                "username": "weakreg",
                "password": "short",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------


class TestRefreshTokens:
    async def test_valid_refresh_returns_new_pair(
        self, client: AsyncClient, regular_user: User
    ):
        refresh = _refresh_token_for(regular_user)
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_access_token_rejected_as_refresh(
        self, client: AsyncClient, regular_user: User
    ):
        access = _access_token_for(regular_user)
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
        assert resp.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "not.a.token"}
        )
        assert resp.status_code == 401

    async def test_revoked_refresh_returns_401(
        self, client: AsyncClient, db_session, regular_user: User
    ):
        refresh = _refresh_token_for(regular_user)
        regular_user.token_version = 1
        db_session.add(regular_user)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh}
        )
        assert resp.status_code == 401

    async def test_inactive_user_refresh_returns_401(
        self, client: AsyncClient, inactive_user: User
    ):
        refresh = _refresh_token_for(inactive_user)
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh}
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


class TestLogout:
    async def test_logout_returns_204(self, client: AsyncClient, regular_user: User):
        token = _access_token_for(regular_user)
        resp = await client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 204

    async def test_logout_increments_token_version(
        self, client: AsyncClient, db_session, regular_user: User
    ):
        token = _access_token_for(regular_user)
        await client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )
        await db_session.refresh(regular_user)
        assert regular_user.token_version == 1

    async def test_old_token_rejected_after_logout(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        await client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )
        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    async def test_logout_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Cookie mode (ADR-18) — opt-in HttpOnly refresh-token cookie
# ---------------------------------------------------------------------------

WEB = {"X-Client": "web"}


@pytest.fixture()
def _cookie_mode_on(monkeypatch: pytest.MonkeyPatch):
    from app.config import settings

    monkeypatch.setattr(settings.base, "refresh_cookie_enabled", True)
    monkeypatch.setattr(settings.base, "refresh_cookie_domain", None)
    monkeypatch.setattr(settings.base, "refresh_cookie_samesite", "none")


class TestCookieMode:
    async def test_token_opt_in_sets_httponly_cookie_and_drops_body_refresh(
        self, client: AsyncClient, regular_user: User, _cookie_mode_on
    ):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "user@test.com", "password": "User#Pass1word"},
            headers=WEB,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        assert "refresh_token" not in body

        set_cookie = resp.headers["set-cookie"].lower()
        assert set_cookie.startswith("refresh_token=")
        assert "httponly" in set_cookie
        assert "secure" in set_cookie
        assert "samesite=none" in set_cookie
        assert "path=/api/v1/auth" in set_cookie

    async def test_token_without_opt_in_header_stays_body_mode(
        self, client: AsyncClient, regular_user: User, _cookie_mode_on
    ):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "user@test.com", "password": "User#Pass1word"},
        )
        assert resp.status_code == 200
        assert resp.json()["refresh_token"]
        assert "set-cookie" not in resp.headers

    async def test_opt_in_header_ignored_when_feature_disabled(
        self, client: AsyncClient, regular_user: User
    ):
        # No _cookie_mode_on fixture -> refresh_cookie_enabled stays False.
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "user@test.com", "password": "User#Pass1word"},
            headers=WEB,
        )
        assert resp.status_code == 200
        assert resp.json()["refresh_token"]
        assert "set-cookie" not in resp.headers

    async def test_refresh_reads_the_cookie_and_rotates_it(
        self, client: AsyncClient, regular_user: User, _cookie_mode_on
    ):
        refresh = _refresh_token_for(regular_user)
        resp = await client.post(
            "/api/v1/auth/refresh",
            headers={**WEB, "Cookie": f"refresh_token={refresh}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        assert "refresh_token" not in body
        assert resp.headers["set-cookie"].lower().startswith("refresh_token=")

    async def test_refresh_still_accepts_a_body_token_with_feature_on(
        self, client: AsyncClient, regular_user: User, _cookie_mode_on
    ):
        refresh = _refresh_token_for(regular_user)
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh}
        )
        assert resp.status_code == 200
        # No opt-in header -> body mode, refresh token returned in the body.
        assert resp.json()["refresh_token"]

    async def test_refresh_with_neither_body_nor_cookie_returns_401(
        self, client: AsyncClient, _cookie_mode_on
    ):
        resp = await client.post("/api/v1/auth/refresh", headers=WEB)
        assert resp.status_code == 401

    async def test_logout_clears_the_cookie(
        self, client: AsyncClient, regular_user: User, _cookie_mode_on
    ):
        token = _access_token_for(regular_user)
        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}", **WEB},
        )
        assert resp.status_code == 204
        set_cookie = resp.headers["set-cookie"].lower()
        assert set_cookie.startswith("refresh_token=")
        assert "max-age=0" in set_cookie or "expires=thu, 01 jan 1970" in set_cookie

    async def test_cors_allows_credentials_for_an_allowed_origin(
        self, client: AsyncClient, regular_user: User
    ):
        # Regression guard for the CORS side of ADR-18 — the middleware is
        # wired allow_credentials=True against a concrete origin list.
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "user@test.com", "password": "User#Pass1word"},
            headers={"Origin": "http://localhost:5173"},
        )
        assert resp.status_code == 200
        assert resp.headers["access-control-allow-credentials"] == "true"
        assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"
