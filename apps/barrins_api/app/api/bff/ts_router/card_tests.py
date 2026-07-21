"""Routes /card-tests (feedback on tested cards, CRUD)."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import TSCardTest, TSMetaDeck, TSPersonalDeck
from app.schemas.responses_tamiyo_scroll import ResponseCardTest
from app.schemas.tamiyo_scroll import CardTestWrite
from app.services.tamiyo_scroll.ownership import ResolvedOwner

router = APIRouter()


async def _get_owned_card_test(
    session: DatabaseSession, test_id: uuid.UUID, owner_id: uuid.UUID
) -> TSCardTest:
    result = await session.execute(
        select(TSCardTest).where(
            TSCardTest.id == test_id, TSCardTest.owner_id == owner_id
        )
    )
    test = result.scalar_one_or_none()
    if test is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Card feedback not found."
        )
    return test


async def _validate_opponent_ref(
    session: DatabaseSession, owner_id: uuid.UUID, opponent_deck_id: uuid.UUID | None
) -> None:
    if opponent_deck_id is None:
        return
    result = await session.execute(
        select(TSMetaDeck.id).where(
            TSMetaDeck.id == opponent_deck_id, TSMetaDeck.owner_id == owner_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Opponent deck not found."
        )


async def _validate_personal_deck_ref(
    session: DatabaseSession, owner_id: uuid.UUID, personal_deck_id: uuid.UUID
) -> None:
    result = await session.execute(
        select(TSPersonalDeck.id).where(
            TSPersonalDeck.id == personal_deck_id, TSPersonalDeck.owner_id == owner_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Personal deck not found."
        )


def _apply_payload(test: TSCardTest, payload: CardTestWrite) -> None:
    test.personal_deck_id = payload.personal_deck_id
    test.tester = payload.tester
    test.card_name = payload.card_name
    test.opponent_deck_id = payload.opponent_deck_id
    test.rating = payload.rating
    test.notes = payload.notes


@router.get("/card-tests", response_model=list[ResponseCardTest])
async def list_card_tests(
    session: DatabaseSession,
    owner: ResolvedOwner,
    personal_deck_id: uuid.UUID | None = None,
) -> list[ResponseCardTest]:
    """Test feedback for the active personal deck — never other decks'.

    `personal_deck_id` filters on the deck being viewed; rows created before
    this column was added (personal_deck_id NULL) don't match any filter
    and stay invisible, cf. migration a3f8c1d9e2b7.
    """
    stmt = select(TSCardTest).where(TSCardTest.owner_id == owner.id)
    if personal_deck_id is not None:
        stmt = stmt.where(TSCardTest.personal_deck_id == personal_deck_id)
    stmt = stmt.order_by(TSCardTest.created_at.desc())
    result = await session.execute(stmt)
    return [ResponseCardTest.model_validate(t) for t in result.scalars().all()]


@router.post(
    "/card-tests", response_model=ResponseCardTest, status_code=status.HTTP_201_CREATED
)
async def create_card_test(
    payload: CardTestWrite,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseCardTest:
    await _validate_personal_deck_ref(
        session, current_user.id, payload.personal_deck_id
    )
    await _validate_opponent_ref(session, current_user.id, payload.opponent_deck_id)
    test = TSCardTest(owner_id=current_user.id)
    _apply_payload(test, payload)
    session.add(test)
    await session.commit()
    await session.refresh(test)
    return ResponseCardTest.model_validate(test)


@router.put("/card-tests/{test_id}", response_model=ResponseCardTest)
async def update_card_test(
    test_id: uuid.UUID,
    payload: CardTestWrite,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseCardTest:
    test = await _get_owned_card_test(session, test_id, current_user.id)
    await _validate_personal_deck_ref(
        session, current_user.id, payload.personal_deck_id
    )
    await _validate_opponent_ref(session, current_user.id, payload.opponent_deck_id)
    _apply_payload(test, payload)
    session.add(test)
    await session.commit()
    await session.refresh(test)
    return ResponseCardTest.model_validate(test)


@router.delete("/card-tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card_test(
    test_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    test = await _get_owned_card_test(session, test_id, current_user.id)
    await session.delete(test)
    await session.commit()
