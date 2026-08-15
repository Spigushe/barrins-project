"""Real Scryfall client — fetches one card's image over HTTPS.

`GET /cards/{scryfall_id}?format=image&version=normal` 302-redirects to
the actual image asset; `follow_redirects=True` returns the image bytes
directly instead of the redirect response. No API key/registration is
required, only a descriptive `User-Agent` per Scryfall's API etiquette
(https://scryfall.com/docs/api) — unlike Moxfield's, this isn't a
revocable per-app secret, just a courtesy identifier.
"""

import asyncio
import time
from typing import Literal

import httpx

from app.config import settings
from app.core.exceptions import ExternalServiceError, ResourceNotFoundError
from app.core.log_config import get_logger
from app.services.scryfall.base import ScryfallImageFetch

logger = get_logger(__name__)

_API_BASE = "https://api.scryfall.com/cards"
# Scryfall's stated courtesy limit is ~10 requests/second (50-100ms apart).
_MIN_SECONDS_BETWEEN_REQUESTS = 0.1

# Module-level (not per-instance) so the rate cap holds across every
# request/instance sharing this process — see fetch_card_image.
_rate_limit_lock = asyncio.Lock()
_last_request_monotonic: float | None = None


class HttpxScryfallClient:
    """Fetches a card image via Scryfall's public API, rate-limited."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        # `transport` is only ever overridden by tests (httpx.MockTransport),
        # to avoid any real network call.
        self._transport = transport

    async def fetch_card_image(
        self, scryfall_id: str, face: Literal["front", "back"] = "front"
    ) -> ScryfallImageFetch:
        await self._wait_for_rate_limit()

        headers = {"User-Agent": settings.base.scryfall_user_agent or ""}
        params = {"format": "image", "version": "normal", "face": face}

        try:
            async with httpx.AsyncClient(
                timeout=10.0, transport=self._transport, follow_redirects=True
            ) as http:
                response = await http.get(
                    f"{_API_BASE}/{scryfall_id}",
                    params=params,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            logger.error("Scryfall request failed", exc_info=exc)
            raise ExternalServiceError(message="Could not reach Scryfall.") from exc

        if response.status_code == httpx.codes.NOT_FOUND:
            raise ResourceNotFoundError(message="Scryfall has no card with this id.")
        if response.status_code != httpx.codes.OK:
            raise ExternalServiceError(
                message=f"Scryfall returned {response.status_code}."
            )

        content_type = response.headers.get("content-type", "image/jpeg")
        return ScryfallImageFetch(content=response.content, content_type=content_type)

    async def _wait_for_rate_limit(self) -> None:
        global _last_request_monotonic
        async with _rate_limit_lock:
            now = time.monotonic()
            if _last_request_monotonic is not None:
                elapsed = now - _last_request_monotonic
                remaining = _MIN_SECONDS_BETWEEN_REQUESTS - elapsed
                if remaining > 0:
                    await asyncio.sleep(remaining)
            _last_request_monotonic = time.monotonic()
