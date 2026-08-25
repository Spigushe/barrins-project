"""Tests for app/services/scryfall/image_cache.py."""

from pathlib import Path

import pytest

from app.services.scryfall import image_cache

_SETTINGS = "app.services.scryfall.image_cache.settings.base"


@pytest.fixture(autouse=True)
def _cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cache_dir = tmp_path / "card_images"
    monkeypatch.setattr(f"{_SETTINGS}.card_image_cache_dir", str(cache_dir))
    return cache_dir


class TestImageCache:
    def test_read_miss_returns_none(self):
        assert image_cache.read_cached_image("missing-id") is None

    def test_write_then_read_round_trips(self):
        image_cache.write_cached_image("abc-123", b"jpeg-bytes")
        assert image_cache.read_cached_image("abc-123") == b"jpeg-bytes"

    def test_clear_removes_cached_entries(self):
        image_cache.write_cached_image("abc-123", b"jpeg-bytes")
        image_cache.clear_image_cache()
        assert image_cache.read_cached_image("abc-123") is None

    def test_clear_on_empty_cache_does_not_raise(self, _cache_dir: Path):
        # Directory doesn't exist yet -- nothing has been cached.
        assert not _cache_dir.exists()
        image_cache.clear_image_cache()

    def test_front_and_back_faces_are_cached_independently(self):
        image_cache.write_cached_image("abc-123", b"front-bytes", face="front")
        image_cache.write_cached_image("abc-123", b"back-bytes", face="back")

        assert image_cache.read_cached_image("abc-123", face="front") == b"front-bytes"
        assert image_cache.read_cached_image("abc-123", face="back") == b"back-bytes"

    def test_face_defaults_to_front(self):
        image_cache.write_cached_image("abc-123", b"front-bytes")
        assert image_cache.read_cached_image("abc-123") == b"front-bytes"
        assert image_cache.read_cached_image("abc-123", face="back") is None
