"""Routes /meta-decks (opponent roster + expected metagame, CRUD)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import (
    MetagameRosterScope,
    TSMetaDeck,
    TSPersonalDeck,
    TSUserSettings,
)
from app.schemas.responses_tamiyo_scroll import ResponseMetaDeck
from app.schemas.tamiyo_scroll import MetaDeckWrite
from app.services.identity_directory import IdentityDirectoryDep
from app.services.tamiyo_scroll.sharing_merge import (
    EffectiveMetaDeck,
    build_merged_view,
    collapse_by_name_and_game,
    norm_name,
    scope_meta_decks,
)

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
    deck.updated_at = datetime.now(UTC)


@router.get("/meta-decks", response_model=list[ResponseMetaDeck])
async def list_meta_decks(
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
    include_archived: bool = False,
) -> list[ResponseMetaDeck]:
    """Roster scoped to the caller's active personal deck (F10).

    No active deck selected -> empty list, same "no deck selected -> no
    data" rule the reporting feature already follows (Constitution §15).
    Otherwise, per `TSUserSettings.metagame_roster_scope`:

    - `"personal_deck"`: only entries created against the exact active
      deck (plus any sharer's read-only match, see `sharing_merge`).
    - `"game"` (default): every entry whose `game` matches the active
      deck's `game`, same-name rows collapsed into one line.

    A sharer's roster entry is folded into the viewer's own matching-name
    entry (never listed twice) or added as a new read-only line when the
    viewer has no roster entry of that name.
    """
    settings_result = await session.execute(
        select(TSUserSettings).where(TSUserSettings.user_id == current_user.id)
    )
    user_settings = settings_result.scalar_one_or_none()
    active_deck_id = user_settings.active_personal_deck_id if user_settings else None
    if active_deck_id is None:
        return []
    scope = (
        user_settings.metagame_roster_scope
        if user_settings
        else MetagameRosterScope.game
    )

    if scope == MetagameRosterScope.personal_deck:
        view = await build_merged_view(
            session,
            directory,
            current_user.id,
            personal_deck_id=active_deck_id,
            filter_meta_decks_by_personal_deck=True,
        )
        decks: list[EffectiveMetaDeck] = view.meta_decks
    else:
        active_deck_result = await session.execute(
            select(TSPersonalDeck.game).where(TSPersonalDeck.id == active_deck_id)
        )
        active_game = active_deck_result.scalar_one_or_none()
        view = await build_merged_view(session, directory, current_user.id)
        decks = scope_meta_decks(
            view.meta_decks,
            scope=scope,
            active_game=active_game,
            personal_deck_id=active_deck_id,
        )

    if not include_archived:
        decks = [d for d in decks if d.archived_at is None]
        if scope != MetagameRosterScope.personal_deck:
            decks = collapse_by_name_and_game(decks)

    decks = sorted(decks, key=lambda d: d.name)
    return [ResponseMetaDeck.model_validate(d) for d in decks]


@router.post(
    "/meta-decks", response_model=ResponseMetaDeck, status_code=status.HTTP_201_CREATED
)
async def create_meta_deck(
    payload: MetaDeckWrite,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseMetaDeck:
    """`personal_deck_id` is a real, validated FK (F10) — the roster entry
    is created *for* that deck; its `game` is inherited from it."""
    personal_deck_result = await session.execute(
        select(TSPersonalDeck.game).where(
            TSPersonalDeck.id == payload.personal_deck_id,
            TSPersonalDeck.owner_id == current_user.id,
        )
    )
    personal_deck_game_row = personal_deck_result.one_or_none()
    if personal_deck_game_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Personal deck not found."
        )

    deck = TSMetaDeck(
        owner_id=current_user.id, personal_deck_id=payload.personal_deck_id
    )
    _apply_payload(deck, payload)
    deck.game = personal_deck_game_row[0]
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
    """Edits propagate to every other same-name/same-`game` row the caller
    owns (F10 item 5) — one atomic `UPDATE`, never sequential per-row
    writes, so no partially-propagated state is ever visible. Never
    touches a sharer's (`is_readonly`) rows: this endpoint is already
    owner-scoped via `_get_owned_meta_deck`.
    """
    deck = await _get_owned_meta_deck(session, deck_id, current_user.id)
    _apply_payload(deck, payload)
    session.add(deck)
    await session.flush()

    # Candidates first, matched by the same `norm_name` rule the rest of
    # this module uses (not a second trim/lowercase reimplementation in
    # SQL) — then one atomic UPDATE by id, not per-row writes.
    candidates_result = await session.execute(
        select(TSMetaDeck.id, TSMetaDeck.name).where(
            TSMetaDeck.owner_id == current_user.id,
            TSMetaDeck.game == deck.game,
            TSMetaDeck.archived_at.is_(None),
            TSMetaDeck.id != deck.id,
        )
    )
    deck_name_norm = norm_name(deck.name)
    propagate_ids = [
        row.id
        for row in candidates_result.all()
        if norm_name(row.name) == deck_name_norm
    ]
    if propagate_ids:
        await session.execute(
            update(TSMetaDeck)
            .where(TSMetaDeck.id.in_(propagate_ids))
            .values(tier=deck.tier, category=deck.category, updated_at=deck.updated_at)
        )

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
