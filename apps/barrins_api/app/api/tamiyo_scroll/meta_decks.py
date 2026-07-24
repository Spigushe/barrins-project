"""Routes /meta-decks (opponent roster + expected metagame, CRUD)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import TSMetaDeck
from app.schemas.responses_tamiyo_scroll import ResponseMetaDeck
from app.schemas.tamiyo_scroll import MetaDeckWrite
from app.services.tamiyo_scroll.ownership import ResolvedOwner

router = APIRouter()


async def _get_owned_meta_deck(
    session: DatabaseSession, deck_id: uuid.UUID, owner_id: uuid.UUID
) -> TSMetaDeck:
    result = await session.execute(
        select(TSMetaDeck).where(
            TSMetaDeck.id == deck_id, TSMetaDeck.owner_id == owner_id
        )
    )
    deck = result.scalar_one_or_none()
    if deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Roster deck not found."
        )
    return deck


def _apply_payload(deck: TSMetaDeck, payload: MetaDeckWrite) -> None:
    deck.name = payload.name
    deck.tier = Decimal(str(payload.tier))
    deck.category = payload.category
    deck.decklist_notes = payload.decklist_notes
    deck.top8 = payload.top8
    deck.presence = payload.presence
    deck.expected = payload.expected
    deck.tests_status = payload.tests_status


@router.get("/meta-decks", response_model=list[ResponseMetaDeck])
async def list_meta_decks(
    session: DatabaseSession,
    owner: ResolvedOwner,
    include_archived: bool = False,
) -> list[ResponseMetaDeck]:
    stmt = select(TSMetaDeck).where(TSMetaDeck.owner_id == owner.id)
    if not include_archived:
        stmt = stmt.where(TSMetaDeck.archived_at.is_(None))
    stmt = stmt.order_by(TSMetaDeck.name)
    result = await session.execute(stmt)
    return [ResponseMetaDeck.model_validate(d) for d in result.scalars().all()]


@router.post(
    "/meta-decks", response_model=ResponseMetaDeck, status_code=status.HTTP_201_CREATED
)
async def create_meta_deck(
    payload: MetaDeckWrite,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseMetaDeck:
    deck = TSMetaDeck(owner_id=current_user.id)
    _apply_payload(deck, payload)
    session.add(deck)
    await session.commit()
    await session.refresh(deck)
    return ResponseMetaDeck.model_validate(deck)


@router.put("/meta-decks/{deck_id}", response_model=ResponseMetaDeck)
async def update_meta_deck(
    deck_id: uuid.UUID,
    payload: MetaDeckWrite,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseMetaDeck:
    deck = await _get_owned_meta_deck(session, deck_id, current_user.id)
    _apply_payload(deck, payload)
    session.add(deck)
    await session.commit()
    await session.refresh(deck)
    return ResponseMetaDeck.model_validate(deck)


@router.delete("/meta-decks/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_meta_deck(
    deck_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Archive the deck (`archived_at`) — never a SQL DELETE, cf. plan Option G."""
    deck = await _get_owned_meta_deck(session, deck_id, current_user.id)
    deck.archived_at = datetime.now(UTC)
    session.add(deck)
    await session.commit()
