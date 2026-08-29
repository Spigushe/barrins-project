"""Tests for /api/v1/users/me/* (platform.md §15-§16): PATCH /me,
DELETE /me, and the email-change confirmation sub-routes.

Negative cases follow tests.md §9-§10.
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.main import app
from app.models.email_change_request import EmailChangeRequest
from app.models.user import User, UserRole
from app.services.email import get_email_sender


class _FakeEmailSender:
    """Test double — captures emails instead of sending them."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send_email_change_code(
        self, *, to_email: str, code: str, verify_link: str
    ) -> None:
        self.sent.append(
            {"to_email": to_email, "code": code, "verify_link": verify_link}
        )


class _FailingEmailSender:
    def send_email_change_code(
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


def _access_token_for(user: User) -> str:
    return create_access_token(
        {
            "sub": str(user.id),
            "role": user.role.value,
            "email": user.email,
            "tkv": user.token_version,
        }
    )


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
async def other_user(db_session) -> User:
    user = User(
        email="taken@test.com",
        hashed_password=hash_password("Other#Pass1word"),
        role=UserRole.user,
        is_active=True,
        is_verified=True,
        token_version=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(autouse=True)
def _stable_verification_setting(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings.base, "require_email_verification", True)


# ---------------------------------------------------------------------------
# PATCH /users/me
# ---------------------------------------------------------------------------


class TestUpdateAccountSettings:
    async def test_display_name_applied_immediately(
        self, client: AsyncClient, db_session, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.patch(
            "/api/v1/users/me",
            json={"display_name": "Alice"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Alice"
        assert resp.json()["email"] == "user@test.com"

        await db_session.refresh(regular_user)
        assert regular_user.display_name == "Alice"

    async def test_display_name_only_creates_no_email_change_request(
        self, client: AsyncClient, db_session, regular_user: User
    ):
        token = _access_token_for(regular_user)
        await client.patch(
            "/api/v1/users/me",
            json={"display_name": "Alice"},
            headers={"Authorization": f"Bearer {token}"},
        )

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_display_name_can_be_cleared_with_null(
        self, client: AsyncClient, db_session, regular_user: User
    ):
        regular_user.display_name = "Old Name"
        db_session.add(regular_user)
        await db_session.commit()

        token = _access_token_for(regular_user)
        resp = await client.patch(
            "/api/v1/users/me",
            json={"display_name": None},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] is None

    async def test_same_email_as_current_is_a_noop(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        token = _access_token_for(regular_user)
        resp = await client.patch(
            "/api/v1/users/me",
            json={"email": "user@test.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "user@test.com"
        assert fake_email_sender.sent == []

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_email_already_taken_returns_409(
        self, client: AsyncClient, regular_user: User, other_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.patch(
            "/api/v1/users/me",
            json={"email": "taken@test.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

        me_resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me_resp.json()["email"] == "user@test.com"

    async def test_new_email_with_verification_required_stays_pending(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        token = _access_token_for(regular_user)
        resp = await client.patch(
            "/api/v1/users/me",
            json={"email": "new@test.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "user@test.com"  # old email, unchanged

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        change_request = result.scalar_one()
        assert change_request.new_email == "new@test.com"

        assert len(fake_email_sender.sent) == 1
        assert fake_email_sender.sent[0]["to_email"] == "new@test.com"

    async def test_second_email_change_replaces_pending_request(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        token = _access_token_for(regular_user)
        headers = {"Authorization": f"Bearer {token}"}
        await client.patch(
            "/api/v1/users/me", json={"email": "first@test.com"}, headers=headers
        )
        await client.patch(
            "/api/v1/users/me", json={"email": "second@test.com"}, headers=headers
        )

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].new_email == "second@test.com"

    async def test_new_email_with_verification_disabled_applies_immediately(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(settings.base, "require_email_verification", False)

        token = _access_token_for(regular_user)
        resp = await client.patch(
            "/api/v1/users/me",
            json={"email": "instant@test.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "instant@test.com"
        assert fake_email_sender.sent == []

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_email_send_failure_returns_502_and_rolls_back(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        failing_email_sender: _FailingEmailSender,
    ):
        token = _access_token_for(regular_user)
        resp = await client.patch(
            "/api/v1/users/me",
            json={"email": "new@test.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 502

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_extra_field_returns_422(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.patch(
            "/api/v1/users/me",
            json={"display_name": "Alice", "role": "admin"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.patch("/api/v1/users/me", json={"display_name": "Alice"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /users/me/email-change/verify
# ---------------------------------------------------------------------------


async def _start_email_change(
    client: AsyncClient, token: str, new_email: str = "new@test.com"
) -> None:
    resp = await client.patch(
        "/api/v1/users/me",
        json={"email": new_email},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


class TestVerifyEmailChange:
    async def test_valid_code_applies_new_email(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        token = _access_token_for(regular_user)
        await _start_email_change(client, token)
        code = fake_email_sender.sent[0]["code"]

        resp = await client.post(
            "/api/v1/users/me/email-change/verify",
            json={"code": code},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "new@test.com"

        await db_session.refresh(regular_user)
        assert regular_user.email == "new@test.com"

    async def test_valid_code_deletes_pending_request(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        token = _access_token_for(regular_user)
        await _start_email_change(client, token)
        code = fake_email_sender.sent[0]["code"]
        await client.post(
            "/api/v1/users/me/email-change/verify",
            json={"code": code},
            headers={"Authorization": f"Bearer {token}"},
        )

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_no_pending_change_returns_404(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.post(
            "/api/v1/users/me/email-change/verify",
            json={"code": "123456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_wrong_code_returns_400_and_increments_attempts(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        token = _access_token_for(regular_user)
        await _start_email_change(client, token)

        resp = await client.post(
            "/api/v1/users/me/email-change/verify",
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        assert result.scalar_one().attempts == 1

    async def test_expired_code_returns_400(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        token = _access_token_for(regular_user)
        await _start_email_change(client, token)

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        change_request = result.scalar_one()
        change_request.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db_session.add(change_request)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/users/me/email-change/verify",
            json={"code": fake_email_sender.sent[0]["code"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_too_many_attempts_returns_429(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        token = _access_token_for(regular_user)
        await _start_email_change(client, token)

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        change_request = result.scalar_one()
        change_request.attempts = settings.base.verification_max_attempts
        db_session.add(change_request)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/users/me/email-change/verify",
            json={"code": fake_email_sender.sent[0]["code"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 429

    async def test_race_conflict_returns_409_and_deletes_pending_request(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        other_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        """Someone else claims the pending new_email between request and confirm."""
        token = _access_token_for(regular_user)
        await _start_email_change(client, token, new_email="contested@test.com")
        code = fake_email_sender.sent[0]["code"]

        other_user.email = "contested@test.com"
        db_session.add(other_user)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/users/me/email-change/verify",
            json={"code": code},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/users/me/email-change/verify", json={"code": "123456"}
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /users/me/email-change/resend
# ---------------------------------------------------------------------------


class TestResendEmailChange:
    async def test_generates_new_code(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        token = _access_token_for(regular_user)
        await _start_email_change(client, token)
        first_code = fake_email_sender.sent[0]["code"]

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        change_request = result.scalar_one()
        change_request.last_sent_at = datetime.now(UTC) - timedelta(
            seconds=settings.base.verification_resend_cooldown_seconds + 1
        )
        db_session.add(change_request)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/users/me/email-change/resend",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202
        assert len(fake_email_sender.sent) == 2
        assert fake_email_sender.sent[1]["code"] != first_code

    async def test_no_pending_change_returns_404(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.post(
            "/api/v1/users/me/email-change/resend",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_cooldown_active_returns_202_without_sending(
        self,
        client: AsyncClient,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        token = _access_token_for(regular_user)
        await _start_email_change(client, token)
        assert len(fake_email_sender.sent) == 1

        resp = await client.post(
            "/api/v1/users/me/email-change/resend",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202
        assert len(fake_email_sender.sent) == 1

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/me/email-change/resend")
        assert resp.status_code == 401

    async def test_email_send_failure_returns_502(
        self,
        client: AsyncClient,
        db_session,
        regular_user: User,
        fake_email_sender: _FakeEmailSender,
    ):
        token = _access_token_for(regular_user)
        await _start_email_change(client, token)

        result = await db_session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.user_id == regular_user.id
            )
        )
        change_request = result.scalar_one()
        change_request.last_sent_at = datetime.now(UTC) - timedelta(
            seconds=settings.base.verification_resend_cooldown_seconds + 1
        )
        db_session.add(change_request)
        await db_session.commit()

        app.dependency_overrides[get_email_sender] = lambda: _FailingEmailSender()
        try:
            resp = await client.post(
                "/api/v1/users/me/email-change/resend",
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            app.dependency_overrides[get_email_sender] = lambda: fake_email_sender
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# DELETE /users/me
# ---------------------------------------------------------------------------


class TestDeleteAccount:
    async def test_wrong_password_returns_401_and_leaves_account_untouched(
        self, client: AsyncClient, db_session, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.request(
            "DELETE",
            "/api/v1/users/me",
            json={"current_password": "WrongPass#1word"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

        await db_session.refresh(regular_user)
        assert regular_user.is_active is True
        assert regular_user.email == "user@test.com"

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.request(
            "DELETE",
            "/api/v1/users/me",
            json={"current_password": "whatever"},
        )
        assert resp.status_code == 401

    async def test_correct_password_soft_deletes_account(
        self, client: AsyncClient, db_session, regular_user: User
    ):
        original_id = regular_user.id
        token = _access_token_for(regular_user)
        resp = await client.request(
            "DELETE",
            "/api/v1/users/me",
            json={"current_password": "User#Pass1word"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

        await db_session.refresh(regular_user)
        assert regular_user.is_active is False
        assert regular_user.email == f"deleted-{original_id}@barrins.invalid"
        assert regular_user.display_name is None
        assert not verify_password("User#Pass1word", regular_user.hashed_password)

    async def test_old_token_rejected_after_deletion(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        await client.request(
            "DELETE",
            "/api/v1/users/me",
            json={"current_password": "User#Pass1word"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    async def test_original_email_reusable_after_deletion(
        self, client: AsyncClient, db_session, regular_user: User
    ):
        token = _access_token_for(regular_user)
        await client.request(
            "DELETE",
            "/api/v1/users/me",
            json={"current_password": "User#Pass1word"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "user@test.com", "password": "AnotherValid#1"},
        )
        assert resp.status_code == 201

    async def test_extra_field_returns_422(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.request(
            "DELETE",
            "/api/v1/users/me",
            json={"current_password": "User#Pass1word", "injected": "evil"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422
