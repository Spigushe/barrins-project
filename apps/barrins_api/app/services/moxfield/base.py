"""Common interface for Moxfield deck-import clients."""

from dataclasses import dataclass
from typing import Protocol

from app.models._types import JsonValue


@dataclass(frozen=True)
class MoxfieldDeckFetch:
    """Result of a `MoxfieldClient.fetch_decklist` call.

    `content` is the formatted decklist text (one card per line, e.g.
    "4 Lightning Bolt", commanders first) — the same free-text format
    `TSPersonalDecklistVersion.content` already uses for manually-entered
    decklists. `raw_data` is the full, unmodified JSON object Moxfield
    returned, stored as-is (`TSPersonalDecklistVersion.moxfield_data`) so
    later features (e.g. the staleness check below) can read fields from
    it without a second Moxfield call.
    """

    content: str
    raw_data: JsonValue


class MoxfieldClient(Protocol):
    """Contract implemented by every Moxfield client in the project."""

    async def fetch_decklist(self, deck_url: str) -> MoxfieldDeckFetch:
        """Fetch a public Moxfield deck's decklist text and raw JSON.

        Raises `app.core.exceptions.BadRequestError` if `deck_url` isn't
        a recognizable Moxfield deck URL, `ResourceNotFoundError` if the
        deck doesn't exist or isn't public, `ExternalServiceError` on any
        other upstream failure.
        """
        ...
