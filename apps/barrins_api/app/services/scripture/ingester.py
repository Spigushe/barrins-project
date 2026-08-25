"""Upserts one scraped tournament (one JSON archive file) into `bs_*` (T3).

`INSERT ... ON CONFLICT DO UPDATE ... RETURNING id`, one statement per
row, in FK order (tournament -> decks/rounds -> deck_cards/round_matches
-> standings) — the upsert mechanism recorded as groundwork in
docs/project/v2.0.0-bump/t3-scripture-ingestion-pipeline/index.md. Every
table's T2 natural-key unique constraint makes this idempotent with no
prior SELECT, unlike S8's importer (`app/services/mtgjson/importer.py`),
which chunks multi-row upserts — that optimization was for AllPrintings'
100k+ rows; a single tournament file's row counts don't warrant it.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import and_, delete, or_, select
from sqlalchemy import insert as sa_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scripture import (
    BSDeck,
    BSDeckBoard,
    BSDeckCard,
    BSRound,
    BSRoundMatch,
    BSSource,
    BSStanding,
    BSTournament,
)
from app.schemas.scripture_ingest import (
    RequestDeck,
    RequestMatch,
    RequestRound,
    RequestStanding,
    RequestTournament,
    ScriptureIngestRequest,
)
from app.services.scripture.card_resolver import resolve_card_name


@dataclass(frozen=True)
class IngestResult:
    """Outcome of a single `ingest_scrape` call."""

    tournament_id: uuid.UUID
    decks_upserted: int
    deck_cards_upserted: int
    rounds_upserted: int
    round_matches_upserted: int
    standings_upserted: int
    skipped_card_names: list[str]


def _excluded_set(
    stmt, values: dict[str, object], exclude: set[str]
) -> dict[str, object]:
    """Builds an `on_conflict_do_update` `set_` dict mechanically.

    Every key in `values` except `exclude` (the conflict/key columns),
    mapped to `stmt.excluded.<col>` — mirrors the pattern
    `app/services/mtgjson/importer.py` already uses for its chunked
    upserts. Removes the risk of a column being added to a `values()`
    call here but the update side forgetting to follow: with a
    hand-written `set_` dict, a forgotten column inserts fine on new rows
    but silently never updates on conflict.
    """
    return {k: getattr(stmt.excluded, k) for k in values if k not in exclude}


async def _upsert_tournament(
    session: AsyncSession, source: BSSource, tournament: RequestTournament
) -> uuid.UUID:
    values: dict[str, object] = {
        "source": source,
        "date": tournament.date,
        "name": tournament.name,
        "url": tournament.url,
        "format": tournament.format,
        "players": tournament.players,
    }
    stmt = pg_insert(BSTournament).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["url"],
        set_=_excluded_set(stmt, values, exclude={"url"}),
    ).returning(BSTournament.id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def _upsert_deck(
    session: AsyncSession, tournament_id: uuid.UUID, deck: RequestDeck
) -> uuid.UUID:
    values: dict[str, object] = {
        "tournament_id": tournament_id,
        "date": deck.date,
        "player": deck.player,
        "result": deck.result,
        "anchor_uri": deck.anchor_uri,
        "notes": deck.notes,
    }
    stmt = pg_insert(BSDeck).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["tournament_id", "anchor_uri"],
        set_=_excluded_set(stmt, values, exclude={"tournament_id", "anchor_uri"}),
    ).returning(BSDeck.id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def _replace_deck_cards(
    session: AsyncSession, deck_id: uuid.UUID, deck: RequestDeck, skipped: set[str]
) -> int:
    """Delete-and-reinsert every mainboard/sideboard line for `deck_id`.

    MTGO decklists are mutable for ~3 days after publication (2026-08-07
    decision, T3 doc) — a naive row-level upsert would leave stale rows
    for any card removed during that window. Deleting and reinserting in
    the same transaction as the deck's own upsert avoids that; the delete
    is scoped to this `deck_id` alone, never touching another deck's rows.

    Card names that don't resolve against S8's `cards` data (typos,
    unusual promos MTGJSON doesn't carry, ...) are skipped — not stored —
    and added to `skipped`, per the 2026-08-07 decision that one bad name
    shouldn't lose an otherwise-good tournament's data.
    """
    await session.execute(delete(BSDeckCard).where(BSDeckCard.deck_id == deck_id))

    # Two raw spellings can resolve to the same canonical (board, name)
    # after normalization — merge by summing counts so the multi-row
    # insert below never violates uq_bs_deck_cards_entry within itself.
    merged: dict[tuple[BSDeckBoard, str], int] = {}
    for board, entries in (
        (BSDeckBoard.mainboard, deck.mainboard),
        (BSDeckBoard.sideboard, deck.sideboard or []),
    ):
        for entry in entries:
            canonical_name = await resolve_card_name(session, entry.name)
            if canonical_name is None:
                skipped.add(entry.name)
                continue
            key = (board, canonical_name)
            merged[key] = merged.get(key, 0) + entry.count

    if not merged:
        return 0

    values = [
        {"deck_id": deck_id, "board": board, "card_name": card_name, "count": count}
        for (board, card_name), count in merged.items()
    ]
    await session.execute(sa_insert(BSDeckCard).values(values))
    return len(values)


async def _upsert_round(
    session: AsyncSession,
    tournament_id: uuid.UUID,
    round_: RequestRound,
    sequence: int,
) -> uuid.UUID:
    values: dict[str, object] = {
        "tournament_id": tournament_id,
        "round_name": round_.round_name,
        "sequence": sequence,
    }
    stmt = pg_insert(BSRound).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["tournament_id", "round_name"],
        set_=_excluded_set(stmt, values, exclude={"tournament_id"}),
    ).returning(BSRound.id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def _upsert_match(
    session: AsyncSession, round_id: uuid.UUID, match: RequestMatch
) -> None:
    """Upserts one pairing, resolving player order against any existing row first.

    `uq_bs_round_matches_pairing` is order-sensitive on `(round_id,
    player_1, player_2)`. A resubmission of the same real-world pairing
    with the two players swapped between scrapes of the same round (a
    plausible source-side inconsistency, not something this schema can
    rule out) would otherwise insert a second row instead of updating the
    first — silently breaking the idempotency this whole pipeline is
    built on. Looking the pairing up in either order first, and reusing
    whichever order is already stored, keeps the upsert idempotent
    regardless of which order a given scrape reports it in.
    """
    player_1, player_2 = match.player_1, match.player_2
    existing = (
        await session.execute(
            select(BSRoundMatch.player_1, BSRoundMatch.player_2).where(
                BSRoundMatch.round_id == round_id,
                or_(
                    and_(
                        BSRoundMatch.player_1 == player_1,
                        BSRoundMatch.player_2 == player_2,
                    ),
                    and_(
                        BSRoundMatch.player_1 == player_2,
                        BSRoundMatch.player_2 == player_1,
                    ),
                ),
            )
        )
    ).first()
    if existing is not None:
        player_1, player_2 = existing

    values: dict[str, object] = {
        "round_id": round_id,
        "player_1": player_1,
        "player_2": player_2,
        "result": match.result,
    }
    stmt = pg_insert(BSRoundMatch).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["round_id", "player_1", "player_2"],
        set_=_excluded_set(stmt, values, exclude={"round_id", "player_1", "player_2"}),
    )
    await session.execute(stmt)


async def _upsert_standing(
    session: AsyncSession, tournament_id: uuid.UUID, standing: RequestStanding
) -> None:
    values: dict[str, object] = {
        "tournament_id": tournament_id,
        "rank": standing.rank,
        "player": standing.player,
        "points": standing.points,
        "wins": standing.wins,
        "losses": standing.losses,
        "draws": standing.draws,
        "omwp": standing.omwp,
        "gwp": standing.gwp,
        "ogwp": standing.ogwp,
    }
    stmt = pg_insert(BSStanding).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["tournament_id", "player"],
        set_=_excluded_set(stmt, values, exclude={"tournament_id", "player"}),
    )
    await session.execute(stmt)


async def ingest_scrape(
    session: AsyncSession, payload: ScriptureIngestRequest
) -> IngestResult:
    """Upserts one scraped tournament into `bs_*`.

    Idempotent: re-ingesting the same file is a no-op on rows that didn't
    change, and reflects any edit MTGO made within its ~3-day mutability
    window (deck cards are deleted-and-reinserted every time, see
    `_replace_deck_cards`). Commits once at the end — a failure partway
    through rolls back the whole file rather than leaving it half-ingested.

    The `*_upserted` counts on the result are counts of *distinct*
    persisted rows (dedup'd by each table's natural key), not raw counts
    of entries in `payload` — a payload that lists the same deck/round/
    standing/match twice (a scraper quirk, an overlapping bulk-replay
    window) collapses to one row via `ON CONFLICT`, and the reported
    count reflects that instead of overstating what was actually written.
    """
    skipped: set[str] = set()

    tournament_id = await _upsert_tournament(
        session, payload.source, payload.tournament
    )

    deck_ids: set[uuid.UUID] = set()
    deck_cards_upserted = 0
    for deck in payload.decks:
        deck_id = await _upsert_deck(session, tournament_id, deck)
        deck_ids.add(deck_id)
        deck_cards_upserted += await _replace_deck_cards(
            session, deck_id, deck, skipped
        )

    round_ids: set[uuid.UUID] = set()
    round_match_keys: set[tuple[uuid.UUID, frozenset[str]]] = set()
    for sequence, round_ in enumerate(payload.rounds):
        round_id = await _upsert_round(session, tournament_id, round_, sequence)
        round_ids.add(round_id)
        for match in round_.matches:
            await _upsert_match(session, round_id, match)
            round_match_keys.add(
                (round_id, frozenset((match.player_1, match.player_2)))
            )

    standing_players: set[str] = set()
    for standing in payload.standings:
        await _upsert_standing(session, tournament_id, standing)
        standing_players.add(standing.player)

    await session.commit()

    return IngestResult(
        tournament_id=tournament_id,
        decks_upserted=len(deck_ids),
        deck_cards_upserted=deck_cards_upserted,
        rounds_upserted=len(round_ids),
        round_matches_upserted=len(round_match_keys),
        standings_upserted=len(standing_players),
        skipped_card_names=sorted(skipped),
    )
