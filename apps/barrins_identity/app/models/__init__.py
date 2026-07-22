"""Central model registry for SQLAlchemy ORM models.

This module serves as the central import point for all database models,
ensuring they are registered with SQLAlchemy's metadata before database
operations (used by Alembic's env.py and by tests/conftest.py).
"""

from app.database import Base
from app.models._types import JSONBCompat, JsonValue, jsonb_column
from app.models.app_settings import AppKey, AppSettings
from app.models.email_change_request import EmailChangeRequest
from app.models.email_verification import EmailVerification
from app.models.password_reset import PasswordResetCode
from app.models.service_account import ServiceAccount
from app.models.user import User, UserRole

__all__ = [
    "AppKey",
    "AppSettings",
    "Base",
    "EmailChangeRequest",
    "EmailVerification",
    "JSONBCompat",
    "JsonValue",
    "PasswordResetCode",
    "ServiceAccount",
    "User",
    "UserRole",
    "jsonb_column",
]

metadata = Base.metadata
