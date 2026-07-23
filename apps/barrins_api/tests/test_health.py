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


async def _broken_get_db() -> AsyncGenerator[_BrokenSession]:
    yield _BrokenSession()


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
