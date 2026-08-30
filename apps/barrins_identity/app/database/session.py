"""Database session management and FastAPI dependencies."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that provides a database session.

    Yields a database session and ensures proper cleanup after request.
    """
    async with AsyncSessionLocal() as session:
        yield session


DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
