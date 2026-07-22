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
            json={"email": "newuser@example.com", "password": "NewUser#Pass1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "newuser@example.com"
        assert body["role"] == "user"
        assert "hashed_password" not in body

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, admin_user: User, regular_user: User
    ):
        token = _access_token_for(admin_user)
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "user@test.com", "password": "AnyValid#1pass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    async def test_non_admin_returns_403(self, client: AsyncClient, regular_user: User):
        token = _access_token_for(regular_user)
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "x@x.com", "password": "SomeValid#1pass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "x@x.com", "password": "SomeValid#1pass"},
        )
        assert resp.status_code == 401

    async def test_extra_field_returns_422(self, client: AsyncClient, admin_user: User):
        token = _access_token_for(admin_user)
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "x2@x.com",
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
            json={"email": "weak@x.com", "password": "short"},
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
