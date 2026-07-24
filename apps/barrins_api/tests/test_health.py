"""Tests for the /health endpoint (app/api/health.py)."""

from collections.abc import AsyncGenerator

from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import get_db
from app.main import app


class _BrokenSession:
    """Stand-in DB session whose queries always fail."""

    async def execute(self, *args: object, **kwargs: object) -> None:
        raise SQLAlchemyError("simulated database outage")


class _UnreachableSession:
    """Stand-in DB session simulating a failure to even establish a
    connection (e.g. auth rejected, connection refused) — this raises
    the raw driver/OS exception, not a SQLAlchemyError, since SQLAlchemy
    only wraps failures that occur after a connection is already open."""

    async def execute(self, *args: object, **kwargs: object) -> None:
        raise ConnectionRefusedError("simulated connection failure")


async def _broken_get_db() -> AsyncGenerator[_BrokenSession]:
    yield _BrokenSession()


async def _unreachable_get_db() -> AsyncGenerator[_UnreachableSession]:
    yield _UnreachableSession()


async def test_health_ok(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_db_down_returns_503(client: AsyncClient):
    app.dependency_overrides[get_db] = _broken_get_db
    try:
        response = await client.get("/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


async def test_health_db_unreachable_returns_503(client: AsyncClient):
    app.dependency_overrides[get_db] = _unreachable_get_db
    try:
        response = await client.get("/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
