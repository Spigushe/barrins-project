"""Common interface for MTGJSON data clients."""

from collections.abc import AsyncIterator
from typing import Any, Protocol


class MTGJSONClient(Protocol):
    """Contract implemented by every MTGJSON client in the project."""

    def stream_sets(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """Stream MTGJSON's `AllPrintings.json` one set at a time.

        Yields `(set_code, set_data)` pairs -- the same per-set shape as
        the old `payload["data"].items()` -- without ever holding the
        full document (raw bytes or parsed tree) in memory at once
        (2026-08-09 incident: buffering the whole multi-hundred-MB file
        OOM-killed the worker mid-import on the staging VPS).

        Raises `app.core.exceptions.ExternalServiceError` on any network
        or non-200 failure.
        """
        ...
