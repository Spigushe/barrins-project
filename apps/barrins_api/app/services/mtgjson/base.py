"""Common interface for MTGJSON data clients."""

from typing import Any, Protocol


class MTGJSONClient(Protocol):
    """Contract implemented by every MTGJSON client in the project."""

    async def fetch_all_printings(self) -> dict[str, Any]:
        """Fetch MTGJSON's `AllPrintings.json`, parsed.

        Returns the full document (`{"meta": {...}, "data": {<set code>:
        <Set object>, ...}}`) -- callers read `payload["data"]`.

        Raises `app.core.exceptions.ExternalServiceError` on any network
        or non-200 failure.
        """
        ...
