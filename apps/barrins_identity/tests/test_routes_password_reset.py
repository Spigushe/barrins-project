"""Tests for /api/v1/auth/password-reset/{request,confirm} (platform.md §14).

Negative cases follow tests.md §8.
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password, verify_password
from app.main import app
from app.models.password_reset import PasswordResetCode
from app.models.user import User, UserRole
from app.services.email import get_email_sender


class _FakeEmailSender:
    """Test double — captures emails instead of sending them."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send_password_reset_code(
        self, *, to_email: str, code: str, reset_link: str
    ) -> None:
        self.sent.append({"to_email": to_email, "code": code, "reset_link": reset_link})


class _FailingEmailSender:
    """Test double — simulates an SMTP send failure."""

    def send_password_reset_code(
        self, *, to_email: str, code: str, reset_link: str
    ) -> None:
        raise RuntimeError("SMTP unavailable")


@pytest.fixture()
def fake_email_sender() -> Generator[_FakeEmailSender, Any]:
    sender = _FakeEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: sender
    yield sender
    app.dependency_overrides.pop(get_email_sender, None)


@pytest.fixture()
def failing_email_sender() -> Generator[_FailingEmailSender, Any]:
    sender = _FailingEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: sender
    yield sender
    app.dependency_overrides.pop(get_email_sender, None)


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


async def _request_reset(client: AsyncClient, email: str = "user@test.com") -> None:
    resp = await client.post(
        "/api/v1/auth/password-reset/request", json={"email": email}
    )
    assert resp.status_code == 202


# ---------------------------------------------------------------------------
# POST /auth/password-reset/request
# ---------------------------------------------------------------------------


class TestRequestPasswordReset:
    async def test_creates_reset_code_and_sends_email(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        await _request_reset(client)

        result = await db_session.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.user_id == regular_user.id
            )
        )
        reset_code = result.scalar_one()
        assert reset_code.attempts == 0
        assert reset_code.expires_at > datetime.now(UTC)

        assert len(fake_email_sender.sent) == 1
        assert fake_email_sender.sent[0]["to_email"] == "user@test.com"
        assert len(fake_email_sender.sent[0]["code"]) == 6

    async def test_reset_link_uses_frontend_base_url(
        self,
        client: AsyncClient,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        await _request_reset(client)
        link = fake_email_sender.sent[0]["reset_link"]
        assert link.startswith(f"{settings.base.frontend_base_url}/reset-password?")
        assert "code=" in link
        assert "email=" in link

    async def test_unknown_email_returns_generic_202(
        self, client: AsyncClient, fake_email_sender: _FakeEmailSender
    ):
        resp = await client.post(
            "/api/v1/auth/password-reset/request", json={"email": "ghost@example.com"}
        )
        assert resp.status_code == 202
        assert fake_email_sender.sent == []

    async def test_inactive_account_returns_generic_202_without_sending(
        self,
        client: AsyncClient,
        inactive_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        resp = await client.post(
            "/api/v1/auth/password-reset/request", json={"email": "inactive@test.com"}
        )
        assert resp.status_code == 202
        assert fake_email_sender.sent == []

    async def test_soft_deleted_account_returns_generic_202_without_sending(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        """A soft-deleted account's email is anonymized (platform.md §15) —
        a lookup by the original address naturally finds no row."""
        original_email = regular_user.email
        regular_user.email = f"deleted-{regular_user.id}@barrins.invalid"
        regular_user.is_active = False
        db_session.add(regular_user)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/password-reset/request", json={"email": original_email}
        )
        assert resp.status_code == 202
        assert fake_email_sender.sent == []

    async def test_cooldown_active_returns_generic_202_without_sending(
        self,
        client: AsyncClient,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        await _request_reset(client)
        assert len(fake_email_sender.sent) == 1

        resp = await client.post(
            "/api/v1/auth/password-reset/request", json={"email": "user@test.com"}
        )
        assert resp.status_code == 202
        assert len(fake_email_sender.sent) == 1

    async def test_second_request_after_cooldown_replaces_code(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        await _request_reset(client)
        first_code = fake_email_sender.sent[0]["code"]

        result = await db_session.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.user_id == regular_user.id
            )
        )
        reset_code = result.scalar_one()
        reset_code.last_sent_at = datetime.now(UTC) - timedelta(
            seconds=settings.base.password_reset_resend_cooldown_seconds + 1
        )
        db_session.add(reset_code)
        await db_session.commit()

        await _request_reset(client)
        assert len(fake_email_sender.sent) == 2
        assert fake_email_sender.sent[1]["code"] != first_code

    async def test_email_send_failure_returns_502_and_rolls_back(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        failing_email_sender: _FailingEmailSender,
    ):
        resp = await client.post(
            "/api/v1/auth/password-reset/request", json={"email": "user@test.com"}
        )
        assert resp.status_code == 502

        result = await db_session.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.user_id == regular_user.id
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_extra_field_returns_422(
        self, client: AsyncClient, fake_email_sender: _FakeEmailSender
    ):
        resp = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "x@x.com", "injected": "evil"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/password-reset/confirm
# ---------------------------------------------------------------------------


class TestConfirmPasswordReset:
    async def test_valid_code_resets_password_and_returns_tokens(
        self, client: AsyncClient, db_session, regular_user: User, fake_email_sender
    ):
        await _request_reset(client)
        code = fake_email_sender.sent[0]["code"]

        resp = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "user@test.com",
                "code": code,
                "new_password": "BrandNew#1word",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

        await db_session.refresh(regular_user)
        assert verify_password("BrandNew#1word", regular_user.hashed_password)

    async def test_valid_code_bumps_token_version(
        self, client: AsyncClient, db_session, regular_user: User, fake_email_sender
    ):
        await _request_reset(client)
        code = fake_email_sender.sent[0]["code"]

        await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "user@test.com",
                "code": code,
                "new_password": "BrandNew#1word",
            },
        )

        await db_session.refresh(regular_user)
        assert regular_user.token_version == 1

    async def test_valid_code_deletes_reset_row(
        self, client: AsyncClient, db_session, regular_user: User, fake_email_sender
    ):
        await _request_reset(client)
        code = fake_email_sender.sent[0]["code"]
        await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "user@test.com",
                "code": code,
                "new_password": "BrandNew#1word",
            },
        )

        result = await db_session.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.user_id == regular_user.id
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_replaying_consumed_code_returns_400(
        self, client: AsyncClient, regular_user: User, fake_email_sender
    ):
        await _request_reset(client)
        code = fake_email_sender.sent[0]["code"]
        await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "user@test.com",
                "code": code,
                "new_password": "BrandNew#1word",
            },
        )

        resp = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "user@test.com",
                "code": code,
                "new_password": "AnotherNew#1word",
            },
        )
        assert resp.status_code == 400

    async def test_wrong_code_returns_400_and_increments_attempts(
        self, client: AsyncClient, db_session, regular_user: User, fake_email_sender
    ):
        await _request_reset(client)

        resp = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "user@test.com",
                "code": "000000",
                "new_password": "BrandNew#1word",
            },
        )
        assert resp.status_code == 400

        result = await db_session.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.user_id == regular_user.id
            )
        )
        reset_code = result.scalar_one()
        assert reset_code.attempts == 1

    async def test_unknown_email_returns_400(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "ghost@example.com",
                "code": "123456",
                "new_password": "BrandNew#1word",
            },
        )
        assert resp.status_code == 400

    async def test_missing_reset_record_returns_400(
        self, client: AsyncClient, regular_user: User
    ):
        resp = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "user@test.com",
                "code": "123456",
                "new_password": "BrandNew#1word",
            },
        )
        assert resp.status_code == 400

    async def test_expired_code_returns_400(
        self, client: AsyncClient, db_session, regular_user: User, fake_email_sender
    ):
        await _request_reset(client)
        result = await db_session.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.user_id == regular_user.id
            )
        )
        reset_code = result.scalar_one()
        reset_code.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db_session.add(reset_code)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "user@test.com",
                "code": fake_email_sender.sent[0]["code"],
                "new_password": "BrandNew#1word",
            },
        )
        assert resp.status_code == 400

    async def test_too_many_attempts_returns_429(
        self, client: AsyncClient, db_session, regular_user: User, fake_email_sender
    ):
        await _request_reset(client)
        result = await db_session.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.user_id == regular_user.id
            )
        )
        reset_code = result.scalar_one()
        reset_code.attempts = settings.base.password_reset_max_attempts
        db_session.add(reset_code)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "user@test.com",
                "code": fake_email_sender.sent[0]["code"],
                "new_password": "BrandNew#1word",
            },
        )
        assert resp.status_code == 429

    async def test_weak_new_password_returns_422(
        self, client: AsyncClient, regular_user: User, fake_email_sender
    ):
        await _request_reset(client)
        resp = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "user@test.com",
                "code": fake_email_sender.sent[0]["code"],
                "new_password": "short",
            },
        )
        assert resp.status_code == 422

    async def test_old_tokens_rejected_after_reset(
        self, client: AsyncClient, regular_user: User, fake_email_sender
    ):
        from app.core.security import create_access_token

        old_token = create_access_token(
            {
                "sub": str(regular_user.id),
                "role": regular_user.role.value,
                "email": regular_user.email,
                "tkv": regular_user.token_version,
            }
        )

        await _request_reset(client)
        code = fake_email_sender.sent[0]["code"]
        await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "user@test.com",
                "code": code,
                "new_password": "BrandNew#1word",
            },
        )

        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Rate limit — POST /auth/password-reset/request
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _low_rate_limit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings.base, "password_reset_rate_limit", "2/minute")


class TestPasswordResetRateLimit:
    async def test_exceeding_limit_returns_429(self, client: AsyncClient):
        payload = {"email": "nobody@example.com"}

        first = await client.post("/api/v1/auth/password-reset/request", json=payload)
        second = await client.post("/api/v1/auth/password-reset/request", json=payload)
        third = await client.post("/api/v1/auth/password-reset/request", json=payload)

        assert first.status_code == 202
        assert second.status_code == 202
        assert third.status_code == 429
