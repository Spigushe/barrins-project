"""Scryfall image client service — implementation selection based on configuration."""

from typing import Annotated

from fastapi import Depends

from app.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.services.scryfall.base import ScryfallClient
from app.services.scryfall.console_client import ConsoleScryfallClient
from app.services.scryfall.http_client import HttpxScryfallClient


def get_scryfall_client() -> ScryfallClient:
    """Return the Scryfall client matching the current configuration.

    Mirrors `app.services.moxfield.get_moxfield_client`'s reasoning:
    silently returning `ConsoleScryfallClient`'s placeholder in production
    would mean every card-image request returns fake art instead of
    failing — so production without `SCRYFALL_USER_AGENT` configured is a
    hard error, not a fallback.
    """
    if settings.base.scryfall_user_agent:
        return HttpxScryfallClient()
    if settings.is_production:
        raise ServiceUnavailableError(
            message="Card image proxy is not configured on this server."
        )
    return ConsoleScryfallClient()


ScryfallClientDep = Annotated[ScryfallClient, Depends(get_scryfall_client)]
