"""Central model registry for SQLAlchemy ORM models.

This module serves as the central import point for all database models,
ensuring they are registered with SQLAlchemy's metadata before database
operations.

Exports:
    Base: SQLAlchemy declarative base
    IDUuidMixin: UUID primary key mixin
    TimestampMixin: created_at / updated_at mixin
    metadata: SQLAlchemy MetaData object for all registered models
"""

from app.database import Base
from app.models._types import JSONBCompat, JsonValue, jsonb_column
from app.models.base import IDUuidMixin, TimestampMixin
from app.models.email_verification import EmailVerification
from app.models.tamiyo_scroll import (
    ArchetypeCategory,
    DecklistVersionSource,
    ExpectedLevel,
    GameResult,
    TSCardTest,
    TSMatch,
    TSMetaDeck,
    TSPersonalDeck,
    TSPersonalDecklistVersion,
    TSUserSettings,
)
from app.models.user import User, UserRole

__all__ = [
    "ArchetypeCategory",
    "Base",
    "DecklistVersionSource",
    "EmailVerification",
    "ExpectedLevel",
    "GameResult",
    "IDUuidMixin",
    "JSONBCompat",
    "JsonValue",
    "TSCardTest",
    "TSMatch",
    "TSMetaDeck",
    "TSPersonalDeck",
    "TSPersonalDecklistVersion",
    "TSUserSettings",
    "TimestampMixin",
    "User",
    "UserRole",
    "jsonb_column",
]

metadata = Base.metadata
