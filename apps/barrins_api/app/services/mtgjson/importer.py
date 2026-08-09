"""Upserts MTGJSON's `AllPrintings.json` into the `sets`/`cards` tables.

Chunked `INSERT ... ON CONFLICT DO UPDATE` (multi-row VALUES per
statement), in FK order (all sets before any card) -- the same
idempotent-upsert pattern already decided for T3's ingestion route
(`docs/project/v2.0.0-bump/t3-scripture-ingestion-pipeline/`), applied
here since both `sets.code` and `cards.id` are natural keys that never
change between MTGJSON releases.

Chunked rather than one statement per row (2026-08-07 fix): AllPrintings.json
has ~700 sets and 100k+ card printings, and one round-trip per row made
`POST /mtgjson/import` take ~45 minutes. Batching into `_UPSERT_CHUNK_SIZE`-row
statements cuts that to a few hundred round-trips.

Consumes `client.stream_sets()` incrementally rather than collecting every
row into `set_rows`/`card_rows` lists upfront (2026-08-09 fix): building
those lists for the whole file, on top of the parsed JSON tree itself,
OOM-killed the worker before a single row was written. Peak memory is now
bounded by `_UPSERT_CHUNK_SIZE`, not file size -- see `_ImportBuffer`.
"""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_config import get_logger
from app.models.mtgjson import Card, MTGSet
from app.services.mtgjson.base import MTGJSONClient

logger = get_logger(__name__)

#: Rows per multi-row upsert statement. Cards have 19 columns, so
#: 500 * 19 = 9,500 bind parameters per statement -- comfortably under
#: Postgres's 65,535 parameter limit even as columns are added later.
_UPSERT_CHUNK_SIZE = 500


@dataclass(frozen=True)
class ImportResult:
    """Outcome of a single `import_all_printings` run."""

    sets_upserted: int
    cards_upserted: int


def _set_values(set_code: str, set_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": set_code,
        "name": set_data["name"],
        "release_date": date.fromisoformat(set_data["releaseDate"]),
        "type": set_data["type"],
        "block": set_data.get("block"),
        "base_set_size": set_data["baseSetSize"],
        "total_set_size": set_data["totalSetSize"],
        "keyrune_code": set_data["keyruneCode"],
        "is_online_only": set_data.get("isOnlineOnly", False),
    }


def _card_values(set_code: str, card_data: dict[str, Any]) -> dict[str, Any]:
    identifiers: dict[str, Any] = card_data.get("identifiers", {})
    return {
        "id": uuid.UUID(card_data["uuid"]),
        "set_code": set_code,
        "name": card_data["name"],
        "face_name": card_data.get("faceName"),
        "side": card_data.get("side"),
        "layout": card_data.get("layout", "normal"),
        "other_face_ids": card_data.get("otherFaceIds", []),
        "type_line": card_data["type"],
        "types": card_data.get("types", []),
        "supertypes": card_data.get("supertypes", []),
        "subtypes": card_data.get("subtypes", []),
        "mana_cost": card_data.get("manaCost"),
        "mana_value": card_data.get("manaValue"),
        "colors": card_data.get("colors", []),
        "color_identity": card_data.get("colorIdentity", []),
        "rarity": card_data["rarity"],
        "number": card_data["number"],
        "scryfall_id": identifiers.get("scryfallId"),
        "scryfall_oracle_id": identifiers.get("scryfallOracleId"),
    }


def _chunked(rows: list[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


async def _upsert_sets(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    for chunk in _chunked(rows, _UPSERT_CHUNK_SIZE):
        stmt = insert(MTGSet).values(chunk)
        update_cols = {k: stmt.excluded[k] for k in chunk[0] if k != "code"}
        stmt = stmt.on_conflict_do_update(index_elements=["code"], set_=update_cols)
        await session.execute(stmt)


async def _upsert_cards(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    for chunk in _chunked(rows, _UPSERT_CHUNK_SIZE):
        stmt = insert(Card).values(chunk)
        update_cols = {k: stmt.excluded[k] for k in chunk[0] if k != "id"}
        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_cols)
        await session.execute(stmt)


@dataclass
class _ImportBuffer:
    """Accumulates rows from the streamed sets and flushes in
    `_UPSERT_CHUNK_SIZE` batches, so peak memory is bounded by chunk size
    rather than the whole file.

    Sets are always flushed before cards: a buffered card's `set_code`
    FK must already have been sent to Postgres (even if the surrounding
    transaction hasn't committed yet -- Postgres checks FKs against the
    transaction's own uncommitted writes) before that card is upserted.
    """

    session: AsyncSession
    sets_upserted: int = 0
    cards_upserted: int = 0
    _pending_sets: list[dict[str, Any]] = field(default_factory=list)
    _pending_cards: list[dict[str, Any]] = field(default_factory=list)

    async def add_set(self, set_code: str, set_data: dict[str, Any]) -> None:
        self._pending_sets.append(_set_values(set_code, set_data))
        self.sets_upserted += 1
        for card_data in set_data.get("cards", []):
            self._pending_cards.append(_card_values(set_code, card_data))
            self.cards_upserted += 1

        if len(self._pending_sets) >= _UPSERT_CHUNK_SIZE:
            await self._flush_sets()
        if len(self._pending_cards) >= _UPSERT_CHUNK_SIZE:
            await self._flush_sets()
            await self._flush_cards()

    async def flush(self) -> None:
        await self._flush_sets()
        await self._flush_cards()

    async def _flush_sets(self) -> None:
        if self._pending_sets:
            await _upsert_sets(self.session, self._pending_sets)
            for row in self._pending_sets:
                logger.debug("Upserted set %s", row["code"])
            self._pending_sets = []

    async def _flush_cards(self) -> None:
        if self._pending_cards:
            await _upsert_cards(self.session, self._pending_cards)
            self._pending_cards = []


async def import_all_printings(
    session: AsyncSession, client: MTGJSONClient
) -> ImportResult:
    """Streams and upserts every set + card from MTGJSON's `AllPrintings.json`.

    Idempotent: re-running with unchanged upstream data updates existing
    rows in place, it never inserts duplicates (both PKs are natural
    keys). Commits once at the end -- a failed run rolls back everything
    rather than leaving a half-imported dataset.

    Consumes `client.stream_sets()` set-by-set via `_ImportBuffer`,
    interleaving set/card upserts as chunks fill rather than collecting
    every row into memory first -- see the module docstring.
    """
    buffer = _ImportBuffer(session)
    async for set_code, set_data in client.stream_sets():
        await buffer.add_set(set_code, set_data)
    await buffer.flush()

    await session.commit()
    return ImportResult(
        sets_upserted=buffer.sets_upserted, cards_upserted=buffer.cards_upserted
    )
