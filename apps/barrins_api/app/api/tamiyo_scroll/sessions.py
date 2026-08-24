"""Routes /sessions (tournament/training session grouping, CRUD + comparison)."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import (
    TSCardTest,
    TSCardTestEvaluation,
    TSMatch,
    TSMetaDeck,
    TSPersonalDeck,
    TSPersonalDecklistVersion,
    TSSession,
)
from app.schemas.responses_tamiyo_scroll import (
    ResponseArchetypeSummary,
    ResponseDeckWinrate,
    ResponseMatchupRow,
    ResponseMatchupSummary,
    ResponseSession,
    ResponseSessionComparison,
)
from app.schemas.tamiyo_scroll import SessionCreate, SessionPatch
from app.services.tamiyo_scroll.decklist_coloring import color_decklist
from app.services.tamiyo_scroll.report import (
    format_period,
    render_session_report_pdf,
    resolve_report_decklist_version,
)
from app.services.tamiyo_scroll.sharing_merge import _from_match
from app.services.tamiyo_scroll.stats import PeriodStats, compute_period_stats

router = APIRouter()


async def _get_owned_session(
    session: DatabaseSession, session_id: uuid.UUID, owner_id: uuid.UUID
) -> TSSession:
    result = await session.execute(
        select(TSSession).where(
            TSSession.id == session_id, TSSession.owner_id == owner_id
        )
    )
    ts_session = result.scalar_one_or_none()
    if ts_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )
    return ts_session


_SORT_COLUMNS = {
    "name": TSSession.name,
    "type": TSSession.type,
    "started_at": TSSession.started_at,
    # NULL `closed_at` = ongoing — sorts by the same column the Status
    # badge reads, so "ascending" groups ongoing sessions per Postgres's
    # default NULLS LAST behavior.
    "status": TSSession.closed_at,
}


@router.get("/sessions", response_model=list[ResponseSession])
async def list_sessions(
    session: DatabaseSession,
    current_user: CurrentUser,
    personal_deck_id: uuid.UUID | None = None,
    include_archived: bool = False,
    limit: int | None = None,
    offset: int = 0,
    sort_by: Literal["name", "type", "started_at", "status"] | None = None,
    sort_dir: Literal["asc", "desc"] = "asc",
    search: str | None = None,
) -> list[ResponseSession]:
    """`limit`/`offset`/`sort_by`/`sort_dir`/`search` are all optional and
    additive (S14) — omitting them keeps the original behavior (every
    matching session, ordered `created_at DESC`), which the match-logging
    session picker and the Match journal's session lookup both still rely
    on.
    """
    stmt = select(TSSession).where(TSSession.owner_id == current_user.id)
    if personal_deck_id is not None:
        stmt = stmt.where(TSSession.personal_deck_id == personal_deck_id)
    if not include_archived:
        stmt = stmt.where(TSSession.archived_at.is_(None))
    if search:
        stmt = stmt.where(TSSession.name.ilike(f"%{search}%"))

    if sort_by is None:
        stmt = stmt.order_by(TSSession.created_at.desc())
    else:
        column = _SORT_COLUMNS[sort_by]
        stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())

    if limit is not None:
        stmt = stmt.limit(limit).offset(offset)
    elif offset:
        stmt = stmt.offset(offset)

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
        location=payload.location,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        hue=payload.hue,
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
    if "location" in payload.model_fields_set:
        ts_session.location = payload.location
    if "started_at" in payload.model_fields_set:
        ts_session.started_at = payload.started_at
    if "ended_at" in payload.model_fields_set:
        ts_session.ended_at = payload.ended_at
    if "hue" in payload.model_fields_set:
        ts_session.hue = payload.hue
    if payload.close:
        ts_session.closed_at = datetime.now(UTC)
    if payload.reopen:
        ts_session.closed_at = None
    if payload.restore:
        ts_session.archived_at = None

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


async def _compute_session_stats(
    session: DatabaseSession, ts_session: TSSession, owner_id: uuid.UUID
) -> PeriodStats:
    """Session's winrate/matchup summary vs. the deck's baseline.

    Baseline = everything logged for the same deck before this session
    started (`created_at < session.created_at`), regardless of whether
    those earlier matches belong to another session or are ungrouped —
    resolved open question 2 in the S9 doc. The session's own matches are
    those explicitly logged into it (`session_id`), never a time window —
    contrast with `personal_decks.get_deck_period_report`'s rolling
    window, which has no such explicit membership to query.
    """
    # Archived decks included — `compute_period_stats` filters them itself
    # (and drops matches against them entirely, rather than orphaning
    # those matches into an unresolvable "?" opponent row).
    meta_decks_result = await session.execute(
        select(TSMetaDeck).where(TSMetaDeck.owner_id == owner_id)
    )
    meta_decks = list(meta_decks_result.scalars().all())

    session_matches_result = await session.execute(
        select(TSMatch).where(TSMatch.session_id == ts_session.id)
    )
    session_matches = [
        _from_match(m, is_readonly=False, shared_by=None)
        for m in session_matches_result.scalars().all()
    ]

    baseline_matches_result = await session.execute(
        select(TSMatch).where(
            TSMatch.owner_id == owner_id,
            TSMatch.personal_deck_id == ts_session.personal_deck_id,
            TSMatch.created_at < ts_session.created_at,
        )
    )
    baseline_matches = [
        _from_match(m, is_readonly=False, shared_by=None)
        for m in baseline_matches_result.scalars().all()
    ]

    return compute_period_stats(meta_decks, session_matches, baseline_matches)


@router.get(
    "/sessions/{session_id}/comparison", response_model=ResponseSessionComparison
)
async def get_session_comparison(
    session_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseSessionComparison:
    ts_session = await _get_owned_session(session, session_id, current_user.id)
    stats = await _compute_session_stats(session, ts_session, current_user.id)

    return ResponseSessionComparison(
        session=ResponseSession.model_validate(ts_session),
        session_match_count=len(stats.current_matches),
        baseline_match_count=len(stats.baseline_matches),
        session_wins=stats.current_wins,
        session_losses=stats.current_losses,
        baseline_wins=stats.baseline_wins,
        baseline_losses=stats.baseline_losses,
        session_archetype_summary=[
            ResponseArchetypeSummary(
                category=s["category"],
                average_winrate=s["average_winrate"],
                decks=[ResponseDeckWinrate(**d) for d in s["decks"]],
            )
            for s in stats.current_archetype
        ],
        baseline_archetype_summary=[
            ResponseArchetypeSummary(
                category=s["category"],
                average_winrate=s["average_winrate"],
                decks=[ResponseDeckWinrate(**d) for d in s["decks"]],
            )
            for s in stats.baseline_archetype
        ],
        session_matchup_summary=ResponseMatchupSummary(
            rows=[ResponseMatchupRow(**row) for row in stats.current_matchup_rows],
            average_winrate=stats.current_avg,
        ),
        baseline_matchup_summary=ResponseMatchupSummary(
            rows=[ResponseMatchupRow(**row) for row in stats.baseline_matchup_rows],
            average_winrate=stats.baseline_avg,
        ),
    )


@router.get("/sessions/{session_id}/report.pdf")
async def get_session_report(
    session_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    """Server-rendered PDF report for one session (S5) — WeasyPrint (I8).

    No client-side composition: the frontend only triggers a download of
    this backend-rendered file (Constitution §4.1).
    """
    ts_session = await _get_owned_session(session, session_id, current_user.id)

    deck_result = await session.execute(
        select(TSPersonalDeck).where(TSPersonalDeck.id == ts_session.personal_deck_id)
    )
    personal_deck = deck_result.scalar_one()

    stats = await _compute_session_stats(session, ts_session, current_user.id)

    versions_result = await session.execute(
        select(TSPersonalDecklistVersion).where(
            TSPersonalDecklistVersion.personal_deck_id == ts_session.personal_deck_id
        )
    )
    versions = list(versions_result.scalars().all())
    version = resolve_report_decklist_version(versions, stats.current_matches)

    all_card_tests_result = await session.execute(
        select(TSCardTest).where(
            TSCardTest.owner_id == current_user.id,
            TSCardTest.personal_deck_id == ts_session.personal_deck_id,
            TSCardTest.archived_at.is_(None),
        )
    )
    all_card_tests = list(all_card_tests_result.scalars().all())
    all_evaluations_result = await session.execute(
        select(TSCardTestEvaluation).where(
            TSCardTestEvaluation.test_id.in_([t.id for t in all_card_tests]),
            TSCardTestEvaluation.archived_at.is_(None),
        )
    )
    all_evaluations = list(all_evaluations_result.scalars().all())
    colored_lines = (
        color_decklist(version.content, all_card_tests, all_evaluations)
        if version
        else []
    )
    version_label = (
        f"Version {version.version} ({version.source.value})"
        if version
        else "No version yet"
    )

    # Card feedback "for the same deck/period" (S5's Done statement): the
    # session's own time window, on the same deck — cf. S9's precedent of
    # deriving temporal scope from timestamps rather than a new column,
    # since `ts_card_tests` carries no `session_id` (S9, resolved open
    # question 1).
    period_card_tests = [
        t
        for t in all_card_tests
        if t.created_at >= ts_session.created_at
        and (ts_session.closed_at is None or t.created_at <= ts_session.closed_at)
    ]
    period_evaluations = [
        e
        for e in all_evaluations
        if e.created_at >= ts_session.created_at
        and (ts_session.closed_at is None or e.created_at <= ts_session.closed_at)
    ]

    subtitle = (
        f"{personal_deck.name} · {ts_session.type.value} · "
        f"{format_period(ts_session.created_at, ts_session.closed_at)}"
    )
    pdf_bytes = render_session_report_pdf(
        title=ts_session.name,
        subtitle=subtitle,
        period_label="Session",
        decklist_version_label=version_label,
        colored_lines=colored_lines,
        period_match_count=len(stats.current_matches),
        period_wins=stats.current_wins,
        period_losses=stats.current_losses,
        baseline_wins=stats.baseline_wins,
        baseline_losses=stats.baseline_losses,
        period_matchup_rows=stats.current_matchup_rows,
        baseline_matchup_rows=stats.baseline_matchup_rows,
        card_tests=period_card_tests,
        evaluations=period_evaluations,
    )

    filename = f"session-report-{ts_session.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
