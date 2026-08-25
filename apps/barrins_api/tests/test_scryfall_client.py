"""Tests for app/services/scryfall/ (client, console stub, factory, rate limiter)."""

from collections.abc import Callable

import httpx
import pytest

from app.core.exceptions import (
    ExternalServiceError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from app.services.scryfall import get_scryfall_client
from app.services.scryfall.console_client import ConsoleScryfallClient
from app.services.scryfall.http_client import HttpxScryfallClient

_SETTINGS = "app.services.scryfall.http_client.settings.base"
_FACTORY_SETTINGS = "app.services.scryfall.settings"

_IMAGE_BYTES = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


def _mock_transport(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


class TestHttpxScryfallClient:
    async def test_fetch_card_image_returns_bytes_and_content_type(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(f"{_SETTINGS}.scryfall_user_agent", "real-agent")
        monkeypatch.setattr(
            "app.services.scryfall.http_client._last_request_monotonic", None
        )

        seen_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen_headers.update(request.headers)
            return httpx.Response(
                200, content=_IMAGE_BYTES, headers={"content-type": "image/jpeg"}
            )

        client = HttpxScryfallClient(transport=_mock_transport(handler))
        fetch = await client.fetch_card_image("abc-123")

        assert fetch.content == _IMAGE_BYTES
        assert fetch.content_type == "image/jpeg"
        assert seen_headers["user-agent"] == "real-agent"

    async def test_fetch_card_image_404_raises_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "app.services.scryfall.http_client._last_request_monotonic", None
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        client = HttpxScryfallClient(transport=_mock_transport(handler))
        with pytest.raises(ResourceNotFoundError):
            await client.fetch_card_image("missing-id")

    async def test_fetch_card_image_passes_face_through_to_scryfall(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "app.services.scryfall.http_client._last_request_monotonic", None
        )

        seen_params: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen_params.update(dict(request.url.params))
            return httpx.Response(
                200, content=_IMAGE_BYTES, headers={"content-type": "image/jpeg"}
            )

        client = HttpxScryfallClient(transport=_mock_transport(handler))
        await client.fetch_card_image("abc-123", face="back")

        assert seen_params["face"] == "back"

    async def test_fetch_card_image_back_face_404_raises_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        # A single-faced card has no back face -- Scryfall 404s the same
        # way it would for an unknown id.
        monkeypatch.setattr(
            "app.services.scryfall.http_client._last_request_monotonic", None
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        client = HttpxScryfallClient(transport=_mock_transport(handler))
        with pytest.raises(ResourceNotFoundError):
            await client.fetch_card_image("single-faced-id", face="back")

    async def test_fetch_card_image_upstream_error_raises_external_service_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "app.services.scryfall.http_client._last_request_monotonic", None
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        client = HttpxScryfallClient(transport=_mock_transport(handler))
        with pytest.raises(ExternalServiceError):
            await client.fetch_card_image("abc-123")

    async def test_fetch_card_image_network_failure_raises_external_service_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "app.services.scryfall.http_client._last_request_monotonic", None
        )

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        client = HttpxScryfallClient(transport=_mock_transport(handler))
        with pytest.raises(ExternalServiceError):
            await client.fetch_card_image("abc-123")


class TestConsoleScryfallClient:
    async def test_returns_placeholder_without_network_call(self):
        fetch = await ConsoleScryfallClient().fetch_card_image("anything")
        assert fetch.content_type == "image/jpeg"
        assert len(fetch.content) > 0


class TestGetScryfallClient:
    def test_returns_http_client_when_user_agent_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            f"{_FACTORY_SETTINGS}.base.scryfall_user_agent", "real-agent"
        )
        assert isinstance(get_scryfall_client(), HttpxScryfallClient)

    def test_returns_console_client_in_dev_when_unconfigured(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(f"{_FACTORY_SETTINGS}.base.scryfall_user_agent", None)
        monkeypatch.setattr(f"{_FACTORY_SETTINGS}.base.environment", "development")
        assert isinstance(get_scryfall_client(), ConsoleScryfallClient)

    def test_raises_in_production_when_unconfigured(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(f"{_FACTORY_SETTINGS}.base.scryfall_user_agent", None)
        monkeypatch.setattr(f"{_FACTORY_SETTINGS}.base.environment", "production")
        with pytest.raises(ServiceUnavailableError):
            get_scryfall_client()
