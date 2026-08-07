"""Real MTGJSON client — downloads `AllPrintings.json` over HTTPS.

No API key/auth needed (MTGJSON is a free public bulk-data file). The
file is large (full reprint history of every card ever printed in every
language) and only ever fetched on an admin-triggered or scheduled
import, never per-request -- a long timeout is deliberate, not an
oversight.
"""

from typing import Any

import httpx

from app.core.exceptions import ExternalServiceError
from app.core.log_config import get_logger

logger = get_logger(__name__)

_ALL_PRINTINGS_URL = "https://mtgjson.com/api/v5/AllPrintings.json"
_DOWNLOAD_TIMEOUT_SECONDS = 300.0


class HttpxMTGJSONClient:
    """Fetches `AllPrintings.json` via a plain `httpx` GET + `json.load`.

    Per the 2026-08-05 decision, this tries the straightforward
    stdlib-`json`-via-`httpx` approach first; a streaming parser (e.g.
    `ijson`) would be a new dependency (Constitution §4.7/§22) only worth
    adding if this actually proves too memory-heavy in practice.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        # `transport` is only ever overridden by tests (httpx.MockTransport).
        self._transport = transport

    async def fetch_all_printings(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=_DOWNLOAD_TIMEOUT_SECONDS, transport=self._transport
            ) as http:
                response = await http.get(_ALL_PRINTINGS_URL)
        except httpx.HTTPError as exc:
            logger.error("MTGJSON download failed", exc_info=exc)
            raise ExternalServiceError(message="Could not reach MTGJSON.") from exc

        if response.status_code != httpx.codes.OK:
            raise ExternalServiceError(
                message=f"MTGJSON returned {response.status_code}."
            )

        return response.json()
