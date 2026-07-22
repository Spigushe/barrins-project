"""ORM model for the `auth_email_change_requests` table (platform.md §16)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailChangeRequest(Base):
    """Pending email change for an account.

    One pending change per user (`UNIQUE(user_id)`) — a new `PATCH
    /users/me` with another address before confirming replaces the
    pending row, same "resend replaces" precedent as `EmailVerification`.
    `users.email` is left untouched until the code is confirmed (the old
    address stays authoritative — platform.md §16.2).
    """

    __tablename__ = "auth_email_change_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    new_email: Mapped[str] = mapped_column(String(255), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    last_sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
