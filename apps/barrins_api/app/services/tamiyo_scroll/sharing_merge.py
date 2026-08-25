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
    CardGame,
    ExpectedLevel,
    GameResult,
    MetagameRosterScope,
    TSMatch,
    TSMetaDeck,
    TSPersonalDeck,
    TSUserSettings,
)
from app.models.user import User


def norm_name(name: str) -> str:
    """Trim + lowercase — the one, reused name-match rule for this module
    and anything cross-deck-matching a roster entry by name (F10 items 4/5)."""
    return name.strip().lower()


_ANONYMOUS_SHARER_LABEL = "a kind user"


def _sharer_label(sharer: User) -> str:
    """Never the email — falls back to a generic label, not personal data."""
    return sharer.display_name or _ANONYMOUS_SHARER_LABEL


def _group_meta_decks_by_name_and_game(
    decks: list[EffectiveMetaDeck],
) -> dict[tuple[str, CardGame | None], list[EffectiveMetaDeck]]:
    groups: dict[tuple[str, CardGame | None], list[EffectiveMetaDeck]] = defaultdict(
        list
    )
    for deck in decks:
        groups[(norm_name(deck.name), deck.game)].append(deck)
    return groups


def collapse_by_name_and_game(
    decks: list[EffectiveMetaDeck],
) -> list[EffectiveMetaDeck]:
    """F10 item 4: within `"game"` roster scope, same-name, same-`game`
    rows fold into one line — a Magic and a Pokémon deck sharing a name
    never merge (`game` is part of the match key, via the same `norm_name`
    trim/lowercase rule this module already uses for sharer matching).
    Callers pass only non-archived rows; archived rows are never part of
    this collapse.

    Ties (divergent tier/category between the grouped rows) resolve to
    the most recently updated row (item 6) — the same rule item 5's
    create-time pre-fill uses.
    """
    collapsed: list[EffectiveMetaDeck] = []
    for group in _group_meta_decks_by_name_and_game(decks).values():
        if len(group) == 1:
            collapsed.append(group[0])
            continue
        canonical = max(group, key=lambda d: d.updated_at)
        has_shared_data = any(d.has_shared_data for d in group)
        merged_ids = tuple(d.id for d in group)
        collapsed.append(
            replace(canonical, has_shared_data=has_shared_data, merged_ids=merged_ids)
        )
    return collapsed


def collapse_meta_decks_and_remap_matches(
    meta_decks: list[EffectiveMetaDeck],
    matches: list[EffectiveMatch],
) -> tuple[list[EffectiveMetaDeck], list[EffectiveMatch]]:
    """Same collapse as `collapse_by_name_and_game`, plus remapping every
    match's `opponent_deck_id` from a merged-away duplicate onto its
    group's canonical id.

    Needed by `get_archetype_summary`/`get_matchup_summary` (F10 UAT):
    the migration's duplicate-and-allocate backfill can leave two
    `TSMetaDeck` rows for what's really one opponent — one carrying the
    match history, its sibling none. Collapsing the *display* rows alone
    (as `list_meta_decks` does) isn't enough there, since a winrate/
    matchup-count computed from only the canonical row's own matches
    would silently drop the sibling's — this remaps matches first so the
    combined history is what gets tallied, under whichever id survives.
    """
    groups = _group_meta_decks_by_name_and_game(meta_decks)
    collapsed: list[EffectiveMetaDeck] = []
    remap: dict[UUID, UUID] = {}
    for group in groups.values():
        canonical = max(group, key=lambda d: d.updated_at)
        has_shared_data = any(d.has_shared_data for d in group)
        merged_ids = tuple(d.id for d in group)
        collapsed.append(
            replace(canonical, has_shared_data=has_shared_data, merged_ids=merged_ids)
        )
        for deck in group:
            remap[deck.id] = canonical.id

    remapped_matches = [
        replace(m, opponent_deck_id=remap.get(m.opponent_deck_id, m.opponent_deck_id))
        for m in matches
    ]
    return collapsed, remapped_matches


async def resolve_metagame_roster_scope(
    session: DatabaseSession, current_user: User, personal_deck_id: UUID
) -> tuple[MetagameRosterScope, CardGame | None]:
    """The caller's `metagame_roster_scope` setting, plus `personal_deck_id`'s
    own `game` (only meaningful for `"game"` scope) — the shared scoping key
    every "roster relative to one active/selected deck" endpoint needs
    (F10: `list_meta_decks`, `get_archetype_summary`)."""
    settings_result = await session.execute(
        select(TSUserSettings.metagame_roster_scope).where(
            TSUserSettings.user_id == current_user.id
        )
    )
    scope = settings_result.scalar_one_or_none() or MetagameRosterScope.game
    active_game_result = await session.execute(
        select(TSPersonalDeck.game).where(TSPersonalDeck.id == personal_deck_id)
    )
    return scope, active_game_result.scalar_one_or_none()


def scope_meta_decks(
    meta_decks: list[EffectiveMetaDeck],
    *,
    scope: MetagameRosterScope,
    active_game: CardGame | None,
    personal_deck_id: UUID,
) -> list[EffectiveMetaDeck]:
    """Filters an already-fetched roster down to what `personal_deck_id`
    should see, per `resolve_metagame_roster_scope`'s result (F10) — the
    same rule `list_meta_decks` applies, shared here so
    `get_archetype_summary` (which lists every roster deck per category,
    "even empty ones, for a stable display grid" — `stats.compute_
    archetype_summary`'s own docstring) doesn't leak every other game's
    roster the same way the roster tab itself used to.
    """
    if scope == MetagameRosterScope.personal_deck:
        return [d for d in meta_decks if d.personal_deck_id == personal_deck_id]
    return [d for d in meta_decks if d.game == active_game]


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

    `personal_deck_id` is `None` for a foreign (`is_readonly`) row — the
    sharer's own id is never exposed to the viewer, same "never leak a
    sharer's raw id" rule `EffectiveMatch` already follows.

    `merged_ids` lists every underlying `TSMetaDeck.id` this row
    represents — just `[id]` normally, or every id a F10 game-scope
    collapse (`collapse_by_name_and_game`/
    `collapse_meta_decks_and_remap_matches`) folded together. Consumers
    that resolve a `TSMatch.opponent_deck_id` against the (possibly
    collapsed) roster need this: an existing match can still reference a
    merged-away duplicate's id, which `id` alone wouldn't match anymore.
    """

    id: UUID
    name: str
    personal_deck_id: UUID | None
    tier: Decimal
    category: ArchetypeCategory
    game: CardGame | None
    decklist_notes: str | None
    top8: int
    presence: int
    expected: ExpectedLevel
    tests_status: str | None
    archived_at: datetime | None
    updated_at: datetime
    is_readonly: bool
    shared_by: str | None = None
    has_shared_data: bool = False
    is_multi_share: bool = False
    merged_ids: tuple[UUID, ...] = ()


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
    game_override: CardGame | None = None,
) -> EffectiveMetaDeck:
    return EffectiveMetaDeck(
        id=deck.id,
        name=deck.name,
        personal_deck_id=None if is_readonly else deck.personal_deck_id,
        tier=deck.tier,
        category=deck.category,
        game=game_override if game_override is not None else deck.game,
        decklist_notes=deck.decklist_notes,
        top8=deck.top8,
        presence=deck.presence,
        expected=deck.expected,
        tests_status=deck.tests_status,
        archived_at=deck.archived_at,
        updated_at=deck.updated_at,
        is_readonly=is_readonly,
        shared_by=shared_by,
        is_multi_share=is_multi_share,
        merged_ids=(deck.id,),
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
    filter_meta_decks_by_personal_deck: bool = False,
) -> MergedView:
    """Own matches/roster, plus any name-matched sharer data merged in read-only.

    `personal_deck_id` scopes `matches` (and, via `own_decks_stmt` below,
    which of the viewer's own decks are considered for sharer name-
    matching) — the existing behavior every caller (`matches.py`,
    `stats.py`, the PDF report route) already relies on: a full roster,
    with only the *matches* narrowed to one deck.

    `filter_meta_decks_by_personal_deck` is a separate opt-in (F10,
    `meta_decks.py`'s `"personal_deck"` roster scope only) — narrowing
    `meta_decks` itself to the exact owning deck would silently break
    those existing callers, which read `view.meta_decks` expecting every
    roster entry regardless of `personal_deck_id`.
    """
    own_meta_decks_stmt = select(TSMetaDeck).where(
        TSMetaDeck.owner_id == current_user.id
    )
    if filter_meta_decks_by_personal_deck and personal_deck_id is not None:
        own_meta_decks_stmt = own_meta_decks_stmt.where(
            TSMetaDeck.personal_deck_id == personal_deck_id
        )
    own_meta_decks_result = await session.execute(own_meta_decks_stmt)
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
        own_deck_id_by_name.setdefault(norm_name(deck.name), deck.id)

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
    # Every sharer personal deck's own `game` — used below to resolve a
    # foreign roster row's `game` instead of trusting `TSMetaDeck.game`
    # directly. That column is a denormalized copy only ever kept in sync
    # by `create_meta_deck`/`_sync_opponent_deck_games`, both on the
    # sharer's side; a legacy row (pre-dating either) can carry a stale or
    # NULL value the viewer has no way to correct. `TSPersonalDeck.game`
    # is the source of truth this module already treats as reliable
    # elsewhere (F10).
    sharer_personal_deck_game: dict[UUID, CardGame | None] = {}
    for deck in sharer_decks_result.scalars().all():
        sharer_personal_deck_game[deck.id] = deck.game
        own_id = own_deck_id_by_name.get(norm_name(deck.name))
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
        norm_name(d.name): d.id for d in own_meta_decks if d.archived_at is None
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
        own_id = own_meta_deck_id_by_name.get(norm_name(sharer_deck.name))
        if own_id is not None:
            opponent_remap[sharer_deck.id] = own_id
            continue
        foreign_groups[norm_name(sharer_deck.name)].append(sharer_deck)

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
                game_override=sharer_personal_deck_game.get(canonical.personal_deck_id),
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
            replace(d, has_shared_data=True)
            if d.id in own_ids_with_shared_matches
            else d
            for d in effective_meta_decks
        ]

    return MergedView(matches=effective_matches, meta_decks=effective_meta_decks)
