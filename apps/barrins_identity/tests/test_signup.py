"""Tests for self-registration and email verification.

Covers POST /auth/signup, /auth/signup/verify, /auth/signup/resend, and
app/models/email_verification.py.
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.email_verification import EmailVerification
from app.models.user import User
from app.services.email import get_email_sender


class _FakeEmailSender:
    """Test double — captures emails instead of sending them."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send_verification_code(
        self, *, to_email: str, code: str, verify_link: str
    ) -> None:
        self.sent.append(
            {"to_email": to_email, "code": code, "verify_link": verify_link}
        )


class _FailingEmailSender:
    """Test double — simulates an SMTP send failure."""

    def send_verification_code(
        self, *, to_email: str, code: str, verify_link: str
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
    """Already-verified account — used for the "already registered"/"verified" cases."""
    user = User(
        email="user@test.com",
        hashed_password=hash_password("User#Pass1word"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _signup(
    client: AsyncClient,
    email: str = "newplayer@example.com",
    password: str = "ValidPass#1word",
) -> None:
    resp = await client.post(
        "/api/v1/auth/signup", json={"email": email, "password": password}
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# POST /auth/signup
# ---------------------------------------------------------------------------


class TestSignup:
    async def test_creates_pending_unverified_account(
        self, client: AsyncClient, db_session, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)

        result = await db_session.execute(
            select(User).where(User.email == "newplayer@example.com")
        )
        user = result.scalar_one()
        assert user.is_verified is False
        assert user.role == "user"

        assert len(fake_email_sender.sent) == 1
        assert fake_email_sender.sent[0]["to_email"] == "newplayer@example.com"
        assert len(fake_email_sender.sent[0]["code"]) == 6

    async def test_creates_verification_record(
        self, client: AsyncClient, db_session, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)

        result = await db_session.execute(
            select(User).where(User.email == "newplayer@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        )
        verification = result.scalar_one()
        assert verification.attempts == 0
        assert verification.expires_at > datetime.now(UTC)

    async def test_verify_link_uses_frontend_base_url(
        self, client: AsyncClient, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)
        link = fake_email_sender.sent[0]["verify_link"]
        assert link.startswith(f"{settings.base.frontend_base_url}/verify-email?")
        assert "code=" in link
        assert "email=" in link

    async def test_duplicate_email_returns_409(
        self,
        client: AsyncClient,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "user@test.com", "password": "AnyValid#1pass"},
        )
        assert resp.status_code == 409
        assert fake_email_sender.sent == []

    async def test_extra_field_returns_422(
        self, client: AsyncClient, fake_email_sender: _FakeEmailSender
    ):
        resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "x@x.com", "password": "SomeValid#1pass", "role": "admin"},
        )
        assert resp.status_code == 422
        assert fake_email_sender.sent == []

    async def test_weak_password_returns_422(
        self, client: AsyncClient, fake_email_sender: _FakeEmailSender
    ):
        resp = await client.post(
            "/api/v1/auth/signup", json={"email": "weak@x.com", "password": "short"}
        )
        assert resp.status_code == 422

    async def test_email_send_failure_returns_502_and_rolls_back(
        self, client: AsyncClient, db_session, failing_email_sender: _FailingEmailSender
    ):
        resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "unlucky@example.com", "password": "ValidPass#1word"},
        )
        assert resp.status_code == 502

        result = await db_session.execute(
            select(User).where(User.email == "unlucky@example.com")
        )
        assert result.scalar_one_or_none() is None


class TestSignupWithVerificationDisabled:
    """REQUIRE_EMAIL_VERIFICATION=false — temporary workaround without SMTP."""

    async def test_creates_already_verified_account_and_returns_tokens(
        self,
        client: AsyncClient,
        db_session,
        fake_email_sender: _FakeEmailSender,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(settings.base, "require_email_verification", False)

        resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "instant@example.com", "password": "ValidPass#1word"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["verification_required"] is False
        assert body["tokens"]["access_token"]
        assert body["tokens"]["refresh_token"]

        result = await db_session.execute(
            select(User).where(User.email == "instant@example.com")
        )
        user = result.scalar_one()
        assert user.is_verified is True

        assert fake_email_sender.sent == []
        verification_result = await db_session.execute(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        )
        assert verification_result.scalar_one_or_none() is None

    async def test_issued_tokens_authenticate_immediately(
        self,
        client: AsyncClient,
        fake_email_sender: _FakeEmailSender,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(settings.base, "require_email_verification", False)

        signup_resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "instant2@example.com", "password": "ValidPass#1word"},
        )
        access_token = signup_resp.json()["tokens"]["access_token"]

        me_resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "instant2@example.com"
        assert me_resp.json()["is_verified"] is True

    async def test_duplicate_email_still_returns_409(
        self,
        client: AsyncClient,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(settings.base, "require_email_verification", False)

        resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "user@test.com", "password": "AnyValid#1pass"},
        )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /auth/signup/verify
# ---------------------------------------------------------------------------


class TestVerifySignup:
    async def test_valid_code_verifies_and_returns_tokens(
        self, client: AsyncClient, db_session, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)
        code = fake_email_sender.sent[0]["code"]

        resp = await client.post(
            "/api/v1/auth/signup/verify",
            json={"email": "newplayer@example.com", "code": code},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

        result = await db_session.execute(
            select(User).where(User.email == "newplayer@example.com")
        )
        user = result.scalar_one()
        assert user.is_verified is True

    async def test_valid_code_deletes_verification_record(
        self, client: AsyncClient, db_session, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)
        code = fake_email_sender.sent[0]["code"]
        await client.post(
            "/api/v1/auth/signup/verify",
            json={"email": "newplayer@example.com", "code": code},
        )

        result = await db_session.execute(
            select(User).where(User.email == "newplayer@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_wrong_code_returns_400_and_increments_attempts(
        self, client: AsyncClient, db_session, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)

        resp = await client.post(
            "/api/v1/auth/signup/verify",
            json={"email": "newplayer@example.com", "code": "000000"},
        )
        assert resp.status_code == 400

        result = await db_session.execute(
            select(User).where(User.email == "newplayer@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        )
        verification = result.scalar_one()
        assert verification.attempts == 1

    async def test_unknown_email_returns_400(
        self, client: AsyncClient, fake_email_sender: _FakeEmailSender
    ):
        resp = await client.post(
            "/api/v1/auth/signup/verify",
            json={"email": "ghost@example.com", "code": "123456"},
        )
        assert resp.status_code == 400

    async def test_already_verified_returns_409(
        self, client: AsyncClient, regular_user: User
    ):
        resp = await client.post(
            "/api/v1/auth/signup/verify",
            json={"email": "user@test.com", "code": "123456"},
        )
        assert resp.status_code == 409

    async def test_missing_verification_record_returns_400(
        self, client: AsyncClient, db_session
    ):
        user = User(
            email="norecord@example.com",
            hashed_password="irrelevant",
            is_verified=False,
        )
        db_session.add(user)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/signup/verify",
            json={"email": "norecord@example.com", "code": "123456"},
        )
        assert resp.status_code == 400

    async def test_expired_code_returns_400(
        self, client: AsyncClient, db_session, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)
        result = await db_session.execute(
            select(User).where(User.email == "newplayer@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        )
        verification = result.scalar_one()
        verification.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db_session.add(verification)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/signup/verify",
            json={
                "email": "newplayer@example.com",
                "code": fake_email_sender.sent[0]["code"],
            },
        )
        assert resp.status_code == 400

    async def test_too_many_attempts_returns_429(
        self, client: AsyncClient, db_session, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)
        result = await db_session.execute(
            select(User).where(User.email == "newplayer@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        )
        verification = result.scalar_one()
        verification.attempts = settings.base.verification_max_attempts
        db_session.add(verification)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/signup/verify",
            json={
                "email": "newplayer@example.com",
                "code": fake_email_sender.sent[0]["code"],
            },
        )
        assert resp.status_code == 429

    async def test_invalid_code_format_returns_422(
        self, client: AsyncClient, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)
        resp = await client.post(
            "/api/v1/auth/signup/verify",
            json={"email": "newplayer@example.com", "code": "not-a-code"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/signup/resend
# ---------------------------------------------------------------------------


class TestResendVerification:
    async def test_generates_new_code(
        self, client: AsyncClient, db_session, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)
        first_code = fake_email_sender.sent[0]["code"]

        result = await db_session.execute(
            select(User).where(User.email == "newplayer@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        )
        verification = result.scalar_one()
        verification.last_sent_at = datetime.now(UTC) - timedelta(
            seconds=settings.base.verification_resend_cooldown_seconds + 1
        )
        db_session.add(verification)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/signup/resend", json={"email": "newplayer@example.com"}
        )
        assert resp.status_code == 202
        assert len(fake_email_sender.sent) == 2
        assert fake_email_sender.sent[1]["code"] != first_code

    async def test_resets_attempts_counter(
        self, client: AsyncClient, db_session, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)
        result = await db_session.execute(
            select(User).where(User.email == "newplayer@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        )
        verification = result.scalar_one()
        verification.attempts = 3
        verification.last_sent_at = datetime.now(UTC) - timedelta(
            seconds=settings.base.verification_resend_cooldown_seconds + 1
        )
        db_session.add(verification)
        await db_session.commit()

        await client.post(
            "/api/v1/auth/signup/resend", json={"email": "newplayer@example.com"}
        )

        await db_session.refresh(verification)
        assert verification.attempts == 0

    async def test_unknown_email_returns_generic_202(
        self, client: AsyncClient, fake_email_sender: _FakeEmailSender
    ):
        resp = await client.post(
            "/api/v1/auth/signup/resend", json={"email": "ghost@example.com"}
        )
        assert resp.status_code == 202
        assert fake_email_sender.sent == []

    async def test_already_verified_returns_generic_202_without_sending(
        self,
        client: AsyncClient,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        resp = await client.post(
            "/api/v1/auth/signup/resend", json={"email": "user@test.com"}
        )
        assert resp.status_code == 202
        assert fake_email_sender.sent == []

    async def test_cooldown_active_returns_generic_202_without_sending(
        self, client: AsyncClient, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)
        assert len(fake_email_sender.sent) == 1

        resp = await client.post(
            "/api/v1/auth/signup/resend", json={"email": "newplayer@example.com"}
        )
        assert resp.status_code == 202
        assert len(fake_email_sender.sent) == 1

    async def test_email_send_failure_returns_502(
        self, client: AsyncClient, db_session, fake_email_sender: _FakeEmailSender
    ):
        await _signup(client)
        result = await db_session.execute(
            select(User).where(User.email == "newplayer@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        )
        verification = result.scalar_one()
        verification.last_sent_at = datetime.now(UTC) - timedelta(
            seconds=settings.base.verification_resend_cooldown_seconds + 1
        )
        db_session.add(verification)
        await db_session.commit()

        app.dependency_overrides[get_email_sender] = lambda: _FailingEmailSender()
        try:
            resp = await client.post(
                "/api/v1/auth/signup/resend", json={"email": "newplayer@example.com"}
            )
        finally:
            app.dependency_overrides.pop(get_email_sender, None)
        assert resp.status_code == 502
