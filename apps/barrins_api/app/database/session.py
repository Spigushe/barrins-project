"""Database session management and FastAPI dependencies.

This module provides utility functions for managing database sessions,
particularly for use as FastAPI dependencies.

Functions:
    get_db: FastAPI dependency that provides a database session
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that provides a database session.

    Yields a database session and ensures proper cleanup after request.
    Use this as a dependency in FastAPI route handlers:

    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()

    Yields:
        AsyncSession: SQLAlchemy asynchronous database session
    """
    async with AsyncSessionLocal() as session:
        yield session


# Type alias for convenience
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
