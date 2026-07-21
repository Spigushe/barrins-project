"""Routes /archetype-summary, /matchup-summary — calculations derived from the log."""

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.database.session import DatabaseSession
from app.models.tamiyo_scroll import TSMatch, TSMetaDeck
from app.schemas.responses_tamiyo_scroll import (
    ResponseArchetypeSummary,
    ResponseDeckWinrate,
    ResponseMatchupRow,
    ResponseMatchupSummary,
)
from app.services.tamiyo_scroll.ownership import ResolvedOwner
from app.services.tamiyo_scroll.stats import (
    compute_archetype_summary,
    compute_matchup_summary,
)

router = APIRouter()


@router.get("/archetype-summary", response_model=list[ResponseArchetypeSummary])
async def get_archetype_summary(
    session: DatabaseSession, owner: ResolvedOwner
) -> list[ResponseArchetypeSummary]:
    meta_decks_result = await session.execute(
        select(TSMetaDeck).where(
            TSMetaDeck.owner_id == owner.id, TSMetaDeck.archived_at.is_(None)
        )
    )
    meta_decks = meta_decks_result.scalars().all()

    matches_result = await session.execute(
        select(TSMatch).where(TSMatch.owner_id == owner.id)
    )
    matches = matches_result.scalars().all()

    summaries = compute_archetype_summary(meta_decks, matches)
    return [
        ResponseArchetypeSummary(
            category=summary["category"],
            average_winrate=summary["average_winrate"],
            decks=[ResponseDeckWinrate(**deck) for deck in summary["decks"]],
        )
        for summary in summaries
    ]


@router.get("/matchup-summary", response_model=ResponseMatchupSummary)
async def get_matchup_summary(
    session: DatabaseSession,
    owner: ResolvedOwner,
    personal_deck_id: uuid.UUID | None = None,
) -> ResponseMatchupSummary:
    stmt = select(TSMatch).where(TSMatch.owner_id == owner.id)
    if personal_deck_id is not None:
        stmt = stmt.where(TSMatch.personal_deck_id == personal_deck_id)
    matches_result = await session.execute(stmt)
    matches = matches_result.scalars().all()

    meta_decks_result = await session.execute(
        select(TSMetaDeck).where(TSMetaDeck.owner_id == owner.id)
    )
    meta_decks_by_id = {d.id: d for d in meta_decks_result.scalars().all()}

    rows, average_winrate = compute_matchup_summary(matches, meta_decks_by_id)
    return ResponseMatchupSummary(
        rows=[ResponseMatchupRow(**row) for row in rows],
        average_winrate=average_winrate,
    )
