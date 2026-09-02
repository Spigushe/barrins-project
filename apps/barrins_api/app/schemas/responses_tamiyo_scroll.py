"""Response schemas for the Tamiyo Scroll domain (Competitive MTG Tracking)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import computed_field

from app.models.tamiyo_scroll import (
    ArchetypeCategory,
    CardGame,
    DecklistVersionSource,
    ExpectedLevel,
    GameResult,
    SessionType,
)
from app.schemas.responses_base import BaseResponse
from app.services.decklist_sort import DecklistCardCategory
from app.services.metrics.aggregates import MetricSource


class ResponseUserSettings(BaseResponse):
    data_shared: bool
    receive_shared_data: bool
    active_personal_deck_id: uuid.UUID | None


class ResponsePersonalDeck(BaseResponse):
    id: uuid.UUID
    name: str
    # Nullable (S10/S11) — NULL on a historical, pre-migration deck until
    # PATCHed; the frontend uses this to show the "set up before logging"
    # affordance rather than waiting for a match-write 422.
    game: CardGame | None
    category: ArchetypeCategory | None
    archived_at: datetime | None
    created_at: datetime


class ResponseDecklistVersion(BaseResponse):
    id: uuid.UUID
    personal_deck_id: uuid.UUID
    version: int
    content: str
    source: DecklistVersionSource
    created_at: datetime
    # Only ever set on the import-moxfield response itself (S3's opportunistic
    # staleness check) — None everywhere else: no prior Moxfield-sourced
    # version to compare against, or this version isn't a Moxfield import.
    moxfield_deck_changed_since_last_import: bool | None = None


class ResponseMetaDeck(BaseResponse):
    id: uuid.UUID
    name: str
    tier: float
    category: ArchetypeCategory
    # Nullable — inherited automatically from whichever personal deck this
    # meta deck was created against (soft data tag, no enforced constraint;
    # see TSMetaDeck.game's docstring). None if created without that
    # context, or if that personal deck itself had no game set yet.
    game: CardGame | None
    decklist_notes: str | None
    top8: int
    presence: int
    expected: ExpectedLevel
    tests_status: str | None
    archived_at: datetime | None
    is_readonly: bool = False
    shared_by: str | None = None
    has_shared_data: bool = False
    is_multi_share: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def conversion(self) -> float | None:
        """Top8 / Presence in % — None (displayed as "—" in the UI) if presence = 0."""
        if not self.presence:
            return None
        return round(self.top8 / self.presence * 100, 2)


class ResponseMatch(BaseResponse):
    id: uuid.UUID
    date: date
    personal_deck_id: uuid.UUID
    opponent_deck_id: uuid.UUID
    decklist_version_id: uuid.UUID | None
    session_id: uuid.UUID | None
    on_play: bool
    game1: GameResult | None
    game2: GameResult | None
    game3: GameResult | None
    opening_hand: str | None
    turning_point: str | None
    final_turn: str | None
    created_at: datetime
    is_readonly: bool = False
    shared_by: str | None = None


class ResponseCardTest(BaseResponse):
    id: uuid.UUID
    personal_deck_id: uuid.UUID | None
    tester: str
    card_name: str
    opponent_deck_id: uuid.UUID | None
    rating: int
    notes: str | None
    created_at: datetime


class ResponseDecklistLine(BaseResponse):
    """A line of the current decklist, colored based on test feedback."""

    line: str
    status: Literal["validated", "rejected", "in_test", "neutral"]


class ResponseDecklistCard(BaseResponse):
    """One resolved card line within a structured decklist-view section."""

    qty: int
    name: str
    status: Literal["validated", "rejected", "in_test", "neutral"]
    mana_cost: str | None
    type_line: str | None
    text: str | None
    keywords: list[str]
    scryfall_id: str | None


class ResponseDecklistTypeGroup(BaseResponse):
    """One type-ordered section of `library_cards` (e.g. "creature" with
    its cards) -- Duel Commander display order (planeswalker, battle,
    creature, instant, sorcery, artifact, enchantment, land, other), each
    sorted by mana value then name. `category` is a stable machine-readable
    key, not a display label -- pluralization/translation is the
    frontend's job."""

    category: DecklistCardCategory
    count: int
    cards: list[ResponseDecklistCard]


class ResponseDecklistView(BaseResponse):
    """Structured Commander/Library decklist view.

    `commander_cards` is empty when the decklist has no recognized
    "Commander" header line — an expected fallback (manually-pasted or
    pre-feature decks), not an error; the frontend simply omits the
    Commander box. `unparsed_lines` preserves `ResponseDecklistLine`'s
    flat shape for any line that isn't a "<qty> <name>" card line, so
    nothing the coloring feature colors today silently disappears.
    """

    commander_cards: list[ResponseDecklistCard]
    library_cards: list[ResponseDecklistTypeGroup]
    unparsed_lines: list[ResponseDecklistLine]


class ResponseDeckWinrate(BaseResponse):
    """Individual winrate of a roster deck, within an archetype group."""

    id: uuid.UUID
    name: str
    winrate: float | None
    is_readonly: bool = False
    has_shared_data: bool = False


class ResponseArchetypeSummary(BaseResponse):
    category: ArchetypeCategory
    average_winrate: float | None
    decks: list[ResponseDeckWinrate]


class ResponseMatchupRow(BaseResponse):
    opponent_deck_id: uuid.UUID
    opponent_deck_name: str
    winrate_global: float | None
    winrate_otp: float | None
    winrate_otd: float | None
    ratio_otp: str
    ratio_otd: str
    match_count: int
    is_readonly: bool = False
    has_shared_data: bool = False


class ResponseMatchupSummary(BaseResponse):
    rows: list[ResponseMatchupRow]
    average_winrate: float | None


class ResponseSession(BaseResponse):
    id: uuid.UUID
    owner_id: uuid.UUID
    personal_deck_id: uuid.UUID
    name: str
    type: SessionType
    notes: str | None
    created_at: datetime
    ended_at: datetime | None
    archived_at: datetime | None


class ResponseSessionComparison(BaseResponse):
    """Session's own stats vs. the baseline (everything logged before it)."""

    session: ResponseSession
    session_match_count: int
    baseline_match_count: int
    # Total decisive-game win/loss tallies (draws excluded, same as
    # winrate) — the Sessions tab's "V/D" ratio line, distinct from the
    # per-opponent ratios already in *_matchup_summary.rows.
    session_wins: int
    session_losses: int
    baseline_wins: int
    baseline_losses: int
    session_archetype_summary: list[ResponseArchetypeSummary]
    baseline_archetype_summary: list[ResponseArchetypeSummary]
    session_matchup_summary: ResponseMatchupSummary
    baseline_matchup_summary: ResponseMatchupSummary


class ResponseTeamSummary(BaseResponse):
    """Minimal team shape for GET /teams/mine (popup quick-mode + team
    pickers) — no member list, no invite code."""

    id: uuid.UUID
    name: str
    is_owner: bool


class ResponseTeamMember(BaseResponse):
    user_id: uuid.UUID
    # Since the identity cutover (ADR-20) the roster shows the identity
    # handle + display name only — never the email address.
    username: str | None
    display_name: str | None
    is_owner: bool
    joined_at: datetime
    # Tests + matches logged across every deck this member has flagged
    # into the team (Done statement's member-list activity column).
    activity_count: int


class ResponseTeam(BaseResponse):
    """Full team-page shape (GET /teams/{id}).

    `invite_code` is visible to every member, not owner-only — §1.6's
    "given out by existing members to anyone they want to invite" reads as
    any member being allowed to share it; the account-settings popup's
    quick mode simply chooses not to *display* it for non-owners.
    """

    id: uuid.UUID
    name: str
    description: str | None
    invite_code: str
    owner_id: uuid.UUID
    created_at: datetime
    members: list[ResponseTeamMember]


class ResponseTeamDeckOwner(BaseResponse):
    deck_id: uuid.UUID
    display: str


class ResponseTeamDeck(BaseResponse):
    """One *name* flagged into a team's testing rotation (S2, revised
    2026-08-01 — name-based, not per-deck-instance). `owners` lists every
    current member owning a matching deck (with that deck's own id, so the
    frontend can still request e.g. a specific owner's PDF report); empty
    if nobody currently does (e.g. renamed away since flagging)."""

    name_key: str
    deck_name: str
    owners: list[ResponseTeamDeckOwner]
    has_thread: bool


class ResponseMemberDeck(BaseResponse):
    """One team member's own personal deck — the owner's flagging picker
    (GET /teams/{id}/members/decks)."""

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    owner_display: str
    is_flagged: bool


class ResponseTeamDeckMessage(BaseResponse):
    id: uuid.UUID
    thread_id: uuid.UUID
    author_id: uuid.UUID
    author_display: str
    body: str
    created_at: datetime


class ResponseAggregateMetric(BaseResponse):
    """A single aggregate count tagged with its app/source (S6, forward
    compat with the planned v3.0.0 externalization — see
    `app.services.metrics.aggregates.AggregateMetric`)."""

    value: int
    source: MetricSource


class ResponsePlatformMetrics(BaseResponse):
    """Admin dashboard payload (S6) — the adoption signals still sourced
    locally after the identity cutover (ADR-20): total personal decks and
    total matches. "Total accounts" moved to `barrins_identity` and isn't
    exposed here yet."""

    total_personal_decks: ResponseAggregateMetric
    total_matches: ResponseAggregateMetric


class ResponseMetricTimeseriesPoint(BaseResponse):
    """One bucket of `ResponseMetricTimeseries` (S6, added 2026-08-02)."""

    period_start: datetime
    count: int


class ResponseMetricTimeseries(BaseResponse):
    """A single metric's day/week/month bucketed evolution (S6, added
    2026-08-02) — same count as the matching `ResponsePlatformMetrics`
    field, just grouped by `created_at` bucket instead of collapsed to
    one all-time total."""

    daily: list[ResponseMetricTimeseriesPoint]
    weekly: list[ResponseMetricTimeseriesPoint]
    monthly: list[ResponseMetricTimeseriesPoint]


class ResponsePlatformMetricsTimeseries(BaseResponse):
    """Admin dashboard time-comparison payload (S6, added 2026-08-02) —
    the same adoption signals as `ResponsePlatformMetrics`, broken down
    per period instead of flattened to an all-time total."""

    personal_decks: ResponseMetricTimeseries
    matches: ResponseMetricTimeseries


class ResponseKarnArchetypeShare(BaseResponse):
    """One archetype's share of a Karn Tablets clustering run (ADR-13)."""

    id: str
    name: str
    deck_count: int
    deck_share: float


class ResponseKarnDeckTypeDistribution(BaseResponse):
    """The S6 admin view of the latest Karn Tablets clustering run for a
    `(format, window)` — the same numbers the public Tolaria News
    `/metagame` route serves (both call
    `app.services.karn.read.metagame_snapshot`, so they cannot drift),
    plus the run's window bounds and deck total for admin oversight."""

    format: str
    window_kind: Literal["rolling_30d", "banlist_period"]
    window_label: str
    window_date_from: date
    window_date_to: date
    total_decks: int
    #: `generated_at` of the run; `None` when no run exists yet.
    generated_at: datetime | None
    archetypes: list[ResponseKarnArchetypeShare]
