"""Central model registry for SQLAlchemy ORM models.

This module serves as the central import point for all database models,
ensuring they are registered with SQLAlchemy's metadata before database
operations (used by Alembic's env.py and by tests/conftest.py).
"""

from app.database import Base
from app.models._types import JSONBCompat, JsonValue, jsonb_column
from app.models.service_account import ServiceAccount
from app.models.user import User, UserRole

__all__ = [
    "Base",
    "JSONBCompat",
    "JsonValue",
    "ServiceAccount",
    "User",
    "UserRole",
    "jsonb_column",
]

metadata = Base.metadata
