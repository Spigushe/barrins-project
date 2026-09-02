"""Routes /teams (S2, "Team Decks") — creation, membership, name-based
deck flagging, threads."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import (
    TSCardTest,
    TSMatch,
    TSMetaDeck,
    TSPersonalDeck,
    TSPersonalDecklistVersion,
    TSTeam,
    TSTeamDeckFlag,
    TSTeamDeckMessage,
    TSTeamDeckThread,
    TSTeamMember,
)
from app.schemas.responses_tamiyo_scroll import (
    ResponseMemberDeck,
    ResponseTeam,
    ResponseTeamDeck,
    ResponseTeamDeckMessage,
    ResponseTeamDeckOwner,
    ResponseTeamMember,
    ResponseTeamSummary,
)
from app.schemas.tamiyo_scroll import (
    TeamCreate,
    TeamDeckFlagCreate,
    TeamDeckThreadMessageCreate,
    TeamDelete,
    TeamJoin,
    TeamPatch,
)
from app.services.identity_directory import (
    IdentityDirectory,
    IdentityDirectoryDep,
    UserRef,
)
from app.services.tamiyo_scroll.decklist_coloring import color_decklist
from app.services.tamiyo_scroll.report import (
    format_period,
    render_session_report_pdf,
    resolve_report_decklist_version,
)
from app.services.tamiyo_scroll.sharing_merge import _from_match
from app.services.tamiyo_scroll.stats import compute_period_stats
from app.services.tamiyo_scroll.teams import (
    check_and_record_invite_attempt,
    compute_member_activity,
    flag_deck_name,
    generate_invite_code,
    get_member_team,
    get_owned_team,
    get_team_deck_owners,
    list_team_deck_groups,
    normalize_deck_name,
    normalize_invite_code,
    unflag_deck_name,
)

REPORT_ROLLING_WINDOW = timedelta(days=30)

router = APIRouter()


_UNKNOWN_MEMBER_LABEL = "Unknown member"


def _ref_label(ref: UserRef | None) -> str:
    """Display label for a user id resolved via the identity directory —
    `display_name` if set, else the handle, else a generic fallback (the
    directory is disabled or identity was unreachable)."""
    return ref.label if ref is not None else _UNKNOWN_MEMBER_LABEL


def _team_deck_owners(
    decks: list[TSPersonalDeck], refs: dict[uuid.UUID, UserRef]
) -> list[ResponseTeamDeckOwner]:
    return sorted(
        (
            ResponseTeamDeckOwner(
                deck_id=deck.id, display=_ref_label(refs.get(deck.owner_id))
            )
            for deck in decks
        ),
        key=lambda o: o.display,
    )


async def _team_to_response(
    session: DatabaseSession, directory: IdentityDirectory, team: TSTeam
) -> ResponseTeam:
    members_result = await session.execute(
        select(TSTeamMember)
        .where(TSTeamMember.team_id == team.id)
        .order_by(TSTeamMember.joined_at)
    )
    team_members = list(members_result.scalars().all())
    refs = await directory.lookup(m.user_id for m in team_members)
    activity = await compute_member_activity(session, team.id)
    members: list[ResponseTeamMember] = []
    for member in team_members:
        ref = refs.get(member.user_id)
        members.append(
            ResponseTeamMember(
                user_id=member.user_id,
                username=ref.username if ref is not None else None,
                display_name=ref.display_name if ref is not None else None,
                is_owner=member.user_id == team.owner_id,
                joined_at=member.joined_at,
                activity_count=activity.total_for(member.user_id),
            )
        )
    return ResponseTeam(
        id=team.id,
        name=team.name,
        description=team.description,
        invite_code=team.invite_code,
        owner_id=team.owner_id,
        created_at=team.created_at,
        members=members,
    )


@router.post("/teams", response_model=ResponseTeam, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
) -> ResponseTeam:
    """Any authenticated user may create a team and becomes its owner +
    first member (S2 §1.6 — no admin gate for v2.0.0).

    `invite_code` collisions are astronomically unlikely (8 chars over a
    36-symbol alphabet) — on the rare `IntegrityError`, the whole request
    fails with 409 and the client simply retries the POST (idempotent from
    its point of view: no team was created), rather than retrying the code
    server-side against an already-rolled-back session.
    """
    team = TSTeam(
        name=payload.name,
        owner_id=current_user.id,
        invite_code=generate_invite_code(),
    )
    session.add(team)
    try:
        await session.flush()
    except IntegrityError as err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not allocate an invite code, please retry.",
        ) from err

    session.add(TSTeamMember(team_id=team.id, user_id=current_user.id))
    await session.commit()
    await session.refresh(team)
    return await _team_to_response(session, directory, team)


@router.post("/teams/join", response_model=ResponseTeam)
async def join_team(
    payload: TeamJoin,
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
) -> ResponseTeam:
    await check_and_record_invite_attempt(session, current_user.id)

    code = normalize_invite_code(payload.invite_code)
    result = await session.execute(select(TSTeam).where(TSTeam.invite_code == code))
    team = result.scalar_one_or_none()
    if team is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invite code."
        )

    existing = await session.execute(
        select(TSTeamMember).where(
            TSTeamMember.team_id == team.id, TSTeamMember.user_id == current_user.id
        )
    )
    if existing.scalar_one_or_none() is None:
        session.add(TSTeamMember(team_id=team.id, user_id=current_user.id))
        await session.commit()

    return await _team_to_response(session, directory, team)


@router.get("/teams/mine", response_model=list[ResponseTeamSummary])
async def list_my_teams(
    session: DatabaseSession,
    current_user: CurrentUser,
) -> list[ResponseTeamSummary]:
    result = await session.execute(
        select(TSTeam)
        .join(TSTeamMember, TSTeamMember.team_id == TSTeam.id)
        .where(TSTeamMember.user_id == current_user.id)
        .order_by(TSTeam.created_at)
    )
    teams = result.scalars().all()
    return [
        ResponseTeamSummary(
            id=team.id, name=team.name, is_owner=team.owner_id == current_user.id
        )
        for team in teams
    ]


@router.get("/teams/{team_id}", response_model=ResponseTeam)
async def get_team(
    team_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
) -> ResponseTeam:
    team = await get_member_team(session, team_id, current_user)
    return await _team_to_response(session, directory, team)


@router.patch("/teams/{team_id}", response_model=ResponseTeam)
async def update_team(
    team_id: uuid.UUID,
    payload: TeamPatch,
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
) -> ResponseTeam:
    team = await get_owned_team(session, team_id, current_user)
    if "description" in payload.model_fields_set:
        team.description = payload.description
    session.add(team)
    await session.commit()
    await session.refresh(team)
    return await _team_to_response(session, directory, team)


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: uuid.UUID,
    payload: TeamDelete,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Hard delete (unlike every other `ts_*` entity — see `TSTeam`'s
    docstring). Requires re-typing the exact invite code, the server-side
    half of the two-step confirmation (an in-page dialog is the client-side
    first step, enforced by the frontend only)."""
    team = await get_owned_team(session, team_id, current_user)
    if normalize_invite_code(payload.invite_code) != team.invite_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite code does not match.",
        )
    await session.delete(team)
    await session.commit()


@router.post("/teams/{team_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_team(
    team_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    team = await get_member_team(session, team_id, current_user)
    if team.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The owner can't leave — delete the team instead.",
        )
    result = await session.execute(
        select(TSTeamMember).where(
            TSTeamMember.team_id == team_id, TSTeamMember.user_id == current_user.id
        )
    )
    member = result.scalar_one()
    await session.delete(member)
    await session.commit()


@router.delete(
    "/teams/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    team = await get_owned_team(session, team_id, current_user)
    if user_id == team.owner_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The owner can't be removed — delete the team instead.",
        )
    result = await session.execute(
        select(TSTeamMember).where(
            TSTeamMember.team_id == team_id, TSTeamMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found."
        )
    await session.delete(member)
    await session.commit()


@router.get("/teams/{team_id}/decks", response_model=list[ResponseTeamDeck])
async def list_team_decks(
    team_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
) -> list[ResponseTeamDeck]:
    await get_member_team(session, team_id, current_user)
    groups = await list_team_deck_groups(session, team_id)
    refs = await directory.lookup(
        deck.owner_id for group in groups for deck in group.owner_decks
    )
    return [
        ResponseTeamDeck(
            name_key=group.name_key,
            deck_name=group.deck_name,
            owners=_team_deck_owners(group.owner_decks, refs),
            has_thread=group.has_thread,
        )
        for group in groups
    ]


@router.get("/teams/{team_id}/decks/{name_key}/report.pdf")
async def get_team_deck_report(
    team_id: uuid.UUID,
    name_key: str,
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
) -> Response:
    """Cumulative PDF report for a team-flagged deck name (S2, 2026-08-01).

    One report per deck *name* per team, not one per owner: combines
    matches and card tests from every current member owning a matching
    deck into a single rolling-30-days view — same shape as
    `personal_decks.get_deck_period_report`, just summed across
    contributors instead of scoped to one person.
    """
    await get_member_team(session, team_id, current_user)

    flag_result = await session.execute(
        select(TSTeamDeckFlag).where(
            TSTeamDeckFlag.team_id == team_id, TSTeamDeckFlag.name_key == name_key
        )
    )
    flag = flag_result.scalar_one_or_none()
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This name isn't flagged into the team.",
        )

    owner_decks = await get_team_deck_owners(session, team_id, name_key)
    if not owner_decks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current member owns a matching deck.",
        )
    deck_ids = [deck.id for deck in owner_decks]

    period_end = datetime.now(UTC)
    period_start = period_end - REPORT_ROLLING_WINDOW

    matches_result = await session.execute(
        select(TSMatch).where(TSMatch.personal_deck_id.in_(deck_ids))
    )
    all_matches = [
        _from_match(m, is_readonly=False, shared_by=None)
        for m in matches_result.scalars().all()
    ]
    period_matches = [m for m in all_matches if m.created_at >= period_start]
    baseline_matches = [m for m in all_matches if m.created_at < period_start]

    owner_ids = {deck.owner_id for deck in owner_decks}
    meta_decks_result = await session.execute(
        select(TSMetaDeck).where(TSMetaDeck.owner_id.in_(owner_ids))
    )
    meta_decks = list(meta_decks_result.scalars().all())

    stats = compute_period_stats(
        meta_decks, period_matches, baseline_matches, frozenset()
    )

    # Canonical decklist for display: the flagger's own matching deck if
    # they still have one, else whichever contributor's deck comes first —
    # arbitrary among ties, display-only (stats above are already summed
    # across every contributor, not just this one).
    canonical_deck = next(
        (deck for deck in owner_decks if deck.owner_id == flag.flagged_by),
        owner_decks[0],
    )
    versions_result = await session.execute(
        select(TSPersonalDecklistVersion).where(
            TSPersonalDecklistVersion.personal_deck_id == canonical_deck.id
        )
    )
    versions = list(versions_result.scalars().all())
    version = resolve_report_decklist_version(versions, stats.current_matches)

    all_card_tests_result = await session.execute(
        select(TSCardTest).where(TSCardTest.personal_deck_id.in_(deck_ids))
    )
    all_card_tests = list(all_card_tests_result.scalars().all())
    colored_lines = color_decklist(version.content, all_card_tests) if version else []
    version_label = (
        f"Version {version.version} ({version.source.value})"
        if version
        else "No version yet"
    )
    period_card_tests = [t for t in all_card_tests if t.created_at >= period_start]

    owner_refs = await directory.lookup({deck.owner_id for deck in owner_decks})
    contributor_names = ", ".join(
        sorted({_ref_label(owner_refs.get(deck.owner_id)) for deck in owner_decks})
    )
    pdf_bytes = render_session_report_pdf(
        title=flag.deck_name,
        subtitle=(
            f"Team cumulative · {contributor_names} · "
            f"{format_period(period_start, period_end)}"
        ),
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

    filename = f"team-deck-report-{name_key.replace(' ', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/teams/{team_id}/members/decks", response_model=list[ResponseMemberDeck])
async def list_member_decks(
    team_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
) -> list[ResponseMemberDeck]:
    """Every current member's own personal decks — owner-only, the pool the
    team admin picks from when flagging a name into the team's rotation."""
    await get_owned_team(session, team_id, current_user)
    result = await session.execute(
        select(TSPersonalDeck)
        .join(TSTeamMember, TSTeamMember.user_id == TSPersonalDeck.owner_id)
        .where(TSTeamMember.team_id == team_id, TSPersonalDeck.archived_at.is_(None))
        .order_by(TSPersonalDeck.name)
    )
    decks = list(result.scalars().all())
    refs = await directory.lookup(deck.owner_id for deck in decks)
    flagged_names_result = await session.execute(
        select(TSTeamDeckFlag.name_key).where(TSTeamDeckFlag.team_id == team_id)
    )
    flagged_names = set(flagged_names_result.scalars().all())

    return [
        ResponseMemberDeck(
            id=deck.id,
            name=deck.name,
            owner_id=deck.owner_id,
            owner_display=_ref_label(refs.get(deck.owner_id)),
            is_flagged=normalize_deck_name(deck.name) in flagged_names,
        )
        for deck in decks
    ]


@router.post(
    "/teams/{team_id}/decks/flags",
    response_model=ResponseTeamDeck,
    status_code=status.HTTP_201_CREATED,
)
async def flag_team_deck(
    team_id: uuid.UUID,
    payload: TeamDeckFlagCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
) -> ResponseTeamDeck:
    """Owner-only: flags a deck's *name* into the team's testing rotation —
    every member owning a same-named deck is included automatically (S2,
    revised 2026-08-01)."""
    await get_owned_team(session, team_id, current_user)
    flag = await flag_deck_name(session, team_id, payload.deck_id, current_user.id)
    groups = await list_team_deck_groups(session, team_id)
    group = next(g for g in groups if g.name_key == flag.name_key)
    refs = await directory.lookup(deck.owner_id for deck in group.owner_decks)
    return ResponseTeamDeck(
        name_key=group.name_key,
        deck_name=group.deck_name,
        owners=_team_deck_owners(group.owner_decks, refs),
        has_thread=group.has_thread,
    )


@router.delete(
    "/teams/{team_id}/decks/flags/{name_key}", status_code=status.HTTP_204_NO_CONTENT
)
async def unflag_team_deck(
    team_id: uuid.UUID,
    name_key: str,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Owner-only: removes a flagged name — every member's matching deck
    drops out of the team's rotation at once."""
    await get_owned_team(session, team_id, current_user)
    await unflag_deck_name(session, team_id, name_key)


async def _get_team_deck_thread(
    session: DatabaseSession, team_id: uuid.UUID, name_key: str
) -> TSTeamDeckThread:
    result = await session.execute(
        select(TSTeamDeckThread).where(
            TSTeamDeckThread.team_id == team_id, TSTeamDeckThread.name_key == name_key
        )
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found."
        )
    return thread


@router.post(
    "/teams/{team_id}/decks/{name_key}/thread",
    status_code=status.HTTP_201_CREATED,
)
async def enable_team_deck_thread(
    team_id: uuid.UUID,
    name_key: str,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Owner-only — which flagged names get a discussion thread is a
    team-admin decision, independent of who owns a matching deck."""
    await get_owned_team(session, team_id, current_user)
    flag_check = await session.execute(
        select(TSTeamDeckThread).where(
            TSTeamDeckThread.team_id == team_id, TSTeamDeckThread.name_key == name_key
        )
    )
    if flag_check.scalar_one_or_none() is not None:
        return
    flag_result = await session.execute(
        select(TSTeamDeckFlag).where(
            TSTeamDeckFlag.team_id == team_id, TSTeamDeckFlag.name_key == name_key
        )
    )
    if flag_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This name isn't flagged into the team.",
        )
    session.add(TSTeamDeckThread(team_id=team_id, name_key=name_key))
    await session.commit()


@router.get(
    "/teams/{team_id}/decks/{name_key}/thread/messages",
    response_model=list[ResponseTeamDeckMessage],
)
async def list_thread_messages(
    team_id: uuid.UUID,
    name_key: str,
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
) -> list[ResponseTeamDeckMessage]:
    await get_member_team(session, team_id, current_user)
    thread = await _get_team_deck_thread(session, team_id, name_key)
    result = await session.execute(
        select(TSTeamDeckMessage)
        .where(TSTeamDeckMessage.thread_id == thread.id)
        .order_by(TSTeamDeckMessage.created_at)
    )
    messages = list(result.scalars().all())
    refs = await directory.lookup(m.author_id for m in messages)
    return [
        ResponseTeamDeckMessage(
            id=message.id,
            thread_id=message.thread_id,
            author_id=message.author_id,
            author_display=_ref_label(refs.get(message.author_id)),
            body=message.body,
            created_at=message.created_at,
        )
        for message in messages
    ]


@router.post(
    "/teams/{team_id}/decks/{name_key}/thread/messages",
    response_model=ResponseTeamDeckMessage,
    status_code=status.HTTP_201_CREATED,
)
async def post_thread_message(
    team_id: uuid.UUID,
    name_key: str,
    payload: TeamDeckThreadMessageCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
    directory: IdentityDirectoryDep,
) -> ResponseTeamDeckMessage:
    await get_member_team(session, team_id, current_user)
    thread = await _get_team_deck_thread(session, team_id, name_key)
    message = TSTeamDeckMessage(
        thread_id=thread.id, author_id=current_user.id, body=payload.body
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return ResponseTeamDeckMessage(
        id=message.id,
        thread_id=message.thread_id,
        author_id=message.author_id,
        author_display=await directory.label(
            current_user.id, fallback=_UNKNOWN_MEMBER_LABEL
        ),
        body=message.body,
        created_at=message.created_at,
    )
