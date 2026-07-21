"""Tests for JWT authentication and role management.

Covers 100%:
- app/core/security.py
- app/dependencies/auth.py
- app/api/v1/routers/auth.py (excluding /signup, /signup/verify, /signup/resend
  — see tests/test_signup.py)
- app/models/user.py (completes the missing line)
"""

# pyright: reportUnknownMemberType=none, reportUnknownVariableType=none, reportUnknownArgumentType=none, reportUnknownParameterType=none, reportMissingParameterType=none, reportUnusedImport=none, reportUnusedFunction=none

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    dummy_verify,
    generate_verification_code,
    hash_password,
    hash_verification_code,
    verify_password,
    verify_verification_code,
)
from app.models.user import User, UserRole
from app.schemas.auth import TokenPair, UserCreate, UserRead  # noqa: F401

# ===========================================================================
# Helpers
# ===========================================================================


def _make_claims(user: User) -> dict[str, str | int | datetime]:
    return {
        "sub": str(user.id),
        "role": user.role.value,
        "email": user.email,
        "tkv": user.token_version,
    }


def _create_user(
    session,
    email: str = "test@example.com",
    password: str = "ValidPass#1word",  # noqa: S107
    role: UserRole = UserRole.user,
    is_active: bool = True,
    token_version: int = 0,
) -> User:
    """Creates and persists a User in the session (no commit — rolled back after)."""

    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
        is_verified=True,
        token_version=token_version,
    )
    return user


# ===========================================================================
# app/models/user.py — UserRole.level
# ===========================================================================


class TestUserRoleLevel:
    def test_user_level(self):
        assert UserRole.user.level == 1

    def test_placeholder_level(self):
        assert UserRole.placeholder.level == 2

    def test_ml_developer_level(self):
        assert UserRole.ml_developer.level == 3

    def test_admin_level(self):
        assert UserRole.admin.level == 4

    def test_str_value(self):
        assert UserRole.admin == "admin"
        assert UserRole.user == "user"


# ===========================================================================
# app/core/security.py
# ===========================================================================


class TestHashPassword:
    def test_hash_is_not_plain(self):
        h = hash_password("MyPassword#1")
        assert h != "MyPassword#1"

    def test_two_hashes_differ(self):
        # Argon2 is salted — two hashes of the same password are different
        assert hash_password("Same#Pass1") != hash_password("Same#Pass1")


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        h = hash_password("Correct#Pass1")
        assert verify_password("Correct#Pass1", h) is True

    def test_wrong_password_returns_false(self):
        h = hash_password("Correct#Pass1")
        assert verify_password("WrongPass#1", h) is False

    def test_invalid_hash_returns_false(self):
        assert verify_password("any_password", "not_a_valid_hash") is False

    def test_empty_string_hash_returns_false(self):
        assert verify_password("any_password", "") is False


class TestDummyVerify:
    def test_does_not_raise_on_wrong_password(self):
        # Must never raise — just consumes time
        dummy_verify("wrong_password")

    def test_does_not_raise_on_empty_string(self):
        dummy_verify("")


class TestCreateDecodeAccessToken:
    def _claims(self) -> dict[str, str | int | datetime]:
        return {
            "sub": str(uuid.uuid4()),
            "role": "user",
            "email": "u@example.com",
            "tkv": 0,
        }

    def test_roundtrip(self):
        token = create_access_token(self._claims())
        data = decode_access_token(token)
        assert data.sub is not None
        assert data.role == UserRole.user
        assert data.token_version == 0

    def test_type_claim_is_access(self):
        token = create_access_token(self._claims())
        payload = jwt.decode(
            token,
            settings.base.secret_key,
            algorithms=[settings.base.algorithm],
        )
        assert payload["type"] == "access"

    def test_decode_refresh_token_as_access_raises(self):
        from jose import JWTError

        refresh = create_refresh_token(self._claims())
        with pytest.raises(JWTError):
            decode_access_token(refresh)

    def test_decode_expired_token_raises(self):
        from jose import JWTError

        claims = self._claims()
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
        claims["type"] = "access"
        token = jwt.encode(
            claims, settings.base.secret_key, algorithm=settings.base.algorithm
        )
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_decode_bad_token_raises(self):
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_access_token("not.a.token")


class TestCreateDecodeRefreshToken:
    def _claims(self) -> dict[str, str | int | datetime]:
        return {
            "sub": str(uuid.uuid4()),
            "role": "admin",
            "email": "admin@example.com",
            "tkv": 2,
        }

    def test_roundtrip(self):
        token = create_refresh_token(self._claims())
        data = decode_refresh_token(token)
        assert data.role == UserRole.admin
        assert data.token_version == 2

    def test_type_claim_is_refresh(self):
        token = create_refresh_token(self._claims())
        payload = jwt.decode(
            token,
            settings.base.secret_key,
            algorithms=[settings.base.algorithm],
        )
        assert payload["type"] == "refresh"

    def test_decode_access_token_as_refresh_raises(self):
        from jose import JWTError

        access = create_access_token(self._claims())
        with pytest.raises(JWTError):
            decode_refresh_token(access)


class TestVerificationCode:
    def test_generate_returns_six_digits(self):
        code = generate_verification_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_is_zero_padded(self, monkeypatch: pytest.MonkeyPatch):
        # always return a small number to test zero-padding
        monkeypatch.setattr("app.core.security.secrets.randbelow", lambda _n: 42)
        assert generate_verification_code() == "000042"

    def test_hash_roundtrip_succeeds(self):
        user_id = uuid.uuid4()
        code = "123456"
        stored = hash_verification_code(code, user_id)
        assert verify_verification_code(code, user_id, stored)

    def test_hash_differs_per_user(self):
        code = "123456"
        assert hash_verification_code(code, uuid.uuid4()) != hash_verification_code(
            code, uuid.uuid4()
        )

    def test_verify_rejects_wrong_code(self):
        user_id = uuid.uuid4()
        stored = hash_verification_code("123456", user_id)
        assert verify_verification_code("654321", user_id, stored) is False

    def test_verify_rejects_wrong_user(self):
        code = "123456"
        stored = hash_verification_code(code, uuid.uuid4())
        assert verify_verification_code(code, uuid.uuid4(), stored) is False


# ===========================================================================
# app/api/v1/routers/auth.py  — via client HTTP
# ===========================================================================


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


def _access_token_for(user: User) -> str:
    return create_access_token(_make_claims(user))


def _refresh_token_for(user: User) -> str:
    return create_refresh_token(_make_claims(user))


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
        assert body["token_type"] == "bearer"  # noqa: S105

    async def test_wrong_password_returns_401(
        self, client: AsyncClient, regular_user: User
    ):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "user@test.com", "password": "WrongPass#1word"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["message"] == "Invalid credentials."
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
        """The three failure branches (unknown email, wrong password, inactive)
        return exactly the same message — no inference possible."""
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
        """A token with tkv=0 is rejected if token_version in the DB is 1."""
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
        """A valid access token for an inactive account is rejected."""
        token = _access_token_for(inactive_user)
        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    async def test_nonexistent_user_token_rejected(self, client: AsyncClient):
        """An access token for a UUID that doesn't exist in the DB returns 401."""
        # Generate a token with a random UUID: this user doesn't exist in the DB.
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
                "password": "NewUser#Pass1",
            },
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
