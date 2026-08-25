"""Common interface for Scryfall card-image clients."""

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ScryfallImageFetch:
    """Result of fetching one card's image.

    `content_type` is always "image/jpeg" today (the "normal" size
    Scryfall serves is JPEG) — kept as a field rather than hardcoded at
    the call site so a future size/format change doesn't require
    touching the cache/route too.
    """

    content: bytes
    content_type: str


class ScryfallClient(Protocol):
    """Contract implemented by every Scryfall image client in the project."""

    async def fetch_card_image(
        self, scryfall_id: str, face: Literal["front", "back"] = "front"
    ) -> ScryfallImageFetch:
        """Fetch one card's "normal"-size image by Scryfall id.

        `face="back"` is only meaningful for a double-faced card (MDFC/
        transform) — raises `ResourceNotFoundError` for a single-faced
        card, same as an unknown `scryfall_id`, so callers (the frontend)
        can treat "no back face" and "no such card" identically: hide the
        image rather than error out.

        Raises `app.core.exceptions.ResourceNotFoundError` if Scryfall has
        no card with this id (or no such face), `ExternalServiceError` on
        any other upstream failure.
        """
        ...
