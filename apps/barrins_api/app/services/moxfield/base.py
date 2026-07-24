"""Common interface for Moxfield deck-import clients."""

from typing import Protocol


class MoxfieldClient(Protocol):
    """Contract implemented by every Moxfield client in the project."""

    async def fetch_decklist(self, deck_url: str) -> str:
        """Fetch a public Moxfield deck and return it as decklist text.

        One card per line (e.g. "4 Lightning Bolt"), commanders first —
        the same free-text format `TSPersonalDecklistVersion.content`
        already uses for manually-entered decklists.

        Raises `app.core.exceptions.BadRequestError` if `deck_url` isn't
        a recognizable Moxfield deck URL, `ResourceNotFoundError` if the
        deck doesn't exist or isn't public, `ExternalServiceError` on any
        other upstream failure.
        """
        ...
