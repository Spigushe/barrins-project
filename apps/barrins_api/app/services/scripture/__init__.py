"""Barrin's Scripture ingestion pipeline (T3): card-name resolution + upserts."""

from app.services.scripture.card_resolver import (
    invalidate_name_cache,
    normalize_name,
    resolve_card_name,
)
from app.services.scripture.ingester import IngestResult, ingest_scrape

__all__ = [
    "IngestResult",
    "ingest_scrape",
    "invalidate_name_cache",
    "normalize_name",
    "resolve_card_name",
]
