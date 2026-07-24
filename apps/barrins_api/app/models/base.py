"""SQLAlchemy base models, mixins, and column helpers.

This module provides reusable mixins for common patterns (UUID IDs,
timestamps), and helper functions for creating typed columns.
The Base class and database connection are managed in app.database.

Classes:
    JSONBCompat: Cross-database JSON/JSONB column type
    IDUuidMixin: Mixin providing UUID primary key with validation
    TimestampMixin: Mixin providing created_at/updated_at timestamps

Functions:
    uuid_column: Create a UUID column (primary or regular)
    uuid_fk_column: Create a UUID foreign key column
    enum_column: Create an enum column with constraints
    jsonb_column: Create a JSON/JSONB compatible column
"""

# Import Base from database module
from app.database import Base


class IDUuidMixin:
    """Mixin for UUID primary key.

    Provides a standard UUID primary key column named 'id' with validation.
    """

    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps.

    Provides automatic timestamping of record creation and updates.
    """

    pass


__all__ = ["Base", "IDUuidMixin", "TimestampMixin"]
