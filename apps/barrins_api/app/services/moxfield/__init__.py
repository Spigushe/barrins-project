"""Moxfield client service — implementation selection based on configuration."""

from typing import Annotated

from fastapi import Depends

from app.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.services.moxfield.base import MoxfieldClient
from app.services.moxfield.console_client import ConsoleMoxfieldClient
from app.services.moxfield.http_client import HttpxMoxfieldClient


def get_moxfield_client() -> MoxfieldClient:
    """Return the Moxfield client matching the current configuration.

    Unlike email (where logging instead of sending is an acceptable
    dev/test fallback), silently returning `ConsoleMoxfieldClient`'s
    sample deck in production would mean a user's import request
    returns fabricated data instead of failing — so production without
    `MOXFIELD_USER_AGENT` configured is a hard error, not a fallback.
    """
    if settings.base.moxfield_user_agent:
        return HttpxMoxfieldClient()
    if settings.is_production:
        raise ServiceUnavailableError(
            message="Moxfield import is not configured on this server."
        )
    return ConsoleMoxfieldClient()


MoxfieldClientDep = Annotated[MoxfieldClient, Depends(get_moxfield_client)]
