"""Disk cache for Scryfall card images, keyed by (scryfall_id, face).

Wiped wholesale on every MTGJSON import (see
`app/api/general/mtgjson.py::import_mtgjson`) rather than tracked
per-entry — imports are infrequent (daily scheduled refresh) so a full
wipe is simpler and correct, matching
`card_resolver.invalidate_name_cache`'s same "cheap to rebuild lazily"
reasoning.
"""

import shutil
from pathlib import Path
from typing import Literal

from app.config import settings


def _cache_dir() -> Path:
    path = Path(settings.base.card_image_cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _image_path(scryfall_id: str, face: Literal["front", "back"]) -> Path:
    return _cache_dir() / f"{scryfall_id}-{face}.jpg"


def read_cached_image(
    scryfall_id: str, face: Literal["front", "back"] = "front"
) -> bytes | None:
    path = _image_path(scryfall_id, face)
    return path.read_bytes() if path.is_file() else None


def write_cached_image(
    scryfall_id: str, content: bytes, face: Literal["front", "back"] = "front"
) -> None:
    # Write-then-rename: avoids a torn/partial file if two requests race
    # on a cold cache for the same id/face.
    path = _image_path(scryfall_id, face)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(content)
    tmp.replace(path)


def clear_image_cache() -> None:
    shutil.rmtree(_cache_dir(), ignore_errors=True)
