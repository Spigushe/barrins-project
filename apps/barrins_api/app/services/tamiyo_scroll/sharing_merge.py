"""Automatic read-only merge of shared decks into the current user's own view.

Sharer attribution (`shared_by`) never exposes an email address — that
would be a real name/email leak to any receiving account, not just a
UI nicety (GDPR: no personal data disclosed beyond what the sharer chose
to set as their `display_name`). Falls back to a generic label instead.

No per-sharer/team linkage exists yet (S2 not built) — a sharer's personal
deck is considered "the same" as one of the current user's own decks purely
by exact name match (trimmed, case-insensitive). This supersedes S1's
original "View: {user}" selector entirely: sharing is now folded
automatically into the viewer's own Journal (matches) and Metagame
(roster + stats), never a separate read-only "view as" mode.

Reconciliation rule (per the user, 2026-07-30):
- A shared match's opponent deck is displayed under the viewer's OWN
  roster entry when an entry with the same name already exists (their own
  tier/category wins over the sharer's) — matches from both sides count
  toward the same roster row.
- If the viewer has no roster entry with that name, the sharer's roster
  entry is added as a new read-only line instead of being dropped.
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.database.session import DatabaseSession
from app.models.tamiyo_scroll import (
    ArchetypeCategory,
    ExpectedLevel,
    GameResult,
    TSMatch,
    TSMetaDeck,
    TSPersonalDeck,
    TSUserSettings,
)
from app.models.user import User


def _norm(name: str) -> str:
    return name.strip().lower()


_ANONYMOUS_SHARER_LABEL = "a kind user"


def _sharer_label(sharer: User) -> str:
    """Never the email — falls back to a generic label, not personal data."""
    return sharer.display_name or _ANONYMOUS_SHARER_LABEL


@dataclass(frozen=True)
class EffectiveMatch:
    """A match as it should appear in the viewer's own Journal/stats.

    Same shape as `TSMatch` (so it satisfies `ResponseMatch.model_validate`
    and the pure calculation functions in `stats.py`), plus `is_readonly`/
    `shared_by` for a merged-in foreign match. `personal_deck_id` and
    `opponent_deck_id` are the viewer's own ids whenever a name match
    exists — never the sharer's raw ids leaking into the viewer's view.
    """

    id: UUID
    date: date
    personal_deck_id: UUID
    opponent_deck_id: UUID
    decklist_version_id: UUID | None
    session_id: UUID | None
    on_play: bool
    game1: GameResult | None
    game2: GameResult | None
    game3: GameResult | None
    opening_hand: str | None
    turning_point: str | None
    final_turn: str | None
    created_at: datetime
    is_readonly: bool
    shared_by: str | None = None


@dataclass(frozen=True)
class EffectiveMetaDeck:
    """A roster entry as it should appear in the viewer's own Metagame tab.

    `has_shared_data` marks an **own** (`is_readonly=False`) entry that has
    also received at least one merged match from a sharer — distinct from
    `is_readonly` (a fully-foreign entry with no owner equivalent). A deck
    can be "mixed": the viewer's own matches plus a sharer's, both counted
    under the same roster row (see reconciliation rule above).
    """

    id: UUID
    name: str
    tier: Decimal
    category: ArchetypeCategory
    decklist_notes: str | None
    top8: int
    presence: int
    expected: ExpectedLevel
    tests_status: str | None
    archived_at: datetime | None
    is_readonly: bool
    shared_by: str | None = None
    has_shared_data: bool = False
    is_multi_share: bool = False


def _from_match(
    match: TSMatch, *, is_readonly: bool, shared_by: str | None
) -> EffectiveMatch:
    return EffectiveMatch(
        id=match.id,
        date=match.date,
        personal_deck_id=match.personal_deck_id,
        opponent_deck_id=match.opponent_deck_id,
        decklist_version_id=match.decklist_version_id,
        session_id=match.session_id,
        on_play=match.on_play,
        game1=match.game1,
        game2=match.game2,
        game3=match.game3,
        opening_hand=match.opening_hand,
        turning_point=match.turning_point,
        final_turn=match.final_turn,
        created_at=match.created_at,
        is_readonly=is_readonly,
        shared_by=shared_by,
    )


def _from_meta_deck(
    deck: TSMetaDeck,
    *,
    is_readonly: bool,
    shared_by: str | None,
    is_multi_share: bool = False,
) -> EffectiveMetaDeck:
    return EffectiveMetaDeck(
        id=deck.id,
        name=deck.name,
        tier=deck.tier,
        category=deck.category,
        decklist_notes=deck.decklist_notes,
        top8=deck.top8,
        presence=deck.presence,
        expected=deck.expected,
        tests_status=deck.tests_status,
        archived_at=deck.archived_at,
        is_readonly=is_readonly,
        shared_by=shared_by,
        is_multi_share=is_multi_share,
    )


@dataclass(frozen=True)
class MergedView:
    matches: list[EffectiveMatch]
    meta_decks: list[EffectiveMetaDeck]

    @property
    def readonly_meta_deck_ids(self) -> frozenset[UUID]:
        return frozenset(d.id for d in self.meta_decks if d.is_readonly)


async def build_merged_view(
    session: DatabaseSession,
    current_user: User,
    *,
    personal_deck_id: UUID | None = None,
) -> MergedView:
    """Own matches/roster, plus any name-matched sharer data merged in read-only."""
    own_meta_decks_result = await session.execute(
        select(TSMetaDeck).where(TSMetaDeck.owner_id == current_user.id)
    )
    own_meta_decks = list(own_meta_decks_result.scalars().all())

    own_matches_stmt = select(TSMatch).where(TSMatch.owner_id == current_user.id)
    if personal_deck_id is not None:
        own_matches_stmt = own_matches_stmt.where(
            TSMatch.personal_deck_id == personal_deck_id
        )
    own_matches_result = await session.execute(own_matches_stmt)
    own_matches = list(own_matches_result.scalars().all())

    effective_matches = [
        _from_match(m, is_readonly=False, shared_by=None) for m in own_matches
    ]
    effective_meta_decks = [
        _from_meta_deck(d, is_readonly=False, shared_by=None) for d in own_meta_decks
    ]
    empty_view = MergedView(matches=effective_matches, meta_decks=effective_meta_decks)

    viewer_settings_result = await session.execute(
        select(TSUserSettings).where(TSUserSettings.user_id == current_user.id)
    )
    viewer_settings = viewer_settings_result.scalar_one_or_none()
    if viewer_settings is None or not viewer_settings.receive_shared_data:
        return empty_view

    own_decks_stmt = select(TSPersonalDeck).where(
        TSPersonalDeck.owner_id == current_user.id
    )
    if personal_deck_id is not None:
        own_decks_stmt = own_decks_stmt.where(TSPersonalDeck.id == personal_deck_id)
    own_decks_result = await session.execute(own_decks_stmt)
    own_decks = list(own_decks_result.scalars().all())
    if not own_decks:
        return empty_view

    own_deck_id_by_name: dict[str, UUID] = {}
    for deck in own_decks:
        own_deck_id_by_name.setdefault(_norm(deck.name), deck.id)

    sharers_result = await session.execute(
        select(User)
        .join(TSUserSettings, TSUserSettings.user_id == User.id)
        .where(TSUserSettings.data_shared.is_(True), User.id != current_user.id)
    )
    sharers = list(sharers_result.scalars().all())
    if not sharers:
        return empty_view
    sharer_label_by_id = {s.id: _sharer_label(s) for s in sharers}

    sharer_decks_result = await session.execute(
        select(TSPersonalDeck).where(
            TSPersonalDeck.owner_id.in_([s.id for s in sharers])
        )
    )
    matched_sharer_deck_own_id: dict[UUID, UUID] = {}
    sharer_deck_owner: dict[UUID, UUID] = {}
    for deck in sharer_decks_result.scalars().all():
        own_id = own_deck_id_by_name.get(_norm(deck.name))
        if own_id is not None:
            matched_sharer_deck_own_id[deck.id] = own_id
            sharer_deck_owner[deck.id] = deck.owner_id
    if not matched_sharer_deck_own_id:
        return empty_view

    sharer_matches_result = await session.execute(
        select(TSMatch).where(
            TSMatch.personal_deck_id.in_(matched_sharer_deck_own_id.keys())
        )
    )
    sharer_matches = list(sharer_matches_result.scalars().all())
    if not sharer_matches:
        return empty_view

    sharer_opponent_ids = {m.opponent_deck_id for m in sharer_matches}
    sharer_meta_decks_result = await session.execute(
        select(TSMetaDeck).where(TSMetaDeck.id.in_(sharer_opponent_ids))
    )
    sharer_meta_decks_by_id = {
        d.id: d for d in sharer_meta_decks_result.scalars().all()
    }

    # Archived-out owner decks don't count as a match: otherwise a foreign
    # opponent silently loses its read-only roster line the moment the
    # viewer archives their own same-named entry (the match's
    # opponent_deck_id would still point at the now-archived, now-hidden
    # owner deck instead of falling back to a fresh read-only line).
    own_meta_deck_id_by_name: dict[str, UUID] = {
        _norm(d.name): d.id for d in own_meta_decks if d.archived_at is None
    }

    # Sharer opponent id -> the id matches should effectively point to: the
    # viewer's own roster entry (name match) or a consolidated foreign
    # entry (new read-only line).
    opponent_remap: dict[UUID, UUID] = {}
    # Foreign decks (no owner equivalent) grouped by normalized name: two
    # different sharers each having their own "Aragorn, King of Gondor"
    # roster entry must not produce two read-only lines — they're folded
    # into one (highest tier wins, "multi share" instead of a single
    # "from: {sharer}" once more than one sharer contributes).
    foreign_groups: dict[str, list[TSMetaDeck]] = defaultdict(list)
    for sharer_deck in sharer_meta_decks_by_id.values():
        own_id = own_meta_deck_id_by_name.get(_norm(sharer_deck.name))
        if own_id is not None:
            opponent_remap[sharer_deck.id] = own_id
            continue
        foreign_groups[_norm(sharer_deck.name)].append(sharer_deck)

    for group in foreign_groups.values():
        canonical = max(group, key=lambda d: d.tier)
        for sharer_deck in group:
            opponent_remap[sharer_deck.id] = canonical.id
        distinct_owners = {d.owner_id for d in group}
        is_multi_share = len(distinct_owners) > 1
        owner_label = (
            None
            if is_multi_share
            else sharer_label_by_id.get(canonical.owner_id, _ANONYMOUS_SHARER_LABEL)
        )
        effective_meta_decks.append(
            _from_meta_deck(
                canonical,
                is_readonly=True,
                shared_by=owner_label,
                is_multi_share=is_multi_share,
            )
        )

    own_meta_deck_ids = {d.id for d in own_meta_decks}
    own_ids_with_shared_matches: set[UUID] = set()

    for match in sharer_matches:
        own_deck_id = matched_sharer_deck_own_id[match.personal_deck_id]
        owner_label = sharer_label_by_id.get(
            sharer_deck_owner[match.personal_deck_id], _ANONYMOUS_SHARER_LABEL
        )
        resolved_opponent_id = opponent_remap.get(
            match.opponent_deck_id, match.opponent_deck_id
        )
        if resolved_opponent_id in own_meta_deck_ids:
            own_ids_with_shared_matches.add(resolved_opponent_id)
        effective_matches.append(
            EffectiveMatch(
                id=match.id,
                date=match.date,
                personal_deck_id=own_deck_id,
                opponent_deck_id=resolved_opponent_id,
                decklist_version_id=None,
                # A sharer's session_id points into their own ts_sessions —
                # meaningless (and inaccessible) to the viewer, and sessions
                # aren't part of the sharing-merge concept (S9); never leaked.
                session_id=None,
                on_play=match.on_play,
                game1=match.game1,
                game2=match.game2,
                game3=match.game3,
                opening_hand=match.opening_hand,
                turning_point=match.turning_point,
                final_turn=match.final_turn,
                created_at=match.created_at,
                is_readonly=True,
                shared_by=owner_label,
            )
        )

    if own_ids_with_shared_matches:
        effective_meta_decks = [
            replace(d, has_shared_data=True) if d.id in own_ids_with_shared_matches
            else d
            for d in effective_meta_decks
        ]

    return MergedView(matches=effective_matches, meta_decks=effective_meta_decks)
