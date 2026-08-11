"""Tournament list/detail queries backing the Tolaria News BFF."""

import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scripture import BSDeck, BSSource, BSStanding, BSTournament
from app.schemas.responses_tolaria_news import (
    DeckSummary,
    Page,
    StandingRow,
    TournamentDetail,
    TournamentSummary,
)
from app.services.tolaria_news.pagination import decode_cursor, encode_cursor

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50


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
) -> tuple[list[DeckSummary], Page]:
    limit = min(limit, _MAX_LIMIT) if limit else _DEFAULT_LIMIT
    stmt = (
        select(BSDeck)
        .where(BSDeck.tournament_id == tournament_id)
        .order_by(BSDeck.player.asc(), BSDeck.id.asc())
    )
    if cursor is not None:
        cursor_player, cursor_id = decode_cursor(cursor)
        stmt = stmt.where(
            tuple_(BSDeck.player, BSDeck.id) > (cursor_player, uuid.UUID(cursor_id))
        )
    rows = (await session.execute(stmt.limit(limit + 1))).scalars().all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        encode_cursor(rows[-1].player, str(rows[-1].id)) if has_more and rows else None
    )
    return (
        [DeckSummary.model_validate(d) for d in rows],
        Page(next_cursor=next_cursor, limit=limit),
    )


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
