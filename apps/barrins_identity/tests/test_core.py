"""Tests for app.main (lifespan, root redirect) and app.database.session."""

from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestMain:
    async def test_read_root_redirects(self, client: AsyncClient):
        response = await client.get("/", follow_redirects=False)
        assert response.status_code == 301
        assert response.headers["location"] == "/docs"

    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_lifespan_startup_and_shutdown(self):
        from app.main import app, lifespan

        async with lifespan(app):
            pass


class TestGetDb:
    async def test_get_db_yields_session(self):
        from app.database.session import get_db

        mock_session = AsyncMock(spec=AsyncSession)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.session.AsyncSessionLocal", return_value=mock_ctx):
            yielded = []
            async for s in get_db():
                yielded.append(s)

        assert len(yielded) == 1
        assert yielded[0] is mock_session
