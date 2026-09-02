"""Routes /archetype-summary, /matchup-summary — calculations derived from the log."""

import uuid

from fastapi import APIRouter

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.schemas.responses_tamiyo_scroll import (
    ResponseArchetypeSummary,
    ResponseDeckWinrate,
    ResponseMatchupRow,
    ResponseMatchupSummary,
)
from app.services.identity_directory import IdentityDirectoryDep
from app.services.tamiyo_scroll.sharing_merge import build_merged_view
from app.services.tamiyo_scroll.stats import (
    compute_archetype_summary,
    compute_matchup_summary,
)

router = APIRouter()


@router.get("/archetype-summary", response_model=list[ResponseArchetypeSummary])
async def get_archetype_summary(
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
    personal_deck_id: uuid.UUID | None = None,
) -> list[ResponseArchetypeSummary]:
    view = await build_merged_view(
        session, directory, current_user.id, personal_deck_id=personal_deck_id
    )
    meta_decks = [d for d in view.meta_decks if d.archived_at is None]

    summaries = compute_archetype_summary(
        meta_decks, view.matches, view.readonly_meta_deck_ids
    )
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
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
    personal_deck_id: uuid.UUID | None = None,
) -> ResponseMatchupSummary:
    view = await build_merged_view(
        session, directory, current_user.id, personal_deck_id=personal_deck_id
    )
    meta_decks_by_id = {d.id: d for d in view.meta_decks}

    rows, average_winrate = compute_matchup_summary(
        view.matches, meta_decks_by_id, view.readonly_meta_deck_ids
    )
    return ResponseMatchupSummary(
        rows=[ResponseMatchupRow(**row) for row in rows],
        average_winrate=average_winrate,
    )
