"""Routes /tournaments (list/detail, decks, standings) -- public, no auth."""

import uuid
from datetime import UTC, datetime
from datetime import date as date_type

from fastapi import APIRouter, HTTPException, Query, status

from app.database.session import DatabaseSession
from app.models.scripture import BSSource
from app.schemas.responses_tolaria_news import (
    Envelope,
    Meta,
    RoundOut,
    StandingRow,
    TournamentDeckSummary,
    TournamentDetail,
    TournamentSummary,
)
from app.services.tolaria_news import tournaments as service
from app.services.tolaria_news.pagination import decode_cursor

router = APIRouter()


async def _meta(session: DatabaseSession) -> Meta:
    return Meta(
        generated_at=datetime.now(UTC),
        source_synced_at=await service.latest_sync(session),
    )


def _decode_cursor_or_400(cursor: str | None) -> None:
    """Validity probe -- the service layer decodes the same cursor again
    for real; this only turns a malformed one into a clean 400 instead
    of a 500."""
    if cursor is None:
        return
    try:
        decode_cursor(cursor)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor."
        ) from exc


@router.get("/tournaments", response_model=Envelope[list[TournamentSummary]])
async def list_tournaments(
    session: DatabaseSession,
    source: BSSource | None = None,
    format: str | None = None,  # noqa: A002 -- matches the query param name
    sizes: list[service.TournamentSizeBucket] | None = Query(None),
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    cursor: str | None = None,
    limit: int = 20,
) -> Envelope[list[TournamentSummary]]:
    _decode_cursor_or_400(cursor)
    data, page = await service.list_tournaments(
        session,
        source=source,
        format_=format,
        sizes=frozenset(sizes) if sizes else None,
        date_from=date_from,
        date_to=date_to,
        cursor=cursor,
        limit=limit,
    )
    return Envelope(data=data, meta=await _meta(session), page=page)


@router.get("/tournaments/{tournament_id}", response_model=Envelope[TournamentDetail])
async def get_tournament(
    tournament_id: uuid.UUID, session: DatabaseSession
) -> Envelope[TournamentDetail]:
    tournament = await service.get_tournament(session, tournament_id)
    if tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found."
        )
    return Envelope(data=tournament, meta=await _meta(session))


@router.get(
    "/tournaments/{tournament_id}/decks",
    response_model=Envelope[list[TournamentDeckSummary]],
)
async def list_tournament_decks(
    tournament_id: uuid.UUID,
    session: DatabaseSession,
    cursor: str | None = None,
    limit: int = 20,
) -> Envelope[list[TournamentDeckSummary]]:
    _decode_cursor_or_400(cursor)
    data, page = await service.list_decks(
        session, tournament_id, cursor=cursor, limit=limit
    )
    return Envelope(data=data, meta=await _meta(session), page=page)


@router.get(
    "/tournaments/{tournament_id}/bracket",
    response_model=Envelope[list[RoundOut]],
)
async def get_tournament_bracket(
    tournament_id: uuid.UUID, session: DatabaseSession
) -> Envelope[list[RoundOut]]:
    data = await service.get_bracket(session, tournament_id)
    return Envelope(data=data, meta=await _meta(session))


@router.get(
    "/tournaments/{tournament_id}/standings",
    response_model=Envelope[list[StandingRow]],
)
async def list_tournament_standings(
    tournament_id: uuid.UUID,
    session: DatabaseSession,
    cursor: str | None = None,
    limit: int = 20,
) -> Envelope[list[StandingRow]]:
    _decode_cursor_or_400(cursor)
    data, page = await service.list_standings(
        session, tournament_id, cursor=cursor, limit=limit
    )
    return Envelope(data=data, meta=await _meta(session), page=page)
