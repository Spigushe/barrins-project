from datetime import date

import pytest
import requests

from karn_tablets import push
from karn_tablets.pipeline import ArchetypeResult, ClusteringRunResult
from karn_tablets.windowing import Window, WindowKind

_RESULT = ClusteringRunResult(
    window=Window(
        kind=WindowKind.rolling_30d,
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    ),
    algorithm="kmeans",
    total_decks=3,
    archetypes=[
        ArchetypeResult(
            cluster_id=1,
            deck_count=3,
            share=1.0,
            representative_mainboard={"Sol Ring": 1},
            representative_sideboard={},
        )
    ],
)


class FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


class TestPush:
    def test_success_posts_to_the_ingest_path(self, monkeypatch: pytest.MonkeyPatch):
        captured: dict[str, object] = {}

        def fake_post(url, json, headers, timeout):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            captured["timeout"] = timeout
            return FakeResponse(200)

        monkeypatch.setattr(push.requests, "post", fake_post)
        ok = push.push(_RESULT, "https://api.example.com", "secret-token")

        assert ok is True
        assert captured["url"] == "https://api.example.com/internal/karn/ingest"
        assert captured["headers"] == {"X-Karn-Token": "secret-token"}
        assert captured["json"]["total_decks"] == 3
        assert captured["json"]["archetypes"][0]["representative_mainboard"] == {
            "Sol Ring": 1
        }

    def test_strips_trailing_slash_from_api_url(self, monkeypatch: pytest.MonkeyPatch):
        captured: dict[str, object] = {}
        monkeypatch.setattr(
            push.requests,
            "post",
            lambda url, **_kw: (captured.__setitem__("url", url), FakeResponse(200))[1],
        )
        push.push(_RESULT, "https://api.example.com/", "token")
        assert captured["url"] == "https://api.example.com/internal/karn/ingest"

    def test_http_error_returns_false(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(push.requests, "post", lambda *_a, **_kw: FakeResponse(500))
        ok = push.push(_RESULT, "https://api.example.com", "token")
        assert ok is False

    def test_network_error_returns_false(self, monkeypatch: pytest.MonkeyPatch):
        def raise_connection_error(*_a, **_kw):
            raise requests.ConnectionError("unreachable")

        monkeypatch.setattr(push.requests, "post", raise_connection_error)
        ok = push.push(_RESULT, "https://api.example.com", "token")
        assert ok is False
