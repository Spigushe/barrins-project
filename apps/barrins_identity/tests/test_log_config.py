"""Tests for app/core/log_config.py — branch coverage of setup_logging()
and the Windows-safe rotate() override."""

import logging
import uuid
from logging.handlers import RotatingFileHandler

from app.config import settings


def _fresh() -> str:
    return f"test_log_{uuid.uuid4().hex}"


class TestSetupLogging:
    def test_idempotent_when_handlers_exist(self):
        from app.core.log_config import setup_logging

        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        name = _fresh()
        logger1 = setup_logging(name)
        logger2 = setup_logging(name)

        assert logger2 is logger1
        assert len(root_logger.handlers) >= 1

        root_logger.handlers.clear()

    def test_no_console_handler(self, monkeypatch):
        from app.core.log_config import setup_logging

        monkeypatch.setattr(settings.base, "log_to_console", False)
        monkeypatch.setattr(settings.base, "log_to_file", False)
        logger = setup_logging(_fresh())
        assert not any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    def test_no_file_handler(self, monkeypatch):
        from app.core.log_config import setup_logging

        monkeypatch.setattr(settings.base, "log_to_console", True)
        monkeypatch.setattr(settings.base, "log_to_file", False)
        logger = setup_logging(_fresh())
        assert not any(isinstance(h, RotatingFileHandler) for h in logger.handlers)

    def test_file_handler_no_log_dir(self, monkeypatch, tmp_path):
        """log_file_path with no directory component: `if log_dir:` is False."""
        from app.core.log_config import setup_logging

        monkeypatch.setattr(settings.base, "log_to_console", False)
        monkeypatch.setattr(settings.base, "log_to_file", True)
        monkeypatch.setattr(
            settings.base, "log_file_path", "barrins_identity_nodir.log"
        )
        monkeypatch.chdir(tmp_path)
        logger = setup_logging(_fresh())
        assert logger is not None
        (tmp_path / "barrins_identity_nodir.log").unlink(missing_ok=True)


class TestWindowsSafeRotatingFileHandler:
    def test_rotate_copies_source_to_dest_and_truncates(self, tmp_path):
        from app.core.log_config import _WindowsSafeRotatingFileHandler

        source = tmp_path / "app.log"
        dest = tmp_path / "app.log.1"
        source.write_text("log content", encoding="utf-8")

        handler = _WindowsSafeRotatingFileHandler(
            filename=str(source), maxBytes=1024, backupCount=1
        )
        handler.rotate(str(source), str(dest))
        handler.close()

        assert dest.read_text(encoding="utf-8") == "log content"
        assert source.read_text(encoding="utf-8") == ""

    def test_rotate_overwrites_existing_dest(self, tmp_path):
        from app.core.log_config import _WindowsSafeRotatingFileHandler

        source = tmp_path / "app.log"
        dest = tmp_path / "app.log.1"
        source.write_text("new content", encoding="utf-8")
        dest.write_text("old content", encoding="utf-8")

        handler = _WindowsSafeRotatingFileHandler(
            filename=str(source), maxBytes=1024, backupCount=1
        )
        handler.rotate(str(source), str(dest))
        handler.close()

        assert dest.read_text(encoding="utf-8") == "new content"
        assert source.read_text(encoding="utf-8") == ""
