"""Routes /decks (global index) and /decks/{id} (detail) -- public, no auth."""

import uuid
from datetime import UTC, datetime
from datetime import date as date_type

from fastapi import APIRouter, HTTPException, Query, status

from app.database.session import DatabaseSession
from app.models.scripture import BSSource
from app.schemas.responses_tolaria_news import DeckDetail, DeckListItem, Envelope, Meta
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
