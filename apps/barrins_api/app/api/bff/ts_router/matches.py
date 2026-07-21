"""Routes /matches (BO3 match log, CRUD)."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import TSMatch, TSMetaDeck, TSPersonalDeck
from app.schemas.responses_tamiyo_scroll import ResponseMatch
from app.schemas.tamiyo_scroll import MatchWrite
from app.services.tamiyo_scroll.ownership import ResolvedOwner

router = APIRouter()


async def _get_owned_match(
    session: DatabaseSession, match_id: uuid.UUID, owner_id: uuid.UUID
) -> TSMatch:
    result = await session.execute(
        select(TSMatch).where(TSMatch.id == match_id, TSMatch.owner_id == owner_id)
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match not found."
        )
    return match


async def _validate_match_refs(
    session: DatabaseSession,
    owner_id: uuid.UUID,
    personal_deck_id: uuid.UUID,
    opponent_deck_id: uuid.UUID,
) -> None:
    personal_result = await session.execute(
        select(TSPersonalDeck.id).where(
            TSPersonalDeck.id == personal_deck_id, TSPersonalDeck.owner_id == owner_id
        )
    )
    if personal_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Personal deck not found."
        )

    opponent_result = await session.execute(
        select(TSMetaDeck.id).where(
            TSMetaDeck.id == opponent_deck_id, TSMetaDeck.owner_id == owner_id
        )
    )
    if opponent_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Opponent deck not found."
        )


def _apply_payload(match: TSMatch, payload: MatchWrite) -> None:
    match.personal_deck_id = payload.personal_deck_id
    match.opponent_deck_id = payload.opponent_deck_id
    match.on_play = payload.on_play
    match.game1 = payload.game1
    match.game2 = payload.game2
    match.game3 = payload.game3
    match.opening_hand = payload.opening_hand
    match.turning_point = payload.turning_point
    match.final_turn = payload.final_turn


@router.get("/matches", response_model=list[ResponseMatch])
async def list_matches(
    session: DatabaseSession, owner: ResolvedOwner
) -> list[ResponseMatch]:
    result = await session.execute(
        select(TSMatch)
        .where(TSMatch.owner_id == owner.id)
        .order_by(TSMatch.created_at.desc())
    )
    return [ResponseMatch.model_validate(m) for m in result.scalars().all()]


@router.post(
    "/matches", response_model=ResponseMatch, status_code=status.HTTP_201_CREATED
)
async def create_match(
    payload: MatchWrite,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseMatch:
    await _validate_match_refs(
        session, current_user.id, payload.personal_deck_id, payload.opponent_deck_id
    )
    match = TSMatch(owner_id=current_user.id)
    _apply_payload(match, payload)
    session.add(match)
    await session.commit()
    await session.refresh(match)
    return ResponseMatch.model_validate(match)


@router.put("/matches/{match_id}", response_model=ResponseMatch)
async def update_match(
    match_id: uuid.UUID,
    payload: MatchWrite,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseMatch:
    match = await _get_owned_match(session, match_id, current_user.id)
    await _validate_match_refs(
        session, current_user.id, payload.personal_deck_id, payload.opponent_deck_id
    )
    _apply_payload(match, payload)
    session.add(match)
    await session.commit()
    await session.refresh(match)
    return ResponseMatch.model_validate(match)


@router.delete("/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match(
    match_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    match = await _get_owned_match(session, match_id, current_user.id)
    await session.delete(match)
    await session.commit()
