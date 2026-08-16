"""Tournament list/detail queries backing the Tolaria News BFF."""

import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Integer, cast, func, select, tuple_
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
from app.schemas.responses_tolaria_news import (
    CommanderRef,
    Page,
    RoundMatchOut,
    RoundOut,
    StandingRow,
    TournamentDeckSummary,
    TournamentDetail,
    TournamentSummary,
)
from app.services.tolaria_news.decks import (
    DUEL_COMMANDER_FORMAT,
    commander_ref,
    resolved_cards,
)
from app.services.tolaria_news.pagination import decode_cursor, encode_cursor

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50

#: Sentinel rank for decks with no numeric-leading `result` (no result yet,
#: or a non-numeric one like "DQ") -- sorts after every real placement.
_UNRESULTED_RANK = 2**31 - 1

#: `result`'s leading integer ("5-8" -> 5, "1" -> 1), or `NULL` if `result`
#: is `NULL` or doesn't start with a digit -- `coalesce`d to
#: `_UNRESULTED_RANK` at each use site so unresulted decks sort last.
_RESULT_LEADING_NUMBER = cast(func.substring(BSDeck.result, r"^\d+"), Integer)


async def latest_sync(session: AsyncSession) -> datetime | None:
    """Most recent `bs_tournaments.created_at` -- freshness proxy for `Meta`."""
    return (
        await session.execute(select(func.max(BSTournament.created_at)))
    ).scalar_one()


async def list_tournaments(
    session: AsyncSession,
    *,
    source: BSSource | None,
    format_: str | None,
    date_from: date_type | None,
    date_to: date_type | None,
    cursor: str | None,
    limit: int,
) -> tuple[list[TournamentSummary], Page]:
    limit = min(limit, _MAX_LIMIT) if limit else _DEFAULT_LIMIT
    stmt = select(BSTournament).order_by(
        BSTournament.date.desc(), BSTournament.id.desc()
    )
    if source is not None:
        stmt = stmt.where(BSTournament.source == source)
    if format_ is not None:
        stmt = stmt.where(BSTournament.format == format_)
    if date_from is not None:
        stmt = stmt.where(BSTournament.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(BSTournament.date <= date_to)
    if cursor is not None:
        cursor_date, cursor_id = decode_cursor(cursor)
        stmt = stmt.where(
            tuple_(BSTournament.date, BSTournament.id)
            < (date_type.fromisoformat(cursor_date), uuid.UUID(cursor_id))
        )
    rows = (await session.execute(stmt.limit(limit + 1))).scalars().all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        encode_cursor(rows[-1].date.isoformat(), str(rows[-1].id))
        if has_more and rows
        else None
    )
    return (
        [TournamentSummary.model_validate(t) for t in rows],
        Page(next_cursor=next_cursor, limit=limit),
    )


async def get_tournament(
    session: AsyncSession, tournament_id: uuid.UUID
) -> TournamentDetail | None:
    tournament = await session.get(BSTournament, tournament_id)
    if tournament is None:
        return None
    deck_count = (
        await session.execute(
            select(func.count())
            .select_from(BSDeck)
            .where(BSDeck.tournament_id == tournament_id)
        )
    ).scalar_one()
    standing_count = (
        await session.execute(
            select(func.count())
            .select_from(BSStanding)
            .where(BSStanding.tournament_id == tournament_id)
        )
    ).scalar_one()
    return TournamentDetail(
        **TournamentSummary.model_validate(tournament).model_dump(),
        deck_count=deck_count,
        standing_count=standing_count,
    )


async def list_decks(
    session: AsyncSession,
    tournament_id: uuid.UUID,
    *,
    cursor: str | None,
    limit: int,
) -> tuple[list[TournamentDeckSummary], Page]:
    """Decks entered in one tournament, ordered by placement (`result`'s
    leading number, e.g. "5-8" ranks as 5th) then player name -- decks
    with no numeric-leading result (not yet resolved, or e.g. "DQ") sort
    last. Each deck carries its `commanders` (populated only for Duel
    Commander tournaments, same guard `get_deck` applies)."""
    limit = min(limit, _MAX_LIMIT) if limit else _DEFAULT_LIMIT
    rank_expr = func.coalesce(_RESULT_LEADING_NUMBER, _UNRESULTED_RANK)
    stmt = (
        select(BSDeck, rank_expr)
        .where(BSDeck.tournament_id == tournament_id)
        .order_by(rank_expr.asc(), BSDeck.player.asc(), BSDeck.id.asc())
    )
    if cursor is not None:
        cursor_rank, cursor_player, cursor_id = decode_cursor(cursor)
        stmt = stmt.where(
            tuple_(rank_expr, BSDeck.player, BSDeck.id)
            > (int(cursor_rank), cursor_player, uuid.UUID(cursor_id))
        )
    rows = (await session.execute(stmt.limit(limit + 1))).all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        encode_cursor(str(rows[-1][1]), rows[-1][0].player, str(rows[-1][0].id))
        if has_more and rows
        else None
    )
    decks = [row[0] for row in rows]

    commanders_by_deck: dict[uuid.UUID, list[CommanderRef]] = {
        deck.id: [] for deck in decks
    }
    tournament = await session.get(BSTournament, tournament_id)
    if tournament is not None and tournament.format == DUEL_COMMANDER_FORMAT and decks:
        card_rows = (
            (
                await session.execute(
                    select(BSDeckCard).where(
                        BSDeckCard.deck_id.in_([d.id for d in decks]),
                        BSDeckCard.board == BSDeckBoard.sideboard,
                    )
                )
            )
            .scalars()
            .all()
        )
        resolved = await resolved_cards(session, card_rows)
        for card in card_rows:
            commanders_by_deck[card.deck_id].append(
                commander_ref(card.card_name, resolved[card.id])
            )

    return (
        [
            TournamentDeckSummary(
                id=deck.id,
                tournament_id=deck.tournament_id,
                date=deck.date,
                player=deck.player,
                result=deck.result,
                anchor_uri=deck.anchor_uri,
                commanders=commanders_by_deck[deck.id],
            )
            for deck in decks
        ],
        Page(next_cursor=next_cursor, limit=limit),
    )


async def get_bracket(
    session: AsyncSession, tournament_id: uuid.UUID
) -> list[RoundOut]:
    """Every round of a tournament's elimination bracket, in scrape order.

    Ordered by `BSRound.sequence` (the scrape/bracket order T3's
    ingestion recorded) -- `created_at` can't do this (transaction-scoped
    `now()` ties every round of one ingest) and `round_name` is free text,
    not reliably sortable. Swiss-only tournaments (no elimination bracket
    scraped) return an empty list, not a 404 -- the tournament exists, it
    just has no bracket.
    """
    rounds = (
        (
            await session.execute(
                select(BSRound)
                .where(BSRound.tournament_id == tournament_id)
                .order_by(BSRound.sequence.asc())
            )
        )
        .scalars()
        .all()
    )
    if not rounds:
        return []

    matches_by_round: dict[uuid.UUID, list[BSRoundMatch]] = {r.id: [] for r in rounds}
    all_matches = (
        (
            await session.execute(
                select(BSRoundMatch)
                .where(BSRoundMatch.round_id.in_(matches_by_round.keys()))
                .order_by(BSRoundMatch.player_1.asc())
            )
        )
        .scalars()
        .all()
    )
    for match in all_matches:
        matches_by_round[match.round_id].append(match)

    return [
        RoundOut(
            round_name=r.round_name,
            matches=[RoundMatchOut.model_validate(m) for m in matches_by_round[r.id]],
        )
        for r in rounds
    ]


async def list_standings(
    session: AsyncSession,
    tournament_id: uuid.UUID,
    *,
    cursor: str | None,
    limit: int,
) -> tuple[list[StandingRow], Page]:
    limit = min(limit, _MAX_LIMIT) if limit else _DEFAULT_LIMIT
    stmt = (
        select(BSStanding)
        .where(BSStanding.tournament_id == tournament_id)
        .order_by(BSStanding.rank.asc())
    )
    if cursor is not None:
        (cursor_rank,) = decode_cursor(cursor)
        stmt = stmt.where(BSStanding.rank > int(cursor_rank))
    rows = (await session.execute(stmt.limit(limit + 1))).scalars().all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = encode_cursor(str(rows[-1].rank)) if has_more and rows else None
    return (
        [StandingRow.model_validate(r) for r in rows],
        Page(next_cursor=next_cursor, limit=limit),
    )
