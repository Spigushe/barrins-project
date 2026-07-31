"""Routes /sessions (tournament/training session grouping, CRUD + comparison)."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import TSMatch, TSMetaDeck, TSPersonalDeck, TSSession
from app.schemas.responses_tamiyo_scroll import (
    ResponseArchetypeSummary,
    ResponseDeckWinrate,
    ResponseMatchupRow,
    ResponseMatchupSummary,
    ResponseSession,
    ResponseSessionComparison,
)
from app.schemas.tamiyo_scroll import SessionCreate, SessionPatch
from app.services.tamiyo_scroll.sharing_merge import _from_match
from app.services.tamiyo_scroll.stats import (
    _tally_games,
    compute_archetype_summary,
    compute_matchup_summary,
)

router = APIRouter()


async def _get_owned_session(
    session: DatabaseSession, session_id: uuid.UUID, owner_id: uuid.UUID
) -> TSSession:
    result = await session.execute(
        select(TSSession).where(TSSession.id == session_id, TSSession.owner_id == owner_id)
    )
    ts_session = result.scalar_one_or_none()
    if ts_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )
    return ts_session


@router.get("/sessions", response_model=list[ResponseSession])
async def list_sessions(
    session: DatabaseSession,
    current_user: CurrentUser,
    personal_deck_id: uuid.UUID | None = None,
    include_archived: bool = False,
) -> list[ResponseSession]:
    stmt = select(TSSession).where(TSSession.owner_id == current_user.id)
    if personal_deck_id is not None:
        stmt = stmt.where(TSSession.personal_deck_id == personal_deck_id)
    if not include_archived:
        stmt = stmt.where(TSSession.archived_at.is_(None))
    stmt = stmt.order_by(TSSession.created_at.desc())
    result = await session.execute(stmt)
    return [ResponseSession.model_validate(s) for s in result.scalars().all()]


@router.post(
    "/sessions", response_model=ResponseSession, status_code=status.HTTP_201_CREATED
)
async def create_session(
    payload: SessionCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseSession:
    deck_result = await session.execute(
        select(TSPersonalDeck.id).where(
            TSPersonalDeck.id == payload.personal_deck_id,
            TSPersonalDeck.owner_id == current_user.id,
        )
    )
    if deck_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Personal deck not found."
        )

    ts_session = TSSession(
        owner_id=current_user.id,
        personal_deck_id=payload.personal_deck_id,
        name=payload.name,
        type=payload.type,
        notes=payload.notes,
    )
    session.add(ts_session)
    await session.commit()
    await session.refresh(ts_session)
    return ResponseSession.model_validate(ts_session)


@router.patch("/sessions/{session_id}", response_model=ResponseSession)
async def update_session(
    session_id: uuid.UUID,
    payload: SessionPatch,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseSession:
    ts_session = await _get_owned_session(session, session_id, current_user.id)

    if payload.name is not None:
        ts_session.name = payload.name
    if "notes" in payload.model_fields_set:
        ts_session.notes = payload.notes
    if payload.close:
        ts_session.ended_at = datetime.now(UTC)
    if payload.reopen:
        ts_session.ended_at = None

    session.add(ts_session)
    await session.commit()
    await session.refresh(ts_session)
    return ResponseSession.model_validate(ts_session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_session(
    session_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Archive the session (`archived_at`) — never a SQL DELETE.

    Matches logged into this session keep their `session_id` unchanged —
    nothing falls back to the ungrouped pool from this action alone.
    """
    ts_session = await _get_owned_session(session, session_id, current_user.id)
    ts_session.archived_at = datetime.now(UTC)
    session.add(ts_session)
    await session.commit()


@router.get("/sessions/{session_id}/comparison", response_model=ResponseSessionComparison)
async def get_session_comparison(
    session_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseSessionComparison:
    """Session's winrate/matchup summary vs. the deck's baseline.

    Baseline = everything logged for the same deck before this session
    started (`created_at < session.created_at`), regardless of whether
    those earlier matches belong to another session or are ungrouped —
    resolved open question 2 in the S9 doc. Reuses the existing
    `compute_archetype_summary`/`compute_matchup_summary` — no parallel
    calculation path.
    """
    ts_session = await _get_owned_session(session, session_id, current_user.id)

    meta_decks_result = await session.execute(
        select(TSMetaDeck).where(
            TSMetaDeck.owner_id == current_user.id, TSMetaDeck.archived_at.is_(None)
        )
    )
    meta_decks = list(meta_decks_result.scalars().all())
    meta_decks_by_id = {d.id: d for d in meta_decks}

    session_matches_result = await session.execute(
        select(TSMatch).where(TSMatch.session_id == ts_session.id)
    )
    session_matches = [
        _from_match(m, is_readonly=False, shared_by=None)
        for m in session_matches_result.scalars().all()
    ]

    baseline_matches_result = await session.execute(
        select(TSMatch).where(
            TSMatch.owner_id == current_user.id,
            TSMatch.personal_deck_id == ts_session.personal_deck_id,
            TSMatch.created_at < ts_session.created_at,
        )
    )
    baseline_matches = [
        _from_match(m, is_readonly=False, shared_by=None)
        for m in baseline_matches_result.scalars().all()
    ]

    session_archetype = compute_archetype_summary(meta_decks, session_matches)
    baseline_archetype = compute_archetype_summary(meta_decks, baseline_matches)
    session_matchup_rows, session_avg = compute_matchup_summary(
        session_matches, meta_decks_by_id
    )
    baseline_matchup_rows, baseline_avg = compute_matchup_summary(
        baseline_matches, meta_decks_by_id
    )
    session_wins, session_losses, _ = _tally_games(session_matches)
    baseline_wins, baseline_losses, _ = _tally_games(baseline_matches)

    return ResponseSessionComparison(
        session=ResponseSession.model_validate(ts_session),
        session_match_count=len(session_matches),
        baseline_match_count=len(baseline_matches),
        session_wins=session_wins,
        session_losses=session_losses,
        baseline_wins=baseline_wins,
        baseline_losses=baseline_losses,
        session_archetype_summary=[
            ResponseArchetypeSummary(
                category=s["category"],
                average_winrate=s["average_winrate"],
                decks=[ResponseDeckWinrate(**d) for d in s["decks"]],
            )
            for s in session_archetype
        ],
        baseline_archetype_summary=[
            ResponseArchetypeSummary(
                category=s["category"],
                average_winrate=s["average_winrate"],
                decks=[ResponseDeckWinrate(**d) for d in s["decks"]],
            )
            for s in baseline_archetype
        ],
        session_matchup_summary=ResponseMatchupSummary(
            rows=[ResponseMatchupRow(**row) for row in session_matchup_rows],
            average_winrate=session_avg,
        ),
        baseline_matchup_summary=ResponseMatchupSummary(
            rows=[ResponseMatchupRow(**row) for row in baseline_matchup_rows],
            average_winrate=baseline_avg,
        ),
    )
