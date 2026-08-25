"""Tests for `HttpxMTGJSONClient.stream_sets` (app/services/mtgjson/http_client.py).

Exercises the real `httpx` + `ijson` streaming path against `httpx.MockTransport`
-- `tests/test_mtgjson.py` only ever exercises `FakeMTGJSONClient`, which never
touches this module, so this is the only coverage of the actual fix for the
2026-08-09 OOM incident (buffering the whole response body/parsed tree, see
`app/services/mtgjson/http_client.py`'s docstring).
"""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.core.exceptions import ExternalServiceError
from app.services.mtgjson.http_client import HttpxMTGJSONClient

_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "mtgjson_sample.json").read_text(
        encoding="utf-8"
    )
)


class TestStreamSets:
    async def test_yields_every_set_with_its_data(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_FIXTURE)

        client = HttpxMTGJSONClient(transport=httpx.MockTransport(handler))
        seen: dict[str, dict[str, Any]] = {
            set_code: set_data async for set_code, set_data in client.stream_sets()
        }

        assert set(seen) == {"P30A", "ZNR"}
        assert [c["name"] for c in seen["P30A"]["cards"]] == ["Serra Angel"]
        assert len(seen["ZNR"]["cards"]) == 2

    async def test_non_200_raises_external_service_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="Service Unavailable")

        client = HttpxMTGJSONClient(transport=httpx.MockTransport(handler))

        with pytest.raises(ExternalServiceError):
            async for _ in client.stream_sets():
                pass

    async def test_network_error_raises_external_service_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        client = HttpxMTGJSONClient(transport=httpx.MockTransport(handler))

        with pytest.raises(ExternalServiceError):
            async for _ in client.stream_sets():
                pass
