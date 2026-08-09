"""Upserts MTGJSON's `AllPrintings.json` into the `mj_sets`/`mj_cards` tables.

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

Progress is tracked live in `mj_import_runs` (2026-08-09 addition, same
day as the memory fix above): `import_all_printings` only commits its
`mj_sets`/`mj_cards` writes once at the end, so any other session --
including a status poll -- can't see them mid-run. `_ImportRunTracker`
writes to `mj_import_runs` through its own session, committed immediately
at the same granularity as `_UPSERT_CHUNK_SIZE`, so `GET
/mtgjson/import/status` can show real progress instead of nothing until
the import finishes.
"""

import uuid
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_config import get_logger
from app.database.connection import AsyncSessionLocal
from app.models.mtgjson import Card, MTGJSONImportRun, MTGSet
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
        update_cols: dict[str, Any] = {
            k: stmt.excluded[k] for k in chunk[0] if k != "code"
        }
        # The raw Core upsert bypasses the ORM unit-of-work path, so the
        # model's `onupdate=func.now()` (app/models/mtgjson.py) never fires
        # on conflict -- set it explicitly or a re-import leaves
        # `updated_at` (and GET /mtgjson/status's last_imported_at) frozen
        # at each row's original insert time forever.
        update_cols["updated_at"] = func.now()
        stmt = stmt.on_conflict_do_update(index_elements=["code"], set_=update_cols)
        await session.execute(stmt)


async def _upsert_cards(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    for chunk in _chunked(rows, _UPSERT_CHUNK_SIZE):
        stmt = insert(Card).values(chunk)
        update_cols: dict[str, Any] = {
            k: stmt.excluded[k] for k in chunk[0] if k != "id"
        }
        update_cols["updated_at"] = func.now()  # see _upsert_sets
        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_cols)
        await session.execute(stmt)


#: Called with (sets_upserted, cards_upserted) after a flush actually
#: writes something, so a caller can track progress at the same
#: granularity as the upsert chunking -- see `_ImportRunTracker`.
_ProgressCallback = Callable[[int, int], Awaitable[None]]


async def _no_op_progress(sets_upserted: int, cards_upserted: int) -> None:
    pass


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
    on_progress: _ProgressCallback = _no_op_progress
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

        flushed = False
        if len(self._pending_sets) >= _UPSERT_CHUNK_SIZE:
            await self._flush_sets()
            flushed = True
        if len(self._pending_cards) >= _UPSERT_CHUNK_SIZE:
            await self._flush_sets()
            await self._flush_cards()
            flushed = True
        if flushed:
            await self.on_progress(self.sets_upserted, self.cards_upserted)

    async def flush(self) -> None:
        await self._flush_sets()
        await self._flush_cards()
        await self.on_progress(self.sets_upserted, self.cards_upserted)

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


class _ImportRunTracker:
    """Records import progress in `mj_import_runs`, independent of the main
    import transaction: `import_all_printings` only commits its sets/cards
    writes once at the end (see module docstring), so a status poll needs
    a separately and immediately committed row to see progress mid-run
    rather than nothing until the whole import finishes.

    Each method opens its own short-lived session via `AsyncSessionLocal`
    and commits before returning.
    """

    def __init__(self) -> None:
        self._run_id: uuid.UUID | None = None

    async def start(self) -> None:
        async with AsyncSessionLocal() as session:
            # Only one admin-triggered import runs at a time, so a row
            # still "running" here was orphaned by a crash (e.g. the
            # 2026-08-09 OOM kill) rather than a concurrent run -- self-heal
            # it instead of leaving it stuck forever.
            stale_runs = (
                await session.execute(
                    select(MTGJSONImportRun).where(MTGJSONImportRun.status == "running")
                )
            ).scalars()
            for stale_run in stale_runs:
                stale_run.status = "failed"
                stale_run.finished_at = datetime.now(UTC)
                stale_run.error_message = "Interrupted by a new import run."

            run = MTGJSONImportRun(status="running")
            session.add(run)
            await session.commit()
            self._run_id = run.id

    async def progress(self, sets_upserted: int, cards_upserted: int) -> None:
        async with AsyncSessionLocal() as session:
            run = await session.get(MTGJSONImportRun, self._run_id)
            assert run is not None
            run.sets_upserted = sets_upserted
            run.cards_upserted = cards_upserted
            await session.commit()

    async def finish(self, sets_upserted: int, cards_upserted: int) -> None:
        async with AsyncSessionLocal() as session:
            run = await session.get(MTGJSONImportRun, self._run_id)
            assert run is not None
            run.status = "succeeded"
            run.finished_at = datetime.now(UTC)
            run.sets_upserted = sets_upserted
            run.cards_upserted = cards_upserted
            await session.commit()

    async def fail(self, error: BaseException) -> None:
        async with AsyncSessionLocal() as session:
            run = await session.get(MTGJSONImportRun, self._run_id)
            assert run is not None
            run.status = "failed"
            run.finished_at = datetime.now(UTC)
            run.error_message = str(error)[:2000]
            await session.commit()


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
    every row into memory first -- see the module docstring. Progress is
    tracked separately, in `mj_import_runs` via `_ImportRunTracker` -- see
    its docstring for why that can't just be another read against
    `session`.
    """
    tracker = _ImportRunTracker()
    await tracker.start()

    buffer = _ImportBuffer(session, on_progress=tracker.progress)
    try:
        async for set_code, set_data in client.stream_sets():
            await buffer.add_set(set_code, set_data)
        await buffer.flush()
        await session.commit()
    except Exception as exc:
        await tracker.fail(exc)
        raise

    await tracker.finish(
        sets_upserted=buffer.sets_upserted, cards_upserted=buffer.cards_upserted
    )
    return ImportResult(
        sets_upserted=buffer.sets_upserted, cards_upserted=buffer.cards_upserted
    )
