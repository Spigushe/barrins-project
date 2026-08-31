"""ORM model for the `applications` table — the Goblin Guide app directory
(ADR-19).

"Which apps can this user open" is a backend rule (constitution §4.1): the
row carries the access *policy*, `GET /api/v1/applications` computes a
per-caller `access` state, and the SPA only renders cards.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.user import UserRole


class Application(Base):
    """A Barrin's application shown in the Goblin Guide launcher."""

    __tablename__ = "applications"
    __table_args__ = (
        # is_role_restricted ⇒ min_role set AND authentication required.
        CheckConstraint(
            "NOT is_role_restricted OR (min_role IS NOT NULL AND needs_authentication)",
            name="ck_applications_role_restriction_consistent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Stable slug used by clients (logo asset key, current-app filter).
    key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    # Inline SVG markup. Served by the API and rendered by the SPA as an
    # <img> data URI — an <img>-loaded SVG cannot run scripts or fetch, so
    # untrusted markup here still can't XSS the launcher. Kept in the DB so
    # the directory needs no cross-origin asset fetch (ADR-19).
    logo_svg: Mapped[str] = mapped_column(Text, nullable=False)
    needs_authentication: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    is_role_restricted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    # Reuses the existing `userrole` PG enum (see user.py) — no second type.
    min_role: Mapped[UserRole | None] = mapped_column(
        Enum(UserRole, name="userrole"),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
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
