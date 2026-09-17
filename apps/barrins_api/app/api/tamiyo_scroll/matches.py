"""Routes /matches (BO3 match log, CRUD)."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.roles import Role, role_level
from app.database.session import DatabaseSession
from app.dependencies.auth import AuthenticatedUser, CurrentUser
from app.models.tamiyo_scroll import (
    MatchEventKind,
    MatchEventSide,
    TSMatch,
    TSMatchGame,
    TSMatchGameEvent,
    TSMetaDeck,
    TSPersonalDeck,
    TSPersonalDecklistVersion,
    TSSession,
)
from app.schemas.responses_tamiyo_scroll import ResponseMatch
from app.schemas.tamiyo_scroll import MatchEventWrite, MatchWrite
from app.services.identity_directory import IdentityDirectoryDep
from app.services.tamiyo_scroll.sharing_merge import build_merged_view

router = APIRouter()

# D7: the mulligan/misplay event-list fields on a `games[]` entry require a
# `moderator`+ caller. Field-level, not a route-level dependency, because
# the same payload also carries the ordinary game-result/`on_play` fields
# every caller may already submit — a route dependency would reject the
# whole request for a sub-moderator caller instead of just these fields.
# Each tuple is (payload field name == TSMatchGame's derived-cache column
# name, event side, event kind) — see `TSMatchGame`'s docstring for why
# the same name is reused for both.
_GATED_EVENT_FIELDS: tuple[tuple[str, MatchEventSide, MatchEventKind], ...] = (
    ("player_mulligans", MatchEventSide.player, MatchEventKind.mulligan),
    ("opponent_mulligans", MatchEventSide.opponent, MatchEventKind.mulligan),
    ("player_misplays", MatchEventSide.player, MatchEventKind.misplay),
    ("opponent_misplays", MatchEventSide.opponent, MatchEventKind.misplay),
)


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
        select(TSPersonalDeck.game, TSPersonalDeck.category).where(
            TSPersonalDeck.id == personal_deck_id, TSPersonalDeck.owner_id == owner_id
        )
    )
    personal_row = personal_result.one_or_none()
    if personal_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Personal deck not found."
        )
    # S10/S11: a deck must have both set before any match can be logged or
    # edited on it — the gate that gives the "required at creation" rule
    # teeth against historical, pre-migration decks (nullable, no backfill).
    if personal_row.game is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="personal_deck_game_required",
        )
    if personal_row.category is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="personal_deck_macrotype_required",
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


async def _resolve_latest_version_id(
    session: DatabaseSession, personal_deck_id: uuid.UUID
) -> uuid.UUID | None:
    """The deck's current latest decklist version, or None if it has none yet."""
    result = await session.execute(
        select(TSPersonalDecklistVersion.id)
        .where(TSPersonalDecklistVersion.personal_deck_id == personal_deck_id)
        .order_by(TSPersonalDecklistVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _validate_decklist_version(
    session: DatabaseSession,
    personal_deck_id: uuid.UUID,
    decklist_version_id: uuid.UUID,
) -> None:
    result = await session.execute(
        select(TSPersonalDecklistVersion.id).where(
            TSPersonalDecklistVersion.id == decklist_version_id,
            TSPersonalDecklistVersion.personal_deck_id == personal_deck_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decklist version not found."
        )


async def _validate_session(
    session: DatabaseSession,
    owner_id: uuid.UUID,
    session_id: uuid.UUID,
    personal_deck_id: uuid.UUID,
) -> None:
    """Session must belong to the caller and to the same personal deck (S9)."""
    result = await session.execute(
        select(TSSession.id).where(
            TSSession.id == session_id,
            TSSession.owner_id == owner_id,
            TSSession.personal_deck_id == personal_deck_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )


def _payload_has_gated_fields(payload: MatchWrite) -> bool:
    """True if any game carries a non-empty mulligan/misplay event list."""
    return any(
        getattr(game, field_name)
        for game in payload.games
        for field_name, _side, _kind in _GATED_EVENT_FIELDS
    )


def _upsert_game_events(
    game: TSMatchGame,
    side: MatchEventSide,
    kind: MatchEventKind,
    payload_events: list[MatchEventWrite],
) -> None:
    """Upsert-by-position against this `(game, side, kind)`'s existing
    events, never delete-and-reinsert the whole group.

    Matches existing `sequence=i` to the new payload's index `i` (both
    1-based `sequence` vs. 0-based `enumerate`, offset by one): updates
    its `comment` in place if changed, inserts new rows for indices
    beyond the old count, deletes rows beyond the new count. A blind
    delete-and-reinsert would reset every event's `created_at` and
    randomize its `id` on every autosave for no reason — `TSMatchGameEvent`
    docstring.
    """
    existing = sorted(
        (e for e in game.events if e.side == side and e.kind == kind),
        key=lambda e: e.sequence,
    )
    for index, event_payload in enumerate(payload_events):
        if index < len(existing):
            existing[index].comment = event_payload.comment
        else:
            game.events.append(
                TSMatchGameEvent(
                    side=side,
                    kind=kind,
                    sequence=index + 1,
                    comment=event_payload.comment,
                )
            )
    for stale in existing[len(payload_events) :]:
        game.events.remove(stale)


def _apply_payload(
    match: TSMatch, payload: MatchWrite, current_user: AuthenticatedUser
) -> None:
    """Full replacement of the match's fields, including its per-game log.

    `games[]` (#123/#124) is a full replacement, same convention as the
    rest of this payload: a game number no longer present is removed, an
    included one is upserted. `TSMatch.on_play`/`game1`/`game2`/`game3`
    (Migration 1's flat columns, kept only for its rollback window) are
    deliberately never written here anymore — the per-game log is now the
    only write path (D1).

    Raises 403 for the whole request if a sub-`moderator` caller's payload
    sets a non-empty mulligan/misplay event list on any game (D7) —
    checked before any mutation, so a rejected request never partially
    applies. A sub-moderator caller's four gated fields are therefore
    always empty lists by the time we reach the loop below: their
    existing events (if any, from an earlier moderator edit) are left
    completely untouched, never cleared just because a sub-moderator
    happened to save an unrelated field on the same match — only the
    derived-cache counter is forced to `NULL` (`TSMatchGame`'s docstring),
    since "not confirmed by this caller's save" must stay distinguishable
    from "confirmed zero" for `stats.py`'s averaging.
    """
    is_moderator = role_level(current_user.role) >= Role.moderator.level
    if not is_moderator and _payload_has_gated_fields(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="moderator_role_required_for_mulligan_misplay_fields",
        )

    match.personal_deck_id = payload.personal_deck_id
    match.opponent_deck_id = payload.opponent_deck_id
    match.opening_hand = payload.opening_hand
    match.turning_point = payload.turning_point
    match.final_turn = payload.final_turn

    games_by_number = {game.game_number: game for game in match.games}
    payload_numbers = {g.game_number for g in payload.games}
    for number, game in list(games_by_number.items()):
        if number not in payload_numbers:
            match.games.remove(game)

    for game_payload in payload.games:
        game = games_by_number.get(game_payload.game_number)
        if game is None:
            game = TSMatchGame(game_number=game_payload.game_number)
            match.games.append(game)
        game.on_play = game_payload.on_play
        game.result = game_payload.result

        for field_name, side, kind in _GATED_EVENT_FIELDS:
            payload_events: list[MatchEventWrite] = getattr(game_payload, field_name)
            if is_moderator:
                _upsert_game_events(game, side, kind, payload_events)
                setattr(game, field_name, len(payload_events))
            else:
                setattr(game, field_name, None)


@router.get("/matches", response_model=list[ResponseMatch])
async def list_matches(
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
    personal_deck_id: uuid.UUID | None = None,
) -> list[ResponseMatch]:
    """Match log for the active personal deck — never other decks'.

    `personal_deck_id` filters on the deck being viewed; omitted, every
    match for the owner is returned. If `receive_shared_data` is on, any
    sharer's matches for a personal deck with the same name are merged in
    read-only (see `sharing_merge`) — no "view as" selector, sharing is
    automatic.
    """
    view = await build_merged_view(
        session, directory, current_user.id, personal_deck_id=personal_deck_id
    )
    matches = sorted(view.matches, key=lambda m: m.created_at, reverse=True)
    return [ResponseMatch.model_validate(m) for m in matches]


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
    if payload.session_id is not None:
        await _validate_session(
            session, current_user.id, payload.session_id, payload.personal_deck_id
        )
    match = TSMatch(owner_id=current_user.id)
    _apply_payload(match, payload, current_user)
    match.session_id = payload.session_id
    # Never the frontend guessing which version is "current" (S3) — the
    # deck's latest version at creation time is resolved server-side,
    # ignoring any decklist_version_id the client may have sent.
    match.decklist_version_id = await _resolve_latest_version_id(
        session, payload.personal_deck_id
    )
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
    if payload.decklist_version_id is not None:
        await _validate_decklist_version(
            session, payload.personal_deck_id, payload.decklist_version_id
        )
    if payload.session_id is not None:
        await _validate_session(
            session, current_user.id, payload.session_id, payload.personal_deck_id
        )
    _apply_payload(match, payload, current_user)
    match.decklist_version_id = payload.decklist_version_id
    match.session_id = payload.session_id
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
