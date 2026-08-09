"""Real MTGJSON client — downloads `AllPrintings.json` over HTTPS.

No API key/auth needed (MTGJSON is a free public bulk-data file). The
file is large (full reprint history of every card ever printed in every
language) and only ever fetched on an admin-triggered or scheduled
import, never per-request -- a long timeout is deliberate, not an
oversight.
"""

from collections.abc import AsyncIterator
from typing import Any

import httpx
import ijson

from app.core.exceptions import ExternalServiceError
from app.core.log_config import get_logger

logger = get_logger(__name__)

_ALL_PRINTINGS_URL = "https://mtgjson.com/api/v5/AllPrintings.json"
_DOWNLOAD_TIMEOUT_SECONDS = 300.0


class HttpxMTGJSONClient:
    """Streams `AllPrintings.json` via `httpx` + `ijson` instead of
    buffering it whole.

    Per the 2026-08-05 decision, a plain `httpx` GET + `response.json()`
    was tried first, on the basis that a streaming parser would only be
    worth the added dependency (Constitution §4.7/§22) if buffering
    actually proved too memory-heavy in practice. It did (2026-08-09:
    OOM-killed the worker mid-import), so this now streams via `ijson`,
    never holding the full response body or parsed tree in memory.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        # `transport` is only ever overridden by tests (httpx.MockTransport).
        self._transport = transport

    async def stream_sets(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        try:
            async with (
                httpx.AsyncClient(
                    timeout=_DOWNLOAD_TIMEOUT_SECONDS, transport=self._transport
                ) as http,
                http.stream("GET", _ALL_PRINTINGS_URL) as response,
            ):
                if response.status_code != httpx.codes.OK:
                    raise ExternalServiceError(
                        message=f"MTGJSON returned {response.status_code}."
                    )
                async for set_code, set_data in ijson.kvitems(
                    ijson.from_iter(response.aiter_bytes()), "data"
                ):
                    yield set_code, set_data
        except httpx.HTTPError as exc:
            logger.error("MTGJSON download failed", exc_info=exc)
            raise ExternalServiceError(message="Could not reach MTGJSON.") from exc
