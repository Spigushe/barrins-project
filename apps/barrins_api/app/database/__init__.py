"""Database package for connection and session management.

This package centralizes all database-related infrastructure including
engine configuration, session management, and database dependencies.

Exports:
    engine: SQLAlchemy engine instance
    SessionLocal: Session factory for database operations
    get_db: FastAPI dependency for database sessions
    Base: SQLAlchemy declarative base (re-exported for convenience)
"""

from app.database.connection import AsyncSessionLocal, Base, engine
from app.database.session import get_db

__all__ = ["AsyncSessionLocal", "Base", "engine", "get_db"]
