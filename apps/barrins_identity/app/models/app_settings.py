"""ORM model for the `app_settings` table — per-app opaque settings blob
(platform.md §17)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._types import JSONBCompat, JsonValue


class AppKey(enum.StrEnum):
    """Fixed set of Barrin's applications that may store settings here.

    Not a Postgres native `ENUM` type (see `AppSettings.app_key`) — this
    is an API-level allow-list, not a database-level constraint, so a new
    app can be added without an `ALTER TYPE` migration.
    """

    tamiyo_scroll = "tamiyo_scroll"
    tolaria_news = "tolaria_news"


class AppSettings(Base):
    """A user's opaque settings blob for one Barrin's app.

    `barrins_identity` stores and serves `data` verbatim — it validates
    nothing about its internal shape beyond overall size (enforced in the
    route handler, not here). Each consuming app owns its own schema for
    what the blob contains (platform.md §17.1).
    """

    __tablename__ = "app_settings"
    __table_args__ = (UniqueConstraint("user_id", "app_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Plain String, not a Postgres ENUM — see AppKey docstring.
    app_key: Mapped[str] = mapped_column(String(64), nullable=False)
    # Declared as dict[str, JsonValue] (its actual runtime shape — always a
    # JSON object, same precedent as ServiceAccount.scopes), stored as JSON
    # via JSONBCompat.
    data: Mapped[dict[str, JsonValue]] = mapped_column(
        JSONBCompat, default=dict, nullable=False
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
