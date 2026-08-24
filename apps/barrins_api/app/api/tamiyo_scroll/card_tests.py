"""Routes /card-tests (feedback on tested cards, CRUD)."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import (
    TSCardTest,
    TSMetaDeck,
    TSPersonalDeck,
    TSPersonalDecklistVersion,
    TSUserSettings,
)
from app.schemas.responses_tamiyo_scroll import ResponseCardTest
from app.schemas.tamiyo_scroll import CardTestWrite
from app.services.scripture.card_resolver import (
    resolve_card_name,
    resolve_card_name_or_raw,
)
from app.services.tamiyo_scroll.card_test_matching import compute_matched_card_test_ids
from app.services.tamiyo_scroll.decklist_coloring import parse_card_line
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
    test.removed_card_name = payload.removed_card_name
    test.added_card_name = payload.added_card_name
    test.opponent_deck_id = payload.opponent_deck_id
    test.rating = payload.rating
    test.notes = payload.notes


async def _validate_removed_card_in_decklist(
    session: DatabaseSession, personal_deck_id: uuid.UUID, removed_card_name: str
) -> None:
    """S16: `removed_card_name` must match a card present in the deck's
    *current* (latest) decklist content, canonicalized through
    `resolve_card_name_or_raw` on both sides."""
    latest_result = await session.execute(
        select(TSPersonalDecklistVersion)
        .where(TSPersonalDecklistVersion.personal_deck_id == personal_deck_id)
        .order_by(TSPersonalDecklistVersion.version.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()
    target = await resolve_card_name_or_raw(session, removed_card_name)
    if latest is not None:
        for line in latest.content.splitlines():
            parsed = parse_card_line(line)
            if parsed is None:
                continue
            _, name = parsed
            canonical = await resolve_card_name_or_raw(session, name)
            if canonical == target:
                return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Removed card is not present in the deck's current decklist.",
    )


async def _validate_added_card_exists(
    session: DatabaseSession, added_card_name: str
) -> None:
    """S16: `added_card_name` must resolve against `mj_cards` -- Magic:
    The Gathering only, so this is opt-in and should stay off for
    non-Magic decks (it would reject every card name)."""
    if await resolve_card_name(session, added_card_name) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Added card does not resolve to a known card.",
        )


async def _run_write_validations(
    session: DatabaseSession, owner_id: uuid.UUID, payload: CardTestWrite
) -> None:
    """When no `TSUserSettings` row exists yet (the owner has never hit
    GET/PATCH /me/settings), fall back to the column defaults rather than
    treating "no row" as "everything off" -- `validate_removed_card_in_decklist`
    defaults on, so a brand-new account must still get it enforced."""
    settings_result = await session.execute(
        select(TSUserSettings).where(TSUserSettings.user_id == owner_id)
    )
    settings = settings_result.scalar_one_or_none()
    validate_removed = (
        settings.validate_removed_card_in_decklist if settings is not None else True
    )
    validate_added = (
        settings.validate_added_card_exists if settings is not None else False
    )
    if validate_removed:
        await _validate_removed_card_in_decklist(
            session, payload.personal_deck_id, payload.removed_card_name
        )
    if validate_added:
        await _validate_added_card_exists(session, payload.added_card_name)


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


@router.get("/card-tests/change-log", response_model=list[ResponseCardTest])
async def list_card_test_change_log(
    session: DatabaseSession,
    owner: ResolvedOwner,
    personal_deck_id: uuid.UUID,
) -> list[ResponseCardTest]:
    """S16: `personal_deck_id`'s card-test entries that don't match any
    real decklist change anywhere in the deck's version history — the
    complement to the matched-card-test comments shown inline on
    `GET .../versions/{id}/diff`."""
    await _validate_personal_deck_ref(session, owner.id, personal_deck_id)
    matched_ids = await compute_matched_card_test_ids(session, personal_deck_id)
    stmt = (
        select(TSCardTest)
        .where(
            TSCardTest.owner_id == owner.id,
            TSCardTest.personal_deck_id == personal_deck_id,
        )
        .order_by(TSCardTest.created_at.desc())
    )
    result = await session.execute(stmt)
    return [
        ResponseCardTest.model_validate(t)
        for t in result.scalars().all()
        if t.id not in matched_ids
    ]


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
    await _run_write_validations(session, current_user.id, payload)
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
    await _run_write_validations(session, current_user.id, payload)
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
