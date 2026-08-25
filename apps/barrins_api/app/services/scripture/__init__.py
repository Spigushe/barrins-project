"""MTGJSON card-name resolution utility (T3), carried without Barrin's
Scripture's ingestion pipeline -- see `card_resolver.py`."""

from app.services.scripture.card_resolver import (
    invalidate_name_cache,
    normalize_name,
    resolve_card_name,
)

__all__ = [
    "invalidate_name_cache",
    "normalize_name",
    "resolve_card_name",
]
