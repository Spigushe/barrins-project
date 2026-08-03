"""Team sharing (S2, "Team Decks") — creation, membership, access, rate limiting.

Mirrors `ownership.py`'s shape for the read-access question ("does this
caller get to see this deck") and `EmailVerification`'s DB-backed
cooldown/attempts pattern for rate limiting (no Redis) — see
`docs/project/v2.0.0-bump/s2-team-sharing/`.

Team-deck sharing is name-based (revised 2026-08-01): the team owner flags
a deck *name* (`TSTeamDeckFlag`) into the team's testing rotation, and
every team member's own personal deck with that exact name (present or
future) is automatically included — mirrors `sharing_merge.py`'s existing
"matched by exact name" convention, applied here instead of per-deck-
instance bookkeeping.
"""

import secrets
import string
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RateLimitExceededError
from app.models.tamiyo_scroll import (
    TSCardTest,
    TSInviteAttempt,
    TSMatch,
    TSPersonalDeck,
    TSTeam,
    TSTeamDeckFlag,
    TSTeamDeckThread,
    TSTeamMember,
)
from app.models.user import User

_INVITE_CODE_ALPHABET = string.ascii_uppercase + string.digits
INVITE_CODE_LENGTH = 8

_INVITE_MIN_INTERVAL = timedelta(seconds=5)
_INVITE_WINDOW = timedelta(minutes=1)
_INVITE_MAX_PER_WINDOW = 5


def normalize_deck_name(name: str) -> str:
    return name.strip().lower()


def generate_invite_code() -> str:
    """8 uppercase-alphanumeric characters (CSPRNG) — uniqueness enforced
    by the DB's `UNIQUE(invite_code)` constraint, not checked here."""
    return "".join(
        secrets.choice(_INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH)
    )


def normalize_invite_code(raw: str) -> str:
    """Uppercases and strips the display-only `XXXX-XXXX` dash grouping."""
    return raw.strip().upper().replace("-", "")


async def check_and_record_invite_attempt(
    session: AsyncSession, user_id: uuid.UUID
) -> None:
    """Enforce 1 attempt/5s and 5 attempts/min per user, then record one.

    Raises `RateLimitExceededError` (429) without recording the attempt if
    either limit is currently exceeded — a rejected attempt doesn't itself
    count against the caller.
    """
    now = datetime.now(UTC)
    result = await session.execute(
        select(TSInviteAttempt).where(TSInviteAttempt.user_id == user_id)
    )
    attempt = result.scalar_one_or_none()

    if attempt is None:
        session.add(
            TSInviteAttempt(
                user_id=user_id,
                window_started_at=now,
                attempts_in_window=1,
                last_attempt_at=now,
            )
        )
        await session.commit()
        return

    if now - attempt.last_attempt_at < _INVITE_MIN_INTERVAL:
        raise RateLimitExceededError("Too many attempts. Please slow down.")

    if now - attempt.window_started_at >= _INVITE_WINDOW:
        attempt.window_started_at = now
        attempt.attempts_in_window = 0

    if attempt.attempts_in_window >= _INVITE_MAX_PER_WINDOW:
        raise RateLimitExceededError("Too many attempts. Please try again in a minute.")

    attempt.attempts_in_window += 1
    attempt.last_attempt_at = now
    session.add(attempt)
    await session.commit()


async def is_team_member(
    session: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    result = await session.execute(
        select(TSTeamMember).where(
            TSTeamMember.team_id == team_id, TSTeamMember.user_id == user_id
        )
    )
    return result.scalar_one_or_none() is not None


async def get_member_team(
    session: AsyncSession, team_id: uuid.UUID, current_user: User
) -> TSTeam:
    """404 unless `team_id` exists and `current_user` belongs to it.

    Same 404-uniformly-for-"not yours"-and-"doesn't exist" convention as
    `personal_decks._get_owned_personal_deck`.
    """
    result = await session.execute(select(TSTeam).where(TSTeam.id == team_id))
    team = result.scalar_one_or_none()
    if team is None or not await is_team_member(session, team_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found."
        )
    return team


async def get_owned_team(
    session: AsyncSession, team_id: uuid.UUID, current_user: User
) -> TSTeam:
    """404 unless `team_id` exists and `current_user` is its owner."""
    result = await session.execute(select(TSTeam).where(TSTeam.id == team_id))
    team = result.scalar_one_or_none()
    if team is None or team.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found."
        )
    return team


async def _team_ids_flagging_name(
    session: AsyncSession, name_key: str, user_id: uuid.UUID
) -> set[uuid.UUID]:
    """Teams `user_id` belongs to that have `name_key` flagged."""
    result = await session.execute(
        select(TSTeamDeckFlag.team_id)
        .join(TSTeamMember, TSTeamMember.team_id == TSTeamDeckFlag.team_id)
        .where(TSTeamDeckFlag.name_key == name_key, TSTeamMember.user_id == user_id)
    )
    return set(result.scalars().all())


async def resolve_team_deck_access(
    session: AsyncSession, deck_id: uuid.UUID, current_user: User
) -> TSPersonalDeck:
    """404 unless `current_user` owns the deck, or shares a team with the
    deck's owner where a deck of this exact name is flagged.

    Used alongside (not instead of) the plain owner-only path — e.g. the
    deck-level PDF report route (S5) also accepts team-member access.
    """
    result = await session.execute(
        select(TSPersonalDeck).where(TSPersonalDeck.id == deck_id)
    )
    deck = result.scalar_one_or_none()
    if deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Personal deck not found."
        )
    if deck.owner_id == current_user.id:
        return deck

    name_key = normalize_deck_name(deck.name)
    viewer_team_ids = await _team_ids_flagging_name(session, name_key, current_user.id)
    if viewer_team_ids:
        owner_membership = await session.execute(
            select(TSTeamMember.team_id).where(
                TSTeamMember.team_id.in_(viewer_team_ids),
                TSTeamMember.user_id == deck.owner_id,
            )
        )
        if owner_membership.scalars().first() is not None:
            return deck

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Personal deck not found."
    )


async def _team_member_decks_by_name(
    session: AsyncSession, team_id: uuid.UUID
) -> dict[str, list[tuple[TSPersonalDeck, User]]]:
    """Every non-archived personal deck owned by a member of `team_id`,
    grouped by normalized name."""
    result = await session.execute(
        select(TSPersonalDeck, User)
        .join(User, User.id == TSPersonalDeck.owner_id)
        .join(TSTeamMember, TSTeamMember.user_id == TSPersonalDeck.owner_id)
        .where(TSTeamMember.team_id == team_id, TSPersonalDeck.archived_at.is_(None))
    )
    by_name: dict[str, list[tuple[TSPersonalDeck, User]]] = defaultdict(list)
    for deck, owner in result.all():
        by_name[normalize_deck_name(deck.name)].append((deck, owner))
    return by_name


async def get_team_deck_owners(
    session: AsyncSession, team_id: uuid.UUID, name_key: str
) -> list[tuple[TSPersonalDeck, User]]:
    """Every current team member owning a deck matching `name_key` — the
    cumulative report's contributor list."""
    by_name = await _team_member_decks_by_name(session, team_id)
    return by_name.get(name_key, [])


@dataclass(frozen=True)
class TeamDeckGroup:
    """One row for the "Team Decks" list — a flagged name, plus whichever
    current members (if any) own a matching deck."""

    name_key: str
    deck_name: str
    owners: list[tuple[TSPersonalDeck, User]] = field(default_factory=list)
    has_thread: bool = False


async def list_team_deck_groups(
    session: AsyncSession, team_id: uuid.UUID
) -> list[TeamDeckGroup]:
    flags_result = await session.execute(
        select(TSTeamDeckFlag).where(TSTeamDeckFlag.team_id == team_id)
    )
    flags = list(flags_result.scalars().all())
    if not flags:
        return []

    decks_by_name = await _team_member_decks_by_name(session, team_id)

    threads_result = await session.execute(
        select(TSTeamDeckThread.name_key).where(TSTeamDeckThread.team_id == team_id)
    )
    name_keys_with_thread = set(threads_result.scalars().all())

    groups = [
        TeamDeckGroup(
            name_key=flag.name_key,
            deck_name=flag.deck_name,
            owners=decks_by_name.get(flag.name_key, []),
            has_thread=flag.name_key in name_keys_with_thread,
        )
        for flag in flags
    ]
    return sorted(groups, key=lambda g: g.name_key)


async def flag_deck_name(
    session: AsyncSession, team_id: uuid.UUID, deck_id: uuid.UUID, flagged_by: User
) -> TSTeamDeckFlag:
    """Flags a deck's name into the team's rotation — the deck must belong
    to a current team member. Idempotent: flagging an already-flagged name
    returns the existing flag rather than erroring."""
    deck_result = await session.execute(
        select(TSPersonalDeck).where(TSPersonalDeck.id == deck_id)
    )
    deck = deck_result.scalar_one_or_none()
    if deck is None or not await is_team_member(session, team_id, deck.owner_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Personal deck not found."
        )

    name_key = normalize_deck_name(deck.name)
    existing_result = await session.execute(
        select(TSTeamDeckFlag).where(
            TSTeamDeckFlag.team_id == team_id, TSTeamDeckFlag.name_key == name_key
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return existing

    flag = TSTeamDeckFlag(
        team_id=team_id,
        deck_name=deck.name,
        name_key=name_key,
        flagged_by=flagged_by.id,
    )
    session.add(flag)
    await session.commit()
    await session.refresh(flag)
    return flag


async def unflag_deck_name(
    session: AsyncSession, team_id: uuid.UUID, name_key: str
) -> None:
    result = await session.execute(
        select(TSTeamDeckFlag).where(
            TSTeamDeckFlag.team_id == team_id, TSTeamDeckFlag.name_key == name_key
        )
    )
    flag = result.scalar_one_or_none()
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found."
        )
    await session.delete(flag)
    await session.commit()


class MemberActivity:
    """Per-member test/match counts across a team's flagged decks."""

    def __init__(
        self,
        tests_by_user: Counter[uuid.UUID],
        matches_by_user: Counter[uuid.UUID],
    ):
        self.tests_by_user = tests_by_user
        self.matches_by_user = matches_by_user

    def total_for(self, user_id: uuid.UUID) -> int:
        return self.tests_by_user[user_id] + self.matches_by_user[user_id]


async def compute_member_activity(
    session: AsyncSession, team_id: uuid.UUID
) -> MemberActivity:
    """Counts tests/matches logged by each member, across their own decks
    whose name is currently flagged into `team_id` — the member list's
    "tests/matches logged" column."""
    groups = await list_team_deck_groups(session, team_id)
    deck_ids = [deck.id for group in groups for deck, _ in group.owners]
    if not deck_ids:
        return MemberActivity(Counter(), Counter())

    tests_result = await session.execute(
        select(TSCardTest.owner_id).where(TSCardTest.personal_deck_id.in_(deck_ids))
    )
    matches_result = await session.execute(
        select(TSMatch.owner_id).where(TSMatch.personal_deck_id.in_(deck_ids))
    )
    return MemberActivity(
        Counter(tests_result.scalars().all()),
        Counter(matches_result.scalars().all()),
    )
