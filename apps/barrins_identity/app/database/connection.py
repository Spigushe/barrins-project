"""Database connection and engine configuration.

Provides the SQLAlchemy engine and session factory, configured from
application settings, and re-exports the declarative Base class for
model definitions.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    str(settings.base.database_url),
    echo=settings.base.database_echo,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class for all ORM models."""

    pass
