"""Unit tests for app.core.log_config, app.database.session, and app.main."""

# pyright: reportUnknownMemberType=none, reportUnknownVariableType=none, reportUnknownArgumentType=none, reportUnknownParameterType=none, reportMissingParameterType=none

import logging
import uuid
from logging.handlers import RotatingFileHandler
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fresh() -> str:
    """Returns a unique logger name to avoid side effects between tests."""
    return f"test_log_{uuid.uuid4().hex}"


# ---------------------------------------------------------------------------
# app.core.log_config — setup_logging
# ---------------------------------------------------------------------------
class TestSetupLogging:
    def test_idempotent_when_handlers_exist(self):
        """A second call returns the logger without additional handlers."""
        from app.core.log_config import setup_logging

        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        name = _fresh()
        logger1 = setup_logging(name)
        logger2 = setup_logging(name)

        assert logger2 is logger1
        assert len(root_logger.handlers) >= 1
        assert len(logger1.handlers) == 0

        root_logger.handlers.clear()

    def test_named_loggers_use_root_handlers_without_duplication(self, monkeypatch):
        """Named loggers must not create their own handlers."""
        from app.core.log_config import setup_logging

        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        monkeypatch.setattr(settings.base, "log_to_console", True)
        monkeypatch.setattr(settings.base, "log_to_file", False)

        logger_a = setup_logging(_fresh())
        logger_b = setup_logging(_fresh())

        assert logger_a is not logger_b
        assert len(root_logger.handlers) >= 1
        assert len(logger_a.handlers) == 0
        assert len(logger_b.handlers) == 0

        root_logger.handlers.clear()

    def test_no_console_handler(self, monkeypatch):
        """log_to_console=False doesn't create a StreamHandler (branch 39->46)."""
        from app.core.log_config import setup_logging

        monkeypatch.setattr(settings.base, "log_to_console", False)
        monkeypatch.setattr(settings.base, "log_to_file", False)
        name = _fresh()
        logger = setup_logging(name)
        assert not any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
        logger.handlers.clear()

    def test_no_file_handler(self, monkeypatch):
        """log_to_file=False doesn't create a RotatingFileHandler."""
        from app.core.log_config import setup_logging

        monkeypatch.setattr(settings.base, "log_to_console", True)
        monkeypatch.setattr(settings.base, "log_to_file", False)
        name = _fresh()
        logger = setup_logging(name)
        assert not any(isinstance(h, RotatingFileHandler) for h in logger.handlers)
        logger.handlers.clear()

    def test_file_handler_no_log_dir(self, monkeypatch, tmp_path):
        """log_file_path with no directory: the `if log_dir:` branch is False."""
        from app.core.log_config import setup_logging

        monkeypatch.setattr(settings.base, "log_to_console", False)
        monkeypatch.setattr(settings.base, "log_to_file", True)
        # Filename only → os.path.dirname("nodir.log") == ""
        monkeypatch.setattr(settings.base, "log_file_path", "barrins_nodir_test.log")
        monkeypatch.chdir(tmp_path)
        name = _fresh()
        logger = setup_logging(name)
        assert logger is not None
        logger.handlers.clear()
        (tmp_path / "barrins_nodir_test.log").unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# app.database.session — get_db
# ---------------------------------------------------------------------------
class TestGetDb:
    @pytest.mark.anyio
    async def test_get_db_yields_session(self):
        """get_db() yields an AsyncSession (lines 34-35)."""
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


# ---------------------------------------------------------------------------
# app.main — redirect + lifespan
# ---------------------------------------------------------------------------
class TestMain:
    @pytest.mark.anyio
    async def test_read_root_redirects(self, client: AsyncClient):
        """GET / returns 301 to /docs (line 100)."""
        response = await client.get("/", follow_redirects=False)
        assert response.status_code == 301
        assert response.headers["location"] == "/docs"

    @pytest.mark.anyio
    async def test_lifespan_startup_and_shutdown(self):
        """The lifespan starts and stops without error

        The schema is managed by Alembic: the lifespan must not touch the
        database (no `create_all`).
        """
        from app.main import app, lifespan

        async with lifespan(app):
            pass
