"""Logging configuration with file rotation.

Copied from apps/barrins_api/app/core/log_config.py — generic infra.
"""

import logging
import os
import shutil
from logging.handlers import RotatingFileHandler

from app.config import settings


class _WindowsSafeRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler compatible with Windows.

    On Windows, os.rename fails if the file is open in any process. Rotation
    is replaced by copy2 + truncate: the destination file receives the
    current content, then the source is emptied in place without being
    renamed — existing handles remain valid.
    """

    def rotate(self, source: str, dest: str) -> None:
        if os.path.exists(dest):
            os.remove(dest)
        shutil.copy2(source, dest)
        with open(source, "w", encoding="utf-8"):
            pass


def _configure_root_logger() -> logging.Logger:
    """Configure the root logger once, with its global handlers."""
    root_logger = logging.getLogger()

    if root_logger.handlers:
        return root_logger

    root_logger.setLevel(getattr(logging, settings.base.log_level))

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if settings.base.log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, settings.base.log_level))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if settings.base.log_to_file:
        log_dir = os.path.dirname(settings.base.log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = _WindowsSafeRotatingFileHandler(
            filename=settings.base.log_file_path,
            maxBytes=settings.base.log_max_bytes,
            backupCount=settings.base.log_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, settings.base.log_level))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def setup_logging(logger_name: str | None = None) -> logging.Logger:
    """Configure the logging system with file rotation."""
    _configure_root_logger()
    logger = logging.getLogger(logger_name)

    logger.setLevel(getattr(logging, settings.base.log_level))
    logger.propagate = True

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger configured for a specific module."""
    return setup_logging(name)


app_logger = setup_logging("app")
