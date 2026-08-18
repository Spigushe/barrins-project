"""Routes /archetype-summary, /matchup-summary — calculations derived from the log."""

import uuid

from fastapi import APIRouter

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import MetagameRosterScope
from app.schemas.responses_tamiyo_scroll import (
    ResponseArchetypeSummary,
    ResponseDeckWinrate,
    ResponseMatchupRow,
    ResponseMatchupSummary,
)
from app.services.tamiyo_scroll.sharing_merge import (
    build_merged_view,
    collapse_meta_decks_and_remap_matches,
    resolve_metagame_roster_scope,
    scope_meta_decks,
)
from app.services.tamiyo_scroll.stats import (
    compute_archetype_summary,
    compute_matchup_summary,
)

router = APIRouter()


@router.get("/archetype-summary", response_model=list[ResponseArchetypeSummary])
async def get_archetype_summary(
    session: DatabaseSession,
    current_user: CurrentUser,
    personal_deck_id: uuid.UUID | None = None,
) -> list[ResponseArchetypeSummary]:
    """`compute_archetype_summary` lists every roster deck per category
    "even empty ones, for a stable display grid" (see its own docstring) —
    unlike `matchup-summary` below (driven purely by already-scoped
    `matches`), that means `meta_decks` itself needs the same F10 game/
    personal_deck scoping `list_meta_decks` applies, or every other
    game's roster leaks through as empty-winrate rows whenever a deck is
    given (§F10 UAT: "Breakdown by archetype" not resetting across games).
    """
    view = await build_merged_view(
        session, current_user, personal_deck_id=personal_deck_id
    )
    meta_decks = [d for d in view.meta_decks if d.archived_at is None]
    matches = view.matches
    if personal_deck_id is not None:
        scope, active_game = await resolve_metagame_roster_scope(
            session, current_user, personal_deck_id
        )
        meta_decks = scope_meta_decks(
            meta_decks,
            scope=scope,
            active_game=active_game,
            personal_deck_id=personal_deck_id,
        )
        if scope != MetagameRosterScope.personal_deck:
            # F10 UAT: the migration's duplicate-and-allocate backfill can
            # leave two rows for one opponent — merge them here too, not
            # just for display, or the winrate split across them silently
            # drops whichever duplicate isn't picked as canonical.
            meta_decks, matches = collapse_meta_decks_and_remap_matches(
                meta_decks, matches
            )

    summaries = compute_archetype_summary(
        meta_decks, matches, view.readonly_meta_deck_ids
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
    personal_deck_id: uuid.UUID | None = None,
) -> ResponseMatchupSummary:
    view = await build_merged_view(
        session, current_user, personal_deck_id=personal_deck_id
    )
    meta_decks = view.meta_decks
    matches = view.matches
    if personal_deck_id is not None:
        scope, _active_game = await resolve_metagame_roster_scope(
            session, current_user, personal_deck_id
        )
        if scope != MetagameRosterScope.personal_deck:
            # Same duplicate-merge as archetype-summary above — two rows
            # for one opponent would otherwise show as two separate
            # matchup rows instead of one combined line.
            meta_decks, matches = collapse_meta_decks_and_remap_matches(
                meta_decks, matches
            )
    meta_decks_by_id = {d.id: d for d in meta_decks}

    rows, average_winrate = compute_matchup_summary(
        matches, meta_decks_by_id, view.readonly_meta_deck_ids
    )
    return ResponseMatchupSummary(
        rows=[ResponseMatchupRow(**row) for row in rows],
        average_winrate=average_winrate,
    )
