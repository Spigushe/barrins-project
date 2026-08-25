"""Tests for GET /api/v1/cards/{scryfall_id}/image."""

from pathlib import Path
from typing import Literal

import pytest
from httpx import AsyncClient

from app.core.exceptions import ExternalServiceError, ResourceNotFoundError
from app.main import app
from app.services.scryfall import get_scryfall_client
from app.services.scryfall.base import ScryfallImageFetch
from app.services.scryfall.image_cache import read_cached_image

_BASE = "/api/v1"
_SETTINGS = "app.services.scryfall.image_cache.settings.base"


@pytest.fixture(autouse=True)
def _cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cache_dir = tmp_path / "card_images"
    monkeypatch.setattr(f"{_SETTINGS}.card_image_cache_dir", str(cache_dir))
    return cache_dir


class _FakeScryfallClient:
    def __init__(self, *, has_back_face: bool = False, fail_times: int = 0) -> None:
        self.calls: list[tuple[str, str]] = []
        self._has_back_face = has_back_face
        self._fail_times = fail_times

    async def fetch_card_image(
        self, scryfall_id: str, face: Literal["front", "back"] = "front"
    ) -> ScryfallImageFetch:
        self.calls.append((scryfall_id, face))
        if self._fail_times > 0:
            self._fail_times -= 1
            raise ExternalServiceError(message="Could not reach Scryfall.")
        if face == "back" and not self._has_back_face:
            raise ResourceNotFoundError(message="No back face.")
        return ScryfallImageFetch(
            content=f"fake-{face}-jpeg-bytes".encode(), content_type="image/jpeg"
        )


class TestGetCardImage:
    async def test_fetches_and_serves_front_face_by_default(self, client: AsyncClient):
        fake_client = _FakeScryfallClient()
        app.dependency_overrides[get_scryfall_client] = lambda: fake_client
        try:
            resp = await client.get(f"{_BASE}/cards/some-scryfall-id/image")
        finally:
            app.dependency_overrides.pop(get_scryfall_client, None)

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/jpeg"
        assert resp.content == b"fake-front-jpeg-bytes"
        assert fake_client.calls == [("some-scryfall-id", "front")]

    async def test_second_request_is_served_from_cache_not_refetched(
        self, client: AsyncClient
    ):
        fake_client = _FakeScryfallClient()
        app.dependency_overrides[get_scryfall_client] = lambda: fake_client
        try:
            first = await client.get(f"{_BASE}/cards/some-scryfall-id/image")
            second = await client.get(f"{_BASE}/cards/some-scryfall-id/image")
        finally:
            app.dependency_overrides.pop(get_scryfall_client, None)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.content == b"fake-front-jpeg-bytes"
        # Only the first request should have reached the (fake) upstream.
        assert fake_client.calls == [("some-scryfall-id", "front")]

    async def test_back_face_is_fetched_and_cached_separately_from_front(
        self, client: AsyncClient
    ):
        fake_client = _FakeScryfallClient(has_back_face=True)
        app.dependency_overrides[get_scryfall_client] = lambda: fake_client
        try:
            front = await client.get(f"{_BASE}/cards/some-scryfall-id/image")
            back = await client.get(f"{_BASE}/cards/some-scryfall-id/image?face=back")
            back_again = await client.get(
                f"{_BASE}/cards/some-scryfall-id/image?face=back"
            )
        finally:
            app.dependency_overrides.pop(get_scryfall_client, None)

        assert front.content == b"fake-front-jpeg-bytes"
        assert back.content == b"fake-back-jpeg-bytes"
        assert back_again.content == b"fake-back-jpeg-bytes"
        assert fake_client.calls == [
            ("some-scryfall-id", "front"),
            ("some-scryfall-id", "back"),
        ]

    async def test_back_face_404s_for_a_single_faced_card(self, client: AsyncClient):
        fake_client = _FakeScryfallClient(has_back_face=False)
        app.dependency_overrides[get_scryfall_client] = lambda: fake_client
        try:
            resp = await client.get(f"{_BASE}/cards/some-scryfall-id/image?face=back")
        finally:
            app.dependency_overrides.pop(get_scryfall_client, None)

        assert resp.status_code == 404

    async def test_upstream_failure_is_not_cached_and_is_retried(
        self, client: AsyncClient
    ):
        # Simulates a connection issue: the first request fails upstream
        # and must not poison the disk cache, so a later request (e.g.
        # after the connection recovers) still reaches Scryfall instead
        # of being stuck serving/reusing the failed attempt.
        fake_client = _FakeScryfallClient(fail_times=1)
        app.dependency_overrides[get_scryfall_client] = lambda: fake_client
        try:
            failed = await client.get(f"{_BASE}/cards/some-scryfall-id/image")
            assert read_cached_image("some-scryfall-id") is None

            retried = await client.get(f"{_BASE}/cards/some-scryfall-id/image")
        finally:
            app.dependency_overrides.pop(get_scryfall_client, None)

        assert failed.status_code == 502
        assert retried.status_code == 200
        assert retried.content == b"fake-front-jpeg-bytes"
        assert fake_client.calls == [
            ("some-scryfall-id", "front"),
            ("some-scryfall-id", "front"),
        ]
