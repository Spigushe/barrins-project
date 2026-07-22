"""Tests for app/models/ — 100% coverage target (tests.md §1)."""

import uuid
from datetime import UTC, datetime, timedelta

from app.models.app_settings import AppKey, AppSettings
from app.models.email_change_request import EmailChangeRequest
from app.models.email_verification import EmailVerification
from app.models.password_reset import PasswordResetCode
from app.models.service_account import ServiceAccount
from app.models.user import User, UserRole


class TestUserRoleLevel:
    def test_user_level(self):
        assert UserRole.user.level == 1

    def test_moderator_level(self):
        assert UserRole.moderator.level == 2

    def test_ml_developer_level(self):
        assert UserRole.ml_developer.level == 3

    def test_admin_level(self):
        assert UserRole.admin.level == 4

    def test_str_value(self):
        assert UserRole.admin == "admin"
        assert UserRole.user == "user"


class TestUserModel:
    async def test_defaults_after_flush(self, db_session):
        """Column defaults (role, is_active, is_verified, token_version) are
        applied by SQLAlchemy at flush time, not at __init__ — see
        db_session-backed assertion here rather than a bare constructor
        check."""
        user = User(email="a@example.com", hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        assert user.role == UserRole.user
        assert user.is_active is True
        assert user.is_verified is False
        assert user.token_version == 0
        assert user.display_name is None

    def test_explicit_id(self):
        user_id = uuid.uuid4()
        user = User(id=user_id, email="b@example.com", hashed_password="hashed")
        assert user.id == user_id


class TestServiceAccountModel:
    async def test_defaults_after_flush(self, db_session):
        account = ServiceAccount(
            client_id="sa_test",
            hashed_client_secret="hashed",
            scopes=["tolaria:read"],
        )
        db_session.add(account)
        await db_session.flush()
        await db_session.refresh(account)

        assert account.is_active is True
        assert account.token_version == 0
        assert account.description is None
        assert account.scopes == ["tolaria:read"]

    def test_explicit_id(self):
        account_id = uuid.uuid4()
        account = ServiceAccount(
            id=account_id,
            client_id="sa_test2",
            hashed_client_secret="hashed",
            scopes=[],
        )
        assert account.id == account_id


class TestEmailVerificationModel:
    async def test_defaults_after_flush(self, db_session):
        user = User(email="c@example.com", hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        verification = EmailVerification(
            user_id=user.id,
            code_hash="deadbeef",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        db_session.add(verification)
        await db_session.flush()
        await db_session.refresh(verification)

        assert verification.attempts == 0

    def test_explicit_id(self):
        verification_id = uuid.uuid4()
        verification = EmailVerification(
            id=verification_id,
            user_id=uuid.uuid4(),
            code_hash="deadbeef",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        assert verification.id == verification_id


class TestPasswordResetCodeModel:
    async def test_defaults_after_flush(self, db_session):
        user = User(email="reset@example.com", hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        reset_code = PasswordResetCode(
            user_id=user.id,
            code_hash="deadbeef",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        db_session.add(reset_code)
        await db_session.flush()
        await db_session.refresh(reset_code)

        assert reset_code.attempts == 0

    def test_explicit_id(self):
        reset_id = uuid.uuid4()
        reset_code = PasswordResetCode(
            id=reset_id,
            user_id=uuid.uuid4(),
            code_hash="deadbeef",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        assert reset_code.id == reset_id


class TestEmailChangeRequestModel:
    async def test_defaults_after_flush(self, db_session):
        user = User(email="changer@example.com", hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        change_request = EmailChangeRequest(
            user_id=user.id,
            new_email="new@example.com",
            code_hash="deadbeef",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        db_session.add(change_request)
        await db_session.flush()
        await db_session.refresh(change_request)

        assert change_request.attempts == 0
        assert change_request.new_email == "new@example.com"

    def test_explicit_id(self):
        request_id = uuid.uuid4()
        change_request = EmailChangeRequest(
            id=request_id,
            user_id=uuid.uuid4(),
            new_email="new@example.com",
            code_hash="deadbeef",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        assert change_request.id == request_id


class TestAppKeyEnum:
    def test_members(self):
        assert AppKey.tamiyo_scroll == "tamiyo_scroll"
        assert AppKey.tolaria_news == "tolaria_news"


class TestAppSettingsModel:
    async def test_defaults_after_flush(self, db_session):
        user = User(email="settings@example.com", hashed_password="hashed")
        db_session.add(user)
        await db_session.flush()

        row = AppSettings(user_id=user.id, app_key=AppKey.tamiyo_scroll.value)
        db_session.add(row)
        await db_session.flush()
        await db_session.refresh(row)

        assert row.data == {}

    def test_explicit_id(self):
        row_id = uuid.uuid4()
        row = AppSettings(
            id=row_id,
            user_id=uuid.uuid4(),
            app_key=AppKey.tamiyo_scroll.value,
            data={"data_shared": True},
        )
        assert row.id == row_id
        assert row.data == {"data_shared": True}
