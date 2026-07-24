"""Email sending service — implementation selection based on configuration."""

from typing import Annotated

from fastapi import Depends

from app.config import settings
from app.services.email.base import EmailSender
from app.services.email.console_sender import ConsoleEmailSender
from app.services.email.smtp_sender import SMTPEmailSender


def get_email_sender() -> EmailSender:
    """Return the email sender matching the current configuration.

    `smtp_host` set → `SMTPEmailSender` (production/staging).
    `smtp_host` empty → `ConsoleEmailSender` (dev/test — `BaseAppSettings`
    already forbids an empty `smtp_host` in production, cf. `app/config/base.py`).
    """
    if settings.base.smtp_host:
        return SMTPEmailSender()
    return ConsoleEmailSender()


# FastAPI dependency — overridable in tests via app.dependency_overrides,
# following the pattern of DatabaseSession (app/database/session.py).
EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]

__all__ = [
    "ConsoleEmailSender",
    "EmailSender",
    "EmailSenderDep",
    "SMTPEmailSender",
    "get_email_sender",
]
