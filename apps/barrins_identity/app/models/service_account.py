"""ORM model for machine-to-machine service accounts (client_credentials)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._types import JSONBCompat


class ServiceAccount(Base):
    """SQLAlchemy model for the `service_accounts` table.

    `client_id` is the public identifier used in the `client_credentials`
    flow (POST /service-token). `hashed_client_secret` uses the same
    Argon2id mechanism as user passwords (platform.md §7) — the plaintext
    secret is only ever returned once, at creation time.
    """

    __tablename__ = "service_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_client_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Declared as list[str] (its actual runtime shape — always assigned a
    # list of scope strings), stored as JSON via JSONBCompat.
    scopes: Mapped[list[str]] = mapped_column(JSONBCompat, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    token_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
