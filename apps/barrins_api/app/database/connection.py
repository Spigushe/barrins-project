"""Database connection and engine configuration.

This module provides the SQLAlchemy engine and session factory,
configured from application settings. It also re-exports the
declarative Base class for model definitions.

Attributes:
    engine: SQLAlchemy engine instance
    SessionLocal: Session factory for creating database sessions
    Base: SQLAlchemy declarative base class
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Create SQLAlchemy engine
engine = create_async_engine(
    str(settings.base.database_url),
    echo=settings.base.database_echo,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,  # Connection pool size
    max_overflow=10,  # Max overflow connections
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class for all ORM models."""

    pass
