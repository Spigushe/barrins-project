"""Pydantic schemas for user authentication."""

import re
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole

# ---------------------------------------------------------------------------
# Password complexity rules
# ---------------------------------------------------------------------------
# Single source of truth — shareable with consumers via GET /openapi.json.
# Pydantic v2's Rust engine doesn't support look-arounds; Field(pattern=...)
# is reserved for OpenAPI exposure, actual validation goes through
# AfterValidator.
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])"  # >= 1 lowercase
    r"(?=.*[A-Z])"  # >= 1 uppercase
    r"(?=.*\d)"  # >= 1 digit
    r"(?=.*[^\w\s])"  # >= 1 symbol (note: _ excluded since it's included in \w)
    r".{12,}$"
)
PASSWORD_RULE = (
    "At least 12 characters with 1 uppercase, 1 lowercase, 1 digit, and 1 symbol."  # noqa: S105
)


def _check_password_complexity(v: str) -> str:
    if not PASSWORD_PATTERN.fullmatch(v):
        raise ValueError(PASSWORD_RULE)
    return v


PasswordStr = Annotated[
    str,
    Field(
        json_schema_extra={
            "pattern": PASSWORD_PATTERN.pattern,
            "description": PASSWORD_RULE,
        }
    ),
    AfterValidator(_check_password_complexity),
]

# ---------------------------------------------------------------------------
# Username rules (constitution §13.2, ADR-17 / platform.md Q-03)
# ---------------------------------------------------------------------------
# 3-32 chars, ASCII letters/digits plus `_` and `-`. Same "single source of
# truth, exposed via GET /openapi.json" pattern as PASSWORD_PATTERN. A plain
# character class has no look-arounds, so Field(pattern=...) both documents
# and enforces it here (unlike the password rule).
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
USERNAME_RULE = "3-32 characters: letters, digits, underscore or hyphen only."

UsernameStr = Annotated[
    str,
    Field(pattern=USERNAME_PATTERN.pattern, description=USERNAME_RULE),
]

# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    """Payload for POST /auth/register (admin-only, platform.md §8).

    extra="forbid": defense in depth — any unknown key produces HTTP 422
    (also catches a role-escalation attempt via an undeclared field).
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    username: UsernameStr
    password: PasswordStr
    role: UserRole = UserRole.user
    is_verified: bool = False
    display_name: str | None = None


class UserSignup(BaseModel):
    """Self-registration payload (POST /auth/signup).

    Deliberately restricted subset of UserCreate:
    - `role` absent -> forced to UserRole.user server-side (no escalation).
    - `is_verified` absent -> forced to False server-side.
    - `extra="forbid"` -> explicit HTTP 422 if an undeclared field is sent
      (detects a role-escalation attempt even if the handler would block it).
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    username: UsernameStr
    password: PasswordStr
    display_name: str | None = None


class UserRead(BaseModel):
    """Public representation of a user (without password)."""

    id: UUID
    email: EmailStr
    username: str
    role: UserRole
    is_active: bool
    is_verified: bool
    display_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# JWT schemas
# ---------------------------------------------------------------------------


class TokenPair(BaseModel):
    """Pair of tokens returned by POST /auth/token and POST /auth/refresh.

    In cookie mode (ADR-18) `refresh_token` is `None` — the token is in an
    HttpOnly cookie instead — and the routes serialize with
    `response_model_exclude_none=True` so the key is omitted entirely.
    """

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"  # noqa: S105


class RefreshRequest(BaseModel):
    """Body of POST /auth/refresh.

    Optional: in cookie mode the refresh token comes from the HttpOnly
    cookie and the body is absent.
    """

    refresh_token: str | None = None


class TokenData(BaseModel):
    """Decoded content of a user token's JWT payload (internal claims)."""

    sub: str  # user UUID (str)
    role: UserRole
    email: EmailStr
    token_version: int  # claim "tkv" — revocation check


class ServiceTokenData(BaseModel):
    """Decoded content of a service-account token's JWT payload."""

    sub: str  # client_id
    scopes: list[str]
    token_version: int  # claim "tkv" — revocation check


# ---------------------------------------------------------------------------
# Self-registration & email verification schemas
# ---------------------------------------------------------------------------


class SignupResponse(BaseModel):
    """Response of POST /auth/signup.

    `verification_required=True` (default): unverified account created, code
    sent by email, `tokens` absent — the client must go through
    POST /auth/signup/verify. `verification_required=False`
    (`REQUIRE_EMAIL_VERIFICATION=false`): account already verified, `tokens`
    present — the client is logged in immediately, no additional call needed.
    """

    detail: str = "Account created. Check your inbox to activate your account."
    verification_required: bool = True
    tokens: TokenPair | None = None


class VerifyEmailRequest(BaseModel):
    """Payload of POST /auth/signup/verify."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$", description="6-digit code received by email.")


class ResendVerificationRequest(BaseModel):
    """Payload of POST /auth/signup/resend."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class ResendVerificationResponse(BaseModel):
    """Generic response of POST /auth/signup/resend.

    The message never varies based on whether the account exists
    (constitution §23.2 — anti-enumeration).
    """

    detail: str = "If an account exists for this address, a new code has been sent."


# ---------------------------------------------------------------------------
# Password reset schemas (platform.md §14)
# ---------------------------------------------------------------------------


class PasswordResetRequest(BaseModel):
    """Payload of POST /auth/password-reset/request."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class PasswordResetRequestResponse(BaseModel):
    """Generic response of POST /auth/password-reset/request.

    The message never varies based on whether the account exists, is
    active, or has a pending reset already (anti-enumeration, same
    pattern as `ResendVerificationResponse`).
    """

    detail: str = "If an account exists for this address, a reset code has been sent."


class PasswordResetConfirm(BaseModel):
    """Payload of POST /auth/password-reset/confirm."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$", description="6-digit code received by email.")
    new_password: PasswordStr
