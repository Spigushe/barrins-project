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
"""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mtgjson import Card, MTGSet
from app.services.mtgjson.base import MTGJSONClient

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


async def import_all_printings(
    session: AsyncSession, client: MTGJSONClient
) -> ImportResult:
    """Fetches and upserts every set + card from MTGJSON's `AllPrintings.json`.

    Idempotent: re-running with unchanged upstream data updates existing
    rows in place, it never inserts duplicates (both PKs are natural
    keys). Commits once at the end -- a failed run rolls back everything
    rather than leaving a half-imported dataset.

    All sets are upserted (in chunks) before any card, preserving the
    `cards.set_code -> sets.code` FK order without needing per-set
    interleaving.
    """
    payload = await client.fetch_all_printings()
    all_sets: dict[str, Any] = payload["data"]

    set_rows = [
        _set_values(set_code, set_data) for set_code, set_data in all_sets.items()
    ]
    card_rows = [
        _card_values(set_code, card_data)
        for set_code, set_data in all_sets.items()
        for card_data in set_data.get("cards", [])
    ]

    await _upsert_sets(session, set_rows)
    await _upsert_cards(session, card_rows)

    await session.commit()
    return ImportResult(sets_upserted=len(set_rows), cards_upserted=len(card_rows))
