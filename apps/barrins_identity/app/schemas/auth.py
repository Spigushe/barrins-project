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
# User schemas
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    """Payload for POST /auth/register (admin-only, platform.md §8).

    extra="forbid": defense in depth — any unknown key produces HTTP 422
    (also catches a role-escalation attempt via an undeclared field).
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: PasswordStr
    role: UserRole = UserRole.user
    is_verified: bool = False
    display_name: str | None = None


class UserRead(BaseModel):
    """Public representation of a user (without password)."""

    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    is_verified: bool
    display_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# JWT schemas
# ---------------------------------------------------------------------------


class TokenPair(BaseModel):
    """Pair of tokens returned by POST /auth/token and POST /auth/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105


class RefreshRequest(BaseModel):
    """Body of POST /auth/refresh."""

    refresh_token: str


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
