"""Real Moxfield client — calls the public deck API over HTTPS.

Endpoint and required header confirmed against a Postman collection the
user supplied (api2.moxfield.com, `GET /v2/decks/all/{publicId}`, no
bearer token needed — just a Moxfield-assigned `User-Agent` value).

The `mainboard`/`commanders`/`companions` board structure and the
root-level `lastUpdatedAtUtc`/`createdAtUtc` fields were confirmed
against a real deck URL on 2026-07-30 (see S3's Moxfield-staleness
scoping notes). `lastUpdatedAtUtc` also appears, unrelated, ~100+ times
nested inside each card's `prices` object — callers reading it back out
of `raw_data` must read `raw_data["lastUpdatedAtUtc"]` at the root, never
a recursive/flattened search.
"""

import asyncio
import time
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.core.exceptions import (
    BadRequestError,
    ExternalServiceError,
    ResourceNotFoundError,
)
from app.core.log_config import get_logger
from app.services.moxfield.base import MoxfieldDeckFetch

logger = get_logger(__name__)

_API_BASE = "https://api2.moxfield.com/v2/decks/all"
_MIN_SECONDS_BETWEEN_REQUESTS = 1.0

# Module-level (not per-instance) so the 1 req/s cap holds across every
# request/instance sharing this process — see fetch_decklist.
_rate_limit_lock = asyncio.Lock()
_last_request_monotonic: float | None = None


def _extract_deck_id(deck_url: str) -> str:
    """Pull the public deck id out of a moxfield.com/decks/<id> URL."""
    parsed = urlparse(deck_url)
    if parsed.netloc.lower() not in {"moxfield.com", "www.moxfield.com"}:
        raise BadRequestError(message=f"Not a Moxfield deck URL: {deck_url!r}")

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2 or parts[0] != "decks":
        raise BadRequestError(message=f"Not a Moxfield deck URL: {deck_url!r}")
    return parts[1]


def _format_board(board: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for card_name, entry in board.items():
        quantity = entry.get("quantity", 1) if isinstance(entry, dict) else 1
        lines.append(f"{quantity} {card_name}")
    return lines


class HttpxMoxfieldClient:
    """Fetches a public deck via Moxfield's API, rate-limited to 1 req/s."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        # `transport` is only ever overridden by tests (httpx.MockTransport),
        # to avoid any real network call.
        self._transport = transport

    async def fetch_decklist(self, deck_url: str) -> MoxfieldDeckFetch:
        deck_id = _extract_deck_id(deck_url)
        await self._wait_for_rate_limit()

        user_agent = settings.base.moxfield_user_agent
        headers = {"User-Agent": user_agent.get_secret_value() if user_agent else ""}

        try:
            async with httpx.AsyncClient(
                timeout=10.0, transport=self._transport
            ) as http:
                response = await http.get(f"{_API_BASE}/{deck_id}", headers=headers)
        except httpx.HTTPError as exc:
            logger.error("Moxfield request failed", exc_info=exc)
            raise ExternalServiceError(message="Could not reach Moxfield.") from exc

        if response.status_code == httpx.codes.NOT_FOUND:
            raise ResourceNotFoundError(
                message="Moxfield deck not found (private, deleted, or bad URL)."
            )
        if response.status_code != httpx.codes.OK:
            raise ExternalServiceError(
                message=f"Moxfield returned {response.status_code}."
            )

        data = response.json()
        lines: list[str] = []
        lines += _format_board(data.get("commanders", {}))
        lines += _format_board(data.get("companions", {}))
        lines += _format_board(data.get("mainboard", {}))
        return MoxfieldDeckFetch(content="\n".join(lines), raw_data=data)

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
