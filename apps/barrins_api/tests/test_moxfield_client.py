"""Tests for app/services/moxfield/ (client, console stub, factory, rate limiter)."""

from collections.abc import Callable

import httpx
import pytest
from pydantic import SecretStr

from app.core.exceptions import (
    BadRequestError,
    ExternalServiceError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from app.services.moxfield import get_moxfield_client
from app.services.moxfield.console_client import ConsoleMoxfieldClient
from app.services.moxfield.http_client import HttpxMoxfieldClient, _extract_deck_id

_SETTINGS = "app.services.moxfield.http_client.settings.base"
_FACTORY_SETTINGS = "app.services.moxfield.settings"

_SAMPLE_RESPONSE = {
    "commanders": {"Atraxa, Praetors' Voice": {"quantity": 1}},
    "companions": {},
    "mainboard": {
        "Sol Ring": {"quantity": 1},
        "Command Tower": {"quantity": 1},
    },
}


def _mock_transport(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


class TestExtractDeckId:
    def test_valid_url(self):
        assert _extract_deck_id("https://www.moxfield.com/decks/abc123") == "abc123"
        assert _extract_deck_id("https://moxfield.com/decks/abc123") == "abc123"

    def test_rejects_non_moxfield_host(self):
        with pytest.raises(BadRequestError):
            _extract_deck_id("https://evil.example.com/decks/abc123")

    def test_rejects_malformed_path(self):
        with pytest.raises(BadRequestError):
            _extract_deck_id("https://moxfield.com/users/someone")


class TestHttpxMoxfieldClient:
    async def test_fetch_decklist_formats_commanders_then_mainboard(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(f"{_SETTINGS}.moxfield_user_agent", SecretStr("real-agent"))
        monkeypatch.setattr(
            "app.services.moxfield.http_client._last_request_monotonic", None
        )

        seen_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen_headers.update(request.headers)
            return httpx.Response(200, json=_SAMPLE_RESPONSE)

        client = HttpxMoxfieldClient(transport=_mock_transport(handler))
        content = await client.fetch_decklist("https://moxfield.com/decks/abc123")

        assert content.splitlines() == [
            "1 Atraxa, Praetors' Voice",
            "1 Sol Ring",
            "1 Command Tower",
        ]
        assert seen_headers["user-agent"] == "real-agent"

    async def test_fetch_decklist_404_raises_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "app.services.moxfield.http_client._last_request_monotonic", None
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        client = HttpxMoxfieldClient(transport=_mock_transport(handler))
        with pytest.raises(ResourceNotFoundError):
            await client.fetch_decklist("https://moxfield.com/decks/missing")

    async def test_fetch_decklist_upstream_error_raises_external_service_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "app.services.moxfield.http_client._last_request_monotonic", None
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        client = HttpxMoxfieldClient(transport=_mock_transport(handler))
        with pytest.raises(ExternalServiceError):
            await client.fetch_decklist("https://moxfield.com/decks/abc123")

    async def test_fetch_decklist_network_failure_raises_external_service_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "app.services.moxfield.http_client._last_request_monotonic", None
        )

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        client = HttpxMoxfieldClient(transport=_mock_transport(handler))
        with pytest.raises(ExternalServiceError):
            await client.fetch_decklist("https://moxfield.com/decks/abc123")

    async def test_rate_limiter_sleeps_for_the_remaining_gap(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Two calls under 1s apart must be spaced out by the limiter.

        `time` and `asyncio` are shared singleton modules — patching
        `time.monotonic`/`asyncio.sleep` in place (even via a dotted path
        through http_client) would mutate them for the whole test run,
        breaking unrelated tests' event-loop/timing internals. Instead,
        replace http_client's own *reference* to each module with a fake
        object; `monkeypatch` restores the reference afterwards, leaving
        the real modules untouched throughout.
        """

        class _FakeTime:
            def __init__(self, values: list[float]) -> None:
                self._values = iter(values)

            def monotonic(self) -> float:
                return next(self._values)

        class _FakeAsyncio:
            def __init__(self) -> None:
                self.sleep_calls: list[float] = []

            async def sleep(self, seconds: float) -> None:
                self.sleep_calls.append(seconds)

        # _wait_for_rate_limit reads time.monotonic() twice per call (once
        # for "now", once to record _last_request_monotonic afterwards).
        fake_time = _FakeTime([100.0, 100.0, 100.2, 100.2])
        fake_asyncio = _FakeAsyncio()
        monkeypatch.setattr("app.services.moxfield.http_client.time", fake_time)
        monkeypatch.setattr("app.services.moxfield.http_client.asyncio", fake_asyncio)
        monkeypatch.setattr(
            "app.services.moxfield.http_client._last_request_monotonic", None
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_SAMPLE_RESPONSE)

        client = HttpxMoxfieldClient(transport=_mock_transport(handler))
        await client.fetch_decklist("https://moxfield.com/decks/abc123")
        await client.fetch_decklist("https://moxfield.com/decks/abc123")

        assert fake_asyncio.sleep_calls == [pytest.approx(0.8)]


class TestConsoleMoxfieldClient:
    async def test_returns_fixed_sample_without_network_call(self):
        content = await ConsoleMoxfieldClient().fetch_decklist(
            "https://moxfield.com/decks/anything"
        )
        assert "Sol Ring" in content


class TestGetMoxfieldClient:
    def test_returns_http_client_when_user_agent_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            f"{_FACTORY_SETTINGS}.base.moxfield_user_agent", SecretStr("real-agent")
        )
        assert isinstance(get_moxfield_client(), HttpxMoxfieldClient)

    def test_returns_console_client_in_dev_when_unconfigured(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(f"{_FACTORY_SETTINGS}.base.moxfield_user_agent", None)
        monkeypatch.setattr(f"{_FACTORY_SETTINGS}.base.environment", "development")
        assert isinstance(get_moxfield_client(), ConsoleMoxfieldClient)

    def test_raises_in_production_when_unconfigured(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(f"{_FACTORY_SETTINGS}.base.moxfield_user_agent", None)
        monkeypatch.setattr(f"{_FACTORY_SETTINGS}.base.environment", "production")
        with pytest.raises(ServiceUnavailableError):
            get_moxfield_client()
