"""Upserts MTGJSON's `AllPrintings.json` into the `sets`/`cards` tables.

One `INSERT ... ON CONFLICT DO UPDATE` per row, in FK order (sets before
their cards) -- the same idempotent-upsert pattern already decided for
T3's ingestion route (`docs/project/v2.0.0-bump/t3-scripture-ingestion-pipeline/`),
applied here since both `sets.code` and `cards.id` are natural keys that
never change between MTGJSON releases.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mtgjson import Card, MTGSet
from app.services.mtgjson.base import MTGJSONClient


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


async def _upsert_set(
    session: AsyncSession, set_code: str, set_data: dict[str, Any]
) -> None:
    values = _set_values(set_code, set_data)
    stmt = insert(MTGSet).values(**values)
    update_cols = {k: v for k, v in values.items() if k != "code"}
    stmt = stmt.on_conflict_do_update(index_elements=["code"], set_=update_cols)
    await session.execute(stmt)


async def _upsert_card(
    session: AsyncSession, set_code: str, card_data: dict[str, Any]
) -> None:
    values = _card_values(set_code, card_data)
    stmt = insert(Card).values(**values)
    update_cols = {k: v for k, v in values.items() if k != "id"}
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
    """
    payload = await client.fetch_all_printings()
    all_sets: dict[str, Any] = payload["data"]

    sets_upserted = 0
    cards_upserted = 0
    for set_code, set_data in all_sets.items():
        await _upsert_set(session, set_code, set_data)
        sets_upserted += 1
        for card_data in set_data.get("cards", []):
            await _upsert_card(session, set_code, card_data)
            cards_upserted += 1

    await session.commit()
    return ImportResult(sets_upserted=sets_upserted, cards_upserted=cards_upserted)
