"""Routes /personal-decks, .../versions*, .../decklist-view, .../report.pdf."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select, update

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models._types import JsonValue
from app.models.tamiyo_scroll import (
    DecklistVersionSource,
    TSCardTest,
    TSMatch,
    TSMetaDeck,
    TSPersonalDeck,
    TSPersonalDecklistVersion,
)
from app.schemas.responses_tamiyo_scroll import (
    ResponseDecklistVersion,
    ResponseDecklistView,
    ResponsePersonalDeck,
)
from app.schemas.tamiyo_scroll import (
    DecklistVersionCreate,
    MoxfieldImportRequest,
    PersonalDeckCreate,
    PersonalDeckPatch,
)
from app.services.identity_directory import IdentityDirectoryDep
from app.services.moxfield import MoxfieldClientDep
from app.services.tamiyo_scroll.decklist_coloring import color_decklist
from app.services.tamiyo_scroll.decklist_view import build_decklist_view
from app.services.tamiyo_scroll.ownership import ResolvedOwner
from app.services.tamiyo_scroll.report import (
    format_period,
    render_session_report_pdf,
    resolve_report_decklist_version,
)
from app.services.tamiyo_scroll.sharing_merge import build_merged_view
from app.services.tamiyo_scroll.stats import compute_period_stats
from app.services.tamiyo_scroll.teams import resolve_team_deck_access

REPORT_ROLLING_WINDOW = timedelta(days=30)

router = APIRouter()


async def _get_owned_personal_deck(
    session: DatabaseSession, deck_id: uuid.UUID, owner_id: uuid.UUID
) -> TSPersonalDeck:
    result = await session.execute(
        select(TSPersonalDeck).where(
            TSPersonalDeck.id == deck_id, TSPersonalDeck.owner_id == owner_id
        )
    )
    deck = result.scalar_one_or_none()
    if deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Personal deck not found."
        )
    return deck


async def _sync_opponent_deck_games(
    session: DatabaseSession, deck: TSPersonalDeck, owner_id: uuid.UUID
) -> None:
    """Cascades a corrected `game` onto every opponent (meta) deck this
    personal deck has been matched against — always overwrites, unlike
    the creation-time hint (`TSMetaDeck.game`'s docstring): once a
    personal deck's game is fixed via PATCH, the opponent decks logged
    against it should carry that same corrected value for ML export
    filtering, not a stale/mismatched one.
    """
    opponent_ids_result = await session.execute(
        select(TSMatch.opponent_deck_id)
        .where(TSMatch.personal_deck_id == deck.id, TSMatch.owner_id == owner_id)
        .distinct()
    )
    opponent_ids = opponent_ids_result.scalars().all()
    if not opponent_ids:
        return
    await session.execute(
        update(TSMetaDeck).where(TSMetaDeck.id.in_(opponent_ids)).values(game=deck.game)
    )


def _moxfield_last_updated_at(raw_data: JsonValue | None) -> datetime | None:
    """Root-level `lastUpdatedAtUtc` only — never a recursive search.

    The same key also appears nested ~100+ times inside each card's
    `prices` object (an unrelated per-card price-refresh time); reading it
    off the root dict specifically is what avoids that trap (see
    http_client.py's module docstring).
    """
    if not isinstance(raw_data, dict):
        return None
    value = raw_data.get("lastUpdatedAtUtc")
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def _create_version(
    session: DatabaseSession,
    deck: TSPersonalDeck,
    content: str,
    source: DecklistVersionSource,
    moxfield_data: JsonValue | None = None,
) -> TSPersonalDecklistVersion:
    # Locks the parent deck's row to prevent a race on the version number
    # between two concurrent requests (cf. plan, Points of vigilance).
    await session.execute(
        select(TSPersonalDeck).where(TSPersonalDeck.id == deck.id).with_for_update()
    )
    max_version_result = await session.execute(
        select(func.max(TSPersonalDecklistVersion.version)).where(
            TSPersonalDecklistVersion.personal_deck_id == deck.id
        )
    )
    next_version = (max_version_result.scalar_one_or_none() or 0) + 1

    version = TSPersonalDecklistVersion(
        personal_deck_id=deck.id,
        version=next_version,
        content=content,
        source=source,
        moxfield_data=moxfield_data,
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


@router.get("/personal-decks", response_model=list[ResponsePersonalDeck])
async def list_personal_decks(
    session: DatabaseSession,
    owner: ResolvedOwner,
    include_archived: bool = False,
) -> list[ResponsePersonalDeck]:
    stmt = select(TSPersonalDeck).where(TSPersonalDeck.owner_id == owner.id)
    if not include_archived:
        stmt = stmt.where(TSPersonalDeck.archived_at.is_(None))
    stmt = stmt.order_by(TSPersonalDeck.created_at)
    result = await session.execute(stmt)
    return [ResponsePersonalDeck.model_validate(d) for d in result.scalars().all()]


@router.post(
    "/personal-decks",
    response_model=ResponsePersonalDeck,
    status_code=status.HTTP_201_CREATED,
)
async def create_personal_deck(
    payload: PersonalDeckCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponsePersonalDeck:
    deck = TSPersonalDeck(
        owner_id=current_user.id,
        name=payload.name,
        game=payload.game,
        category=payload.category,
    )
    session.add(deck)
    await session.commit()
    await session.refresh(deck)
    return ResponsePersonalDeck.model_validate(deck)


@router.delete("/personal-decks/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_personal_deck(
    deck_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Archive the deck (`archived_at`) — never a SQL DELETE, cf. plan Option G."""
    deck = await _get_owned_personal_deck(session, deck_id, current_user.id)
    deck.archived_at = datetime.now(UTC)
    session.add(deck)
    await session.commit()


@router.patch("/personal-decks/{deck_id}", response_model=ResponsePersonalDeck)
async def patch_personal_deck(
    deck_id: uuid.UUID,
    payload: PersonalDeckPatch,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponsePersonalDeck:
    """Partial update — rename (S1), and/or set/correct game/category
    (S10/S11) — owner-only. Only the fields present in the payload change.

    Team-deck sharing is name-based (S2) — renaming a deck away from a
    flagged name drops it out of that team's rotation for this member
    (still shown if other members' decks keep the old name), and renaming
    it *to* an already-flagged name picks it up automatically. No extra
    bookkeeping needed here: `list_team_deck_groups` matches by name at
    read time, not by a stored link on this row.

    Setting/correcting `game` also cascades onto every opponent (meta)
    deck this deck has been matched against (`_sync_opponent_deck_games`)
    — unlike the creation-time inheritance hint, this always overwrites.
    """
    deck = await _get_owned_personal_deck(session, deck_id, current_user.id)
    if payload.name is not None:
        deck.name = payload.name
    if payload.game is not None:
        deck.game = payload.game
        await _sync_opponent_deck_games(session, deck, current_user.id)
    if payload.category is not None:
        deck.category = payload.category
    session.add(deck)
    await session.commit()
    await session.refresh(deck)
    return ResponsePersonalDeck.model_validate(deck)


@router.get(
    "/personal-decks/{deck_id}/versions", response_model=list[ResponseDecklistVersion]
)
async def list_decklist_versions(
    deck_id: uuid.UUID,
    session: DatabaseSession,
    owner: ResolvedOwner,
) -> list[ResponseDecklistVersion]:
    deck = await _get_owned_personal_deck(session, deck_id, owner.id)
    result = await session.execute(
        select(TSPersonalDecklistVersion)
        .where(TSPersonalDecklistVersion.personal_deck_id == deck.id)
        .order_by(TSPersonalDecklistVersion.version.desc())
    )
    return [ResponseDecklistVersion.model_validate(v) for v in result.scalars().all()]


@router.post(
    "/personal-decks/{deck_id}/versions",
    response_model=ResponseDecklistVersion,
    status_code=status.HTTP_201_CREATED,
)
async def create_decklist_version(
    deck_id: uuid.UUID,
    payload: DecklistVersionCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseDecklistVersion:
    deck = await _get_owned_personal_deck(session, deck_id, current_user.id)
    version = await _create_version(
        session, deck, payload.content, DecklistVersionSource.manual
    )
    return ResponseDecklistVersion.model_validate(version)


@router.post(
    "/personal-decks/{deck_id}/versions/import-moxfield",
    response_model=ResponseDecklistVersion,
    status_code=status.HTTP_201_CREATED,
)
async def import_moxfield(
    deck_id: uuid.UUID,
    payload: MoxfieldImportRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
    moxfield: MoxfieldClientDep,
) -> ResponseDecklistVersion:
    """Create a new decklist version from a public Moxfield deck URL.

    Also opportunistically checks staleness (S3): compares this fetch's
    `lastUpdatedAtUtc` against the deck's prior Moxfield-sourced version
    (if any) — no dedicated Moxfield call is made just for this, per the
    2026-07-27 constraint (see S3 doc).
    """
    deck = await _get_owned_personal_deck(session, deck_id, current_user.id)
    fetch = await moxfield.fetch_decklist(payload.moxfield_url)

    prior_result = await session.execute(
        select(TSPersonalDecklistVersion)
        .where(
            TSPersonalDecklistVersion.personal_deck_id == deck.id,
            TSPersonalDecklistVersion.source == DecklistVersionSource.moxfield_import,
        )
        .order_by(TSPersonalDecklistVersion.version.desc())
        .limit(1)
    )
    prior_version = prior_result.scalar_one_or_none()

    changed_since_last_import: bool | None = None
    if prior_version is not None:
        prior_last_updated = _moxfield_last_updated_at(prior_version.moxfield_data)
        new_last_updated = _moxfield_last_updated_at(fetch.raw_data)
        if prior_last_updated is not None and new_last_updated is not None:
            changed_since_last_import = new_last_updated != prior_last_updated

    version = await _create_version(
        session,
        deck,
        fetch.content,
        DecklistVersionSource.moxfield_import,
        moxfield_data=fetch.raw_data,
    )
    response = ResponseDecklistVersion.model_validate(version)
    return response.model_copy(
        update={"moxfield_deck_changed_since_last_import": changed_since_last_import}
    )


@router.delete(
    "/personal-decks/{deck_id}/versions/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_decklist_version(
    deck_id: uuid.UUID,
    version_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Actually deletes the version — it's not the deck that's targeted (Option G)."""
    deck = await _get_owned_personal_deck(session, deck_id, current_user.id)
    result = await session.execute(
        select(TSPersonalDecklistVersion).where(
            TSPersonalDecklistVersion.id == version_id,
            TSPersonalDecklistVersion.personal_deck_id == deck.id,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version not found."
        )
    await session.delete(version)
    await session.commit()


@router.get(
    "/personal-decks/{deck_id}/decklist-view", response_model=ResponseDecklistView
)
async def get_decklist_view(
    deck_id: uuid.UUID,
    session: DatabaseSession,
    owner: ResolvedOwner,
) -> ResponseDecklistView:
    deck = await _get_owned_personal_deck(session, deck_id, owner.id)
    latest_result = await session.execute(
        select(TSPersonalDecklistVersion)
        .where(TSPersonalDecklistVersion.personal_deck_id == deck.id)
        .order_by(TSPersonalDecklistVersion.version.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()
    if latest is None:
        return ResponseDecklistView(
            commander_cards=[], library_cards=[], unparsed_lines=[]
        )

    tests_result = await session.execute(
        select(TSCardTest).where(
            TSCardTest.owner_id == owner.id, TSCardTest.personal_deck_id == deck_id
        )
    )
    card_tests = tests_result.scalars().all()
    return await build_decklist_view(session, latest.content, card_tests)


@router.get("/personal-decks/{deck_id}/report.pdf")
async def get_deck_period_report(
    deck_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
) -> Response:
    """Server-rendered PDF report for a deck, no session required (S5).

    Fixed to a rolling last-30-days window for now — letting the caller
    choose the data/timeframe instead is a flagged follow-up, not built
    here (see S5 doc's "outside of a session" addition). Baseline =
    everything logged before that window, same shape as a session's
    report (`sessions.get_session_report`), just windowed by time instead
    of by explicit session membership.

    Access (S2): the deck's owner, or any member of the team it's shared
    into (`resolve_team_deck_access`). Either way the report always shows
    the deck **owner's** own data — a team member sees the same report the
    owner would see themselves, never their own unrelated stats.
    """
    deck = await resolve_team_deck_access(session, deck_id, current_user)
    period_end = datetime.now(UTC)
    period_start = period_end - REPORT_ROLLING_WINDOW

    # The deck owner's own matches/roster, plus any sharer data merged in
    # read-only (S1) when the owner opted into `receive_shared_data` —
    # same merge `/archetype-summary`/`/matchup-summary` already apply,
    # split here into period/baseline by timestamp since `build_merged_view`
    # itself has no time-window concept (a session's matches are scoped by
    # explicit membership instead — see `sessions.get_session_report`).
    view = await build_merged_view(
        session, directory, deck.owner_id, personal_deck_id=deck.id
    )
    period_matches = [m for m in view.matches if m.created_at >= period_start]
    baseline_matches = [m for m in view.matches if m.created_at < period_start]

    # `view.meta_decks` (archived decks included) is passed as-is —
    # `compute_period_stats` filters archived decks itself, and drops
    # matches against them entirely rather than leaving them orphaned.
    stats = compute_period_stats(
        view.meta_decks, period_matches, baseline_matches, view.readonly_meta_deck_ids
    )

    versions_result = await session.execute(
        select(TSPersonalDecklistVersion).where(
            TSPersonalDecklistVersion.personal_deck_id == deck.id
        )
    )
    versions = list(versions_result.scalars().all())
    version = resolve_report_decklist_version(versions, stats.current_matches)

    all_card_tests_result = await session.execute(
        select(TSCardTest).where(
            TSCardTest.owner_id == deck.owner_id,
            TSCardTest.personal_deck_id == deck.id,
        )
    )
    all_card_tests = list(all_card_tests_result.scalars().all())
    colored_lines = color_decklist(version.content, all_card_tests) if version else []
    version_label = (
        f"Version {version.version} ({version.source.value})"
        if version
        else "No version yet"
    )
    period_card_tests = [t for t in all_card_tests if t.created_at >= period_start]

    pdf_bytes = render_session_report_pdf(
        title=deck.name,
        subtitle=f"Last 30 days · {format_period(period_start, period_end)}",
        period_label="Last 30 days",
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
    )

    filename = f"deck-report-{deck.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
