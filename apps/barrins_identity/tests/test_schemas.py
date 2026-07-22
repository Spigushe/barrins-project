"""Tests for app/schemas/ — 100% coverage target (tests.md §1)."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    PASSWORD_RULE,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ServiceTokenData,
    SignupResponse,
    TokenData,
    TokenPair,
    UserCreate,
    UserRead,
    UserSignup,
    VerifyEmailRequest,
)
from app.schemas.service_account import (
    ServiceAccountCreate,
    ServiceAccountCreated,
    ServiceAccountRead,
    ServiceTokenRequest,
    ServiceTokenResponse,
)

# ===========================================================================
# PasswordStr / UserCreate
# ===========================================================================


class TestPasswordStr:
    def test_valid_password_accepted(self):
        user = UserCreate(email="a@example.com", password="ValidPass#1word")
        assert user.password == "ValidPass#1word"

    def test_too_short_rejected(self):
        with pytest.raises(ValidationError, match=PASSWORD_RULE):
            UserCreate(email="a@example.com", password="Short#1")

    def test_missing_symbol_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(email="a@example.com", password="NoSymbolPass1word")

    def test_missing_digit_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(email="a@example.com", password="NoDigitPass#word")

    def test_missing_uppercase_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(email="a@example.com", password="nouppercase#1word")

    def test_missing_lowercase_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(email="a@example.com", password="NOLOWERCASE#1WORD")


class TestUserCreate:
    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate.model_validate(
                {
                    "email": "a@example.com",
                    "password": "ValidPass#1word",
                    "injected": "evil",
                }
            )

    def test_defaults(self):
        user = UserCreate(email="a@example.com", password="ValidPass#1word")
        assert user.role == "user"
        assert user.is_verified is False
        assert user.display_name is None


class TestUserRead:
    def test_from_attributes(self):
        fake_user = SimpleNamespace(
            id=uuid.uuid4(),
            email="a@example.com",
            role="user",
            is_active=True,
            is_verified=True,
            display_name="Alice",
        )
        read = UserRead.model_validate(fake_user)
        assert read.email == "a@example.com"


# ===========================================================================
# Token schemas
# ===========================================================================


class TestTokenData:
    def test_construction(self):
        data = TokenData(
            sub=str(uuid.uuid4()), role="admin", email="a@example.com", token_version=1
        )
        assert data.role == "admin"


class TestServiceTokenData:
    def test_construction(self):
        data = ServiceTokenData(sub="sa_abc", scopes=["x:read"], token_version=0)
        assert data.scopes == ["x:read"]


# ===========================================================================
# Service-account schemas
# ===========================================================================


class TestServiceAccountCreate:
    def test_requires_at_least_one_scope(self):
        with pytest.raises(ValidationError):
            ServiceAccountCreate(scopes=[])

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            ServiceAccountCreate.model_validate(
                {"scopes": ["x:read"], "injected": "evil"}
            )

    def test_valid(self):
        payload = ServiceAccountCreate(description="Tolaria", scopes=["tolaria:read"])
        assert payload.scopes == ["tolaria:read"]


class TestServiceAccountRead:
    def test_from_attributes(self):
        fake_account = SimpleNamespace(
            id=uuid.uuid4(),
            client_id="sa_abc",
            description=None,
            scopes=["x:read"],
            is_active=True,
            created_at=datetime.now(UTC),
        )
        read = ServiceAccountRead.model_validate(fake_account)
        assert read.client_id == "sa_abc"


class TestServiceAccountCreated:
    def test_includes_secret(self):
        created = ServiceAccountCreated(
            id=uuid.uuid4(),
            client_id="sa_abc",
            description=None,
            scopes=["x:read"],
            is_active=True,
            created_at=datetime.now(UTC),
            client_secret="plaintext-secret",
        )
        assert created.client_secret == "plaintext-secret"


class TestServiceTokenRequest:
    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            ServiceTokenRequest.model_validate(
                {"client_id": "sa_abc", "client_secret": "x", "injected": "evil"}
            )

    def test_valid(self):
        req = ServiceTokenRequest(client_id="sa_abc", client_secret="x")
        assert req.client_id == "sa_abc"


class TestServiceTokenResponse:
    def test_defaults(self):
        resp = ServiceTokenResponse(access_token="tok", expires_in=900)
        assert resp.token_type == "bearer"


# ===========================================================================
# Self-registration & email verification schemas
# ===========================================================================


class TestUserSignup:
    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            UserSignup.model_validate(
                {
                    "email": "a@example.com",
                    "password": "ValidPass#1word",
                    "role": "admin",
                }
            )

    def test_valid(self):
        payload = UserSignup(email="a@example.com", password="ValidPass#1word")
        assert payload.display_name is None


class TestSignupResponse:
    def test_defaults(self):
        resp = SignupResponse()
        assert resp.verification_required is True
        assert resp.tokens is None

    def test_with_tokens(self):
        resp = SignupResponse(
            verification_required=False,
            tokens=TokenPair(access_token="a", refresh_token="b"),
        )
        assert resp.tokens is not None


class TestVerifyEmailRequest:
    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            VerifyEmailRequest.model_validate(
                {"email": "a@example.com", "code": "123456", "injected": "evil"}
            )

    def test_invalid_code_pattern_rejected(self):
        with pytest.raises(ValidationError):
            VerifyEmailRequest(email="a@example.com", code="abc123")

    def test_valid(self):
        req = VerifyEmailRequest(email="a@example.com", code="123456")
        assert req.code == "123456"


class TestResendVerificationRequest:
    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            ResendVerificationRequest.model_validate(
                {"email": "a@example.com", "injected": "evil"}
            )

    def test_valid(self):
        req = ResendVerificationRequest(email="a@example.com")
        assert req.email == "a@example.com"


class TestResendVerificationResponse:
    def test_default_message(self):
        resp = ResendVerificationResponse()
        assert "If an account exists" in resp.detail
