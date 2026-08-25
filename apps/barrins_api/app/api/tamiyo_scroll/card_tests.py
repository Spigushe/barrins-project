"""Routes /card-tests (card logs, CRUD) and their evaluations (S17)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.mtgjson import Card
from app.models.tamiyo_scroll import (
    TSCardTest,
    TSCardTestEvaluation,
    TSMetaDeck,
    TSPersonalDeck,
    TSPersonalDecklistVersion,
    TSUserSettings,
)
from app.schemas.responses_tamiyo_scroll import (
    ResponseCardTest,
    ResponseCardTestEvaluation,
)
from app.schemas.tamiyo_scroll import CardTestEvaluationWrite, CardTestWrite
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


async def _get_owned_evaluation(
    session: DatabaseSession, test: TSCardTest, evaluation_id: uuid.UUID
) -> TSCardTestEvaluation:
    """`test` must already be ownership-checked via `_get_owned_card_test`."""
    result = await session.execute(
        select(TSCardTestEvaluation).where(
            TSCardTestEvaluation.id == evaluation_id,
            TSCardTestEvaluation.test_id == test.id,
        )
    )
    evaluation = result.scalar_one_or_none()
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found."
        )
    return evaluation


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
    test.notes = payload.notes


def _apply_evaluation_payload(
    evaluation: TSCardTestEvaluation, payload: CardTestEvaluationWrite
) -> None:
    evaluation.opponent_deck_id = payload.opponent_deck_id
    evaluation.rating = payload.rating
    evaluation.notes = payload.notes


async def _evaluations_by_test_id(
    session: DatabaseSession, test_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[TSCardTestEvaluation]]:
    """Batched fetch, grouped by parent log — avoids one query per card
    log when building a `ResponseCardTest` list (`evaluations` is
    embedded rather than requiring a separate per-log GET, matching this
    BFF's "aggregate to reduce frontend complexity" convention). Archived
    evaluations (Constitution §11.8) are excluded, same as archived logs."""
    result = await session.execute(
        select(TSCardTestEvaluation).where(
            TSCardTestEvaluation.test_id.in_(test_ids),
            TSCardTestEvaluation.archived_at.is_(None),
        )
    )
    by_test_id: dict[uuid.UUID, list[TSCardTestEvaluation]] = {}
    for evaluation in result.scalars().all():
        by_test_id.setdefault(evaluation.test_id, []).append(evaluation)
    return by_test_id


async def _scryfall_ids_by_name(
    session: DatabaseSession, names: Sequence[str]
) -> dict[str, str | None]:
    """One resolver pass + one batched `mj_cards` query, name -> scryfall id
    -- mirrors `decklist_view._resolved_by_name`, narrowed to just the id
    the card log's own hover preview needs (S17 item 3 follow-up: the
    "Tested cards" block's Removed/Added Card cells hover the same way
    a pending decklist line's names do)."""
    canonical_by_name: dict[str, str] = {}
    for name in names:
        canonical = await resolve_card_name(session, name)
        if canonical is not None:
            canonical_by_name[name] = canonical

    canonical_names = set(canonical_by_name.values())
    if not canonical_names:
        return dict.fromkeys(names)

    matches = await session.execute(
        select(Card.name, Card.face_name, Card.scryfall_id).where(
            or_(
                Card.name.in_(canonical_names),
                Card.face_name.in_(canonical_names),
            )
        )
    )
    scryfall_by_card_name: dict[str, str | None] = {}
    for name, face_name, scryfall_id in matches.all():
        scryfall_by_card_name.setdefault(name, scryfall_id)
        if face_name:
            scryfall_by_card_name.setdefault(face_name, scryfall_id)

    return {
        name: scryfall_by_card_name.get(canonical_by_name.get(name, ""))
        for name in names
    }


def _card_test_names(tests: Sequence[TSCardTest]) -> list[str]:
    return [name for t in tests for name in (t.removed_card_name, t.added_card_name)]


def _response_card_test(
    test: TSCardTest,
    evaluations: list[TSCardTestEvaluation],
    scryfall_by_name: dict[str, str | None],
) -> ResponseCardTest:
    """`evaluations` has no ORM relationship to validate `from_attributes`
    against (every `TS*` model in this file is FK-only), so the response
    is built explicitly rather than via `model_validate(test)`."""
    return ResponseCardTest(
        id=test.id,
        personal_deck_id=test.personal_deck_id,
        removed_card_name=test.removed_card_name,
        added_card_name=test.added_card_name,
        removed_card_scryfall_id=scryfall_by_name.get(test.removed_card_name),
        added_card_scryfall_id=scryfall_by_name.get(test.added_card_name),
        notes=test.notes,
        created_at=test.created_at,
        evaluations=[ResponseCardTestEvaluation.model_validate(e) for e in evaluations],
    )


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
    session: DatabaseSession,
    owner_id: uuid.UUID,
    payload: CardTestWrite,
    *,
    check_removed_in_decklist: bool,
) -> None:
    """When no `TSUserSettings` row exists yet (the owner has never hit
    GET/PATCH /me/settings), fall back to the column defaults rather than
    treating "no row" as "everything off" -- `validate_removed_card_in_decklist`
    defaults on, so a brand-new account must still get it enforced.

    `check_removed_in_decklist` is `False` on update: the removed-card
    check only makes sense against the deck's *current* decklist, so it's
    a create-time guard -- re-running it on every edit would reject
    saving a plain notes change on an already-saved log once the
    decklist has since moved past that card. `validate_added_card_exists`
    doesn't have this problem (`mj_cards` doesn't shift under a deck) so
    it still runs on both create and update."""
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
    if validate_removed and check_removed_in_decklist:
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
    and stay invisible, cf. migration a3f8c1d9e2b7. Archived logs
    (Constitution §11.8) are excluded — no `include_archived` toggle yet.
    """
    stmt = select(TSCardTest).where(
        TSCardTest.owner_id == owner.id, TSCardTest.archived_at.is_(None)
    )
    if personal_deck_id is not None:
        stmt = stmt.where(TSCardTest.personal_deck_id == personal_deck_id)
    stmt = stmt.order_by(TSCardTest.created_at.desc())
    result = await session.execute(stmt)
    tests = list(result.scalars().all())
    evaluations_by_test = await _evaluations_by_test_id(session, [t.id for t in tests])
    scryfall_by_name = await _scryfall_ids_by_name(session, _card_test_names(tests))
    return [
        _response_card_test(t, evaluations_by_test.get(t.id, []), scryfall_by_name)
        for t in tests
    ]


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
            TSCardTest.archived_at.is_(None),
        )
        .order_by(TSCardTest.created_at.desc())
    )
    result = await session.execute(stmt)
    tests = [t for t in result.scalars().all() if t.id not in matched_ids]
    evaluations_by_test = await _evaluations_by_test_id(session, [t.id for t in tests])
    scryfall_by_name = await _scryfall_ids_by_name(session, _card_test_names(tests))
    return [
        _response_card_test(t, evaluations_by_test.get(t.id, []), scryfall_by_name)
        for t in tests
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
    await _run_write_validations(
        session, current_user.id, payload, check_removed_in_decklist=True
    )
    test = TSCardTest(owner_id=current_user.id)
    _apply_payload(test, payload)
    session.add(test)
    await session.commit()
    await session.refresh(test)
    scryfall_by_name = await _scryfall_ids_by_name(session, _card_test_names([test]))
    return _response_card_test(
        test, [], scryfall_by_name
    )  # a new log starts with no evaluations


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
    await _run_write_validations(
        session, current_user.id, payload, check_removed_in_decklist=False
    )
    _apply_payload(test, payload)
    session.add(test)
    await session.commit()
    await session.refresh(test)
    evaluations_by_test = await _evaluations_by_test_id(session, [test.id])
    scryfall_by_name = await _scryfall_ids_by_name(session, _card_test_names([test]))
    return _response_card_test(
        test, evaluations_by_test.get(test.id, []), scryfall_by_name
    )


@router.delete("/card-tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card_test(
    test_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Archive the log (`archived_at`) — never a SQL DELETE, Constitution
    §11.8. Its evaluations stay in the database too (only hidden from
    reads by `_evaluations_by_test_id`'s own filter), not cascade-deleted."""
    test = await _get_owned_card_test(session, test_id, current_user.id)
    test.archived_at = datetime.now(UTC)
    session.add(test)
    await session.commit()


@router.post(
    "/card-tests/{test_id}/evaluations",
    response_model=ResponseCardTestEvaluation,
    status_code=status.HTTP_201_CREATED,
)
async def create_card_test_evaluation(
    test_id: uuid.UUID,
    payload: CardTestEvaluationWrite,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseCardTestEvaluation:
    test = await _get_owned_card_test(session, test_id, current_user.id)
    await _validate_opponent_ref(session, current_user.id, payload.opponent_deck_id)
    evaluation = TSCardTestEvaluation(test_id=test.id)
    _apply_evaluation_payload(evaluation, payload)
    session.add(evaluation)
    await session.commit()
    await session.refresh(evaluation)
    return ResponseCardTestEvaluation.model_validate(evaluation)


@router.put(
    "/card-tests/{test_id}/evaluations/{evaluation_id}",
    response_model=ResponseCardTestEvaluation,
)
async def update_card_test_evaluation(
    test_id: uuid.UUID,
    evaluation_id: uuid.UUID,
    payload: CardTestEvaluationWrite,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseCardTestEvaluation:
    test = await _get_owned_card_test(session, test_id, current_user.id)
    evaluation = await _get_owned_evaluation(session, test, evaluation_id)
    await _validate_opponent_ref(session, current_user.id, payload.opponent_deck_id)
    _apply_evaluation_payload(evaluation, payload)
    session.add(evaluation)
    await session.commit()
    await session.refresh(evaluation)
    return ResponseCardTestEvaluation.model_validate(evaluation)


@router.delete(
    "/card-tests/{test_id}/evaluations/{evaluation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_card_test_evaluation(
    test_id: uuid.UUID,
    evaluation_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Archive the evaluation — never a SQL DELETE, Constitution §11.8."""
    test = await _get_owned_card_test(session, test_id, current_user.id)
    evaluation = await _get_owned_evaluation(session, test, evaluation_id)
    evaluation.archived_at = datetime.now(UTC)
    session.add(evaluation)
    await session.commit()
