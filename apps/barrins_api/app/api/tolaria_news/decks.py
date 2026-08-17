"""Routes /decks (global index) and /decks/{id} (detail) -- public, no auth."""

import uuid
from datetime import UTC, datetime
from datetime import date as date_type

from fastapi import APIRouter, HTTPException, Query, status

from app.database.session import DatabaseSession
from app.models.scripture import BSSource
from app.schemas.responses_tolaria_news import (
    CommanderTrendsResponse,
    DeckDetail,
    DeckListItem,
    Envelope,
    Meta,
    StaplesResponse,
    TrendWindowMode,
)
from app.services.tolaria_news import decks as service
from app.services.tolaria_news import tournaments as tournaments_service
from app.services.tolaria_news.pagination import decode_cursor

router = APIRouter()


async def _meta(session: DatabaseSession) -> Meta:
    return Meta(
        generated_at=datetime.now(UTC),
        source_synced_at=await tournaments_service.latest_sync(session),
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


@router.get("/decks", response_model=Envelope[list[DeckListItem]])
async def list_decks(
    session: DatabaseSession,
    player: str | None = None,
    source: BSSource | None = None,
    commander: str | None = None,
    colors: list[str] | None = Query(None),
    sizes: list[service.TournamentSizeBucket] | None = Query(None),
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    cursor: str | None = None,
    limit: int = 20,
) -> Envelope[list[DeckListItem]]:
    _decode_cursor_or_400(cursor)
    data, page = await service.list_decks(
        session,
        player=player,
        source=source,
        commander=commander,
        colors=frozenset(colors) if colors else None,
        sizes=frozenset(sizes) if sizes else None,
        date_from=date_from,
        date_to=date_to,
        cursor=cursor,
        limit=limit,
    )
    return Envelope(data=data, meta=await _meta(session), page=page)


@router.get("/decks/commanders", response_model=Envelope[list[str]])
async def list_commanders(session: DatabaseSession) -> Envelope[list[str]]:
    """Must stay registered before `/decks/{deck_id}` -- both match
    `/decks/<segment>`, and route matching is registration-order, so
    `{deck_id}` would otherwise swallow this path and fail UUID parsing
    with a 422 instead of reaching this handler."""
    data = await service.list_commanders(session)
    return Envelope(data=data, meta=await _meta(session))


@router.get(
    "/decks/commanders/trending",
    response_model=Envelope[CommanderTrendsResponse],
)
async def list_trending_commanders(
    session: DatabaseSession,
    mode: TrendWindowMode = "rolling_30d",
    period_offset: int = 0,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
) -> Envelope[CommanderTrendsResponse]:
    """Top 10 commanders (or partner pairs) by deck count in `mode`'s
    window, each with a per-bucket play-count trend. `period_offset`
    only applies to `mode=banlist_period` (0 = the period containing
    today, 1 = the one before that, ...). `date_from` is required (and
    `date_to` optional, defaulting server-side to today) when
    `mode=custom` -- e.g. the frontend's "20-life decks" preset (a fixed
    start date, open-ended end) or its date-picker range (both given)."""
    if mode == "custom" and date_from is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from is required when mode=custom.",
        )
    if date_to is not None and date_from is not None and date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must not be before date_from.",
        )
    data = await service.list_trending_commanders(
        session,
        mode=mode,
        period_offset=period_offset,
        date_from=date_from,
        date_to=date_to,
    )
    return Envelope(data=data, meta=await _meta(session))


@router.get("/decks/staples", response_model=Envelope[StaplesResponse])
async def get_staples(
    session: DatabaseSession,
    date_from: date_type,
    date_to: date_type,
    min_percentage: float = service.DEFAULT_STAPLE_MIN_PERCENTAGE,
    fallback_min_percentage: float = service.DEFAULT_STAPLE_FALLBACK_MIN_PERCENTAGE,
) -> Envelope[StaplesResponse]:
    """Must stay registered before `/decks/{deck_id}` -- both match
    `/decks/<segment>`, and route matching is registration-order (same
    reasoning as `list_commanders`'s own placement above).

    `min_percentage`/`fallback_min_percentage` default to
    `list_staples`'s own tuned defaults but are overridable here -- this
    threshold has already been retuned once against real data, so a query
    param (not a hardcoded constant only) keeps the next retune a
    parameter change, not a deploy."""
    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must not be before date_from.",
        )
    data = await service.list_staples(
        session,
        date_from=date_from,
        date_to=date_to,
        min_percentage=min_percentage,
        fallback_min_percentage=fallback_min_percentage,
    )
    return Envelope(data=data, meta=await _meta(session))


@router.get("/decks/{deck_id}", response_model=Envelope[DeckDetail])
async def get_deck(
    deck_id: uuid.UUID, session: DatabaseSession
) -> Envelope[DeckDetail]:
    deck = await service.get_deck(session, deck_id)
    if deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found."
        )
    return Envelope(data=deck, meta=await _meta(session))
