"""Pydantic schemas for service-account (machine-to-machine) authentication."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ServiceAccountCreate(BaseModel):
    """Payload for POST /service-accounts (admin-only)."""

    model_config = ConfigDict(extra="forbid")

    description: str | None = None
    scopes: list[str] = Field(min_length=1)


class ServiceAccountRead(BaseModel):
    """Public representation of a service account (never the secret)."""

    id: UUID
    client_id: str
    description: str | None = None
    scopes: list[str]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceAccountCreated(ServiceAccountRead):
    """Response of POST /service-accounts — includes the plaintext secret.

    The secret is shown exactly once, at creation time; it is never
    retrievable afterwards (only its Argon2id hash is stored).
    """

    client_secret: str


class ServiceTokenRequest(BaseModel):
    """Body of POST /service-token (client_credentials-style exchange)."""

    model_config = ConfigDict(extra="forbid")

    client_id: str
    client_secret: str


class ServiceTokenResponse(BaseModel):
    """Response of POST /service-token."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int  # seconds
