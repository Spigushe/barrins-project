"""Response schemas for the Tolaria News BFF (public tournament data).

Wrapped in `Envelope`/`Meta`/`Page` (`{data, meta, page?}`) -- a deliberate
divergence from Tamiyo Scroll's bare-response style, confirmed during T4's
planning: Tolaria News is public/cacheable data where staleness
(`source_synced_at`) is a user-visible concern Tamiyo Scroll's personal
data doesn't have. See docs/content/back/barrins_api/bff/tolaria_news.md.
"""

import uuid
from datetime import date as date_type
from datetime import datetime
from typing import Literal

from app.models.scripture import BSSource
from app.schemas.responses_base import BaseResponse
from app.services.decklist_sort import DecklistCardCategory


class Meta(BaseResponse):
    generated_at: datetime
    #: Most recent ingested-row timestamp across `bs_*` -- a proxy for
    #: "how fresh is this data", not a true last-sweep-run log (no such
    #: table exists yet). None if `bs_*` is empty.
    source_synced_at: datetime | None


class Page(BaseResponse):
    next_cursor: str | None
    limit: int


class Envelope[T](BaseResponse):
    data: T
    meta: Meta
    page: Page | None = None


class TournamentSummary(BaseResponse):
    id: uuid.UUID
    source: BSSource
    date: date_type
    name: str
    url: str
    format: str
    players: int


class TournamentDetail(TournamentSummary):
    deck_count: int
    standing_count: int


class DeckSummary(BaseResponse):
    id: uuid.UUID
    tournament_id: uuid.UUID
    date: date_type
    player: str
    result: str | None
    anchor_uri: str


class DeckListItem(DeckSummary):
    """One row of the global cross-tournament decklist index
    (`GET /decks`) -- carries just enough tournament context to be
    meaningful on its own, since a global list isn't scoped to a single
    tournament page the way `DeckSummary` normally is."""

    tournament_name: str
    tournament_source: BSSource


class CommanderRef(BaseResponse):
    name: str
    scryfall_id: str | None
    color_identity: list[str]
    mana_cost: str | None
    text: str | None
    keywords: list[str]


class TournamentDeckSummary(DeckSummary):
    """One row of a single tournament's deck list (`GET
    /tournaments/{id}/decks`) -- adds `commanders` on top of `DeckSummary`,
    kept off that base class (and off `DeckListItem`) so the global `/decks`
    index and single-deck detail responses stay unchanged."""

    commanders: list[CommanderRef]


class DeckCardOut(BaseResponse):
    name: str
    qty: int
    cmc: float | None
    type_line: str | None
    scryfall_id: str | None
    mana_cost: str | None
    text: str | None
    keywords: list[str]


class StapleRow(BaseResponse):
    name: str
    cmc: float | None
    type_line: str | None
    scryfall_id: str | None
    mana_cost: str | None
    text: str | None
    keywords: list[str]
    deck_count: int
    #: `deck_count / decks_considered * 100`, rounded to one decimal place.
    percentage: float


class StaplesResponse(BaseResponse):
    """A metagame-wide "staples" snapshot -- card frequency pooled across
    every qualifying tournament in `[date_from, date_to]`, not one
    tournament's own decks (see
    `app.services.tolaria_news.decks.list_staples`'s docstring for the
    tournament-pooling rule)."""

    date_from: date_type
    date_to: date_type
    #: Set when the pool was narrowed to decks piloting this commander
    #: (see `app.services.tolaria_news.decks.list_staples`'s `commander`
    #: param); `None` for the metagame-wide view.
    commander: str | None = None
    tournaments_considered: int
    decks_considered: int
    #: Minimum `StapleRow.percentage` a card had to reach to be included in
    #: `rows` -- normally 65.0, or the softer 45.0 fallback if 65.0 would
    #: have left `rows` empty for this window (see
    #: `app.services.tolaria_news.decks.list_staples`). Reported (not
    #: hardcoded by the frontend) so the empty-state message always names
    #: the floor that was actually applied.
    min_percentage: float
    #: Up to 60 rows meeting `min_percentage`, ranked descending by
    #: `deck_count`.
    rows: list[StapleRow]


class DeckCardTypeGroup(BaseResponse):
    """One type-ordered section of `mainboard` (e.g. "creature" with its
    cards) -- Duel Commander display order (planeswalker, battle, creature,
    instant, sorcery, artifact, enchantment, land, other), each sorted by
    mana value then name. `category` is a stable machine-readable key, not
    a display label -- pluralization/translation is the frontend's job."""

    category: DecklistCardCategory
    count: int
    cards: list[DeckCardOut]


class DeckDetail(DeckSummary):
    notes: str | None
    commanders: list[CommanderRef]
    mainboard: list[DeckCardTypeGroup]


class StandingRow(BaseResponse):
    rank: int
    player: str
    points: int
    wins: int
    losses: int
    draws: int
    omwp: float
    gwp: float
    ogwp: float


class RoundMatchOut(BaseResponse):
    player_1: str
    player_2: str
    result: str


class RoundOut(BaseResponse):
    round_name: str
    matches: list[RoundMatchOut]


#: Mirrors `dc_calendar.windowing.WindowKind` plus two modes that package
#: doesn't itself have a concept of (it only resolves *a* window, given a
#: kind and a reference date): "all_time" (every window there's ever
#: been) and "custom" (a caller-supplied date range, e.g. the frontend's
#: "20-life decks" preset or its date-picker range) -- see
#: `app/services/tolaria_news/decks.py::list_trending_commanders`.
TrendWindowMode = Literal["rolling_30d", "banlist_period", "all_time", "custom"]


class WindowOut(BaseResponse):
    kind: TrendWindowMode
    label: str
    date_from: date_type
    date_to: date_type


class TelemetryResponse(BaseResponse):
    """Bottom-rail data: the currently *effective* banlist season (not
    necessarily the calendar-date period -- see
    `dc_calendar.windowing.effective_banlist_period`), its `<year>-<number>`
    label components, and when the next one takes effect."""

    season: WindowOut
    #: 1-6, the season's position within `season_year` -- see
    #: `dc_calendar.windowing.banlist_period_number`.
    season_year: int
    season_number: int
    next_banlist_at: datetime


class CommanderTrendPoint(BaseResponse):
    date_from: date_type
    date_to: date_type
    #: `None` (not `0`) when no deck in this bucket ran the commander --
    #: lets the frontend sparkline render a gap instead of dipping to zero.
    deck_count: int | None


class CommanderTrendSeries(BaseResponse):
    #: 1 entry (solo commander) or 2 (a partner pair), always resolved via
    #: the same `CommanderRef` shape `DeckDetail` uses.
    commanders: list[CommanderRef]
    total_deck_count: int
    points: list[CommanderTrendPoint]


class CommanderTrendsResponse(BaseResponse):
    window: WindowOut
    #: Up to 10 entries, ranked descending by `total_deck_count`.
    series: list[CommanderTrendSeries]


class StatsResponse(BaseResponse):
    """Landing-page headline counts (`GET /stats`) -- Duel Commander
    tournaments/decks recorded from `EARLIEST_RELEVANT_DATE` onward, same
    scope every other Tolaria News endpoint defaults to (see
    `app.services.tolaria_news.decks.EARLIEST_RELEVANT_DATE`)."""

    tournaments_count: int
    decks_count: int


# --- Karn Tablets metagame clustering (ADR-13) ---------------------------
# Backed by the `kt_*` tables `apps/karn_tablets` pushes into. `format`
# defaults to "Duel Commander" (the only populated value in v1); the param
# ships from v1 by user decision, superseding ADR-13's "no format param"
# note -- retrofitting a param onto a public contract later is worse.


#: `deck_share` movement of an archetype from the previous run of the
#: same `(format, window_kind)` to the latest one:
#: - "rising"/"falling" -- `deck_share` changed by more than 10% of its
#:   previous value (a relative band, so a 2%-share archetype and a
#:   20%-share one are held to proportional thresholds);
#: - "stable" -- present in both runs, within that band;
#: - "new" -- had a cluster in the latest run but none in the previous one.
#: When there is no previous run at all, every archetype is "stable" with
#: a `None` delta -- there is nothing to compare against, not a claim of
#: stability.
ArchetypeMomentum = Literal["rising", "falling", "stable", "new"]


class CardRef(BaseResponse):
    """A card name plus its resolved Scryfall id (`None` if unresolved),
    enough for the frontend's card-image hover."""

    name: str
    scryfall_id: str | None


class MetagameArchetype(BaseResponse):
    #: Stable across runs (`kt_archetypes.id` as a string) -- unlike a
    #: run's raw cluster integer.
    id: str
    name: str
    #: The archetype's commander card(s): 1 for a solo commander, 2 for a
    #: partner pair, empty for data with no commander. `name` can diverge
    #: (an admin rename, or a "#2" build split) -- these are the actual
    #: underlying cards, for the image hover.
    commanders: list[CardRef]
    deck_count: int
    #: `deck_count / run total`, in [0, 1].
    deck_share: float
    #: `deck_share` (latest run) minus `deck_share` (previous run) for this
    #: archetype identity. `None` when there is no previous run, or the
    #: archetype is absent from it (`momentum == "new"`).
    deck_share_delta: float | None
    #: `deck_share_delta` bucketed -- see `ArchetypeMomentum`. The band
    #: threshold is a backend-owned domain rule, not a frontend concern
    #: (Constitution 4.1/4.2).
    momentum: ArchetypeMomentum


class RepresentativeCard(BaseResponse):
    name: str
    qty: int
    #: `None` if the name doesn't resolve in `mj_cards`.
    scryfall_id: str | None
    #: Resolved against `mj_cards` (`type_line`); `False` for a name that
    #: doesn't resolve.
    is_land: bool
    #: `False` only for a land at or above the field-prevalence threshold
    #: across the latest run's archetypes (a metagame-wide staple, not
    #: archetype-defining). Always `True` for non-lands and for a land
    #: unique to a single archetype. The frontend's "signature cards" view
    #: renders only `is_signature` cards -- the threshold is a
    #: backend-owned rule (Constitution 4.1/4.2).
    is_signature: bool


class MetagameArchetypeDetail(MetagameArchetype):
    """`GET /archetypes` row -- adds the aggregated representative
    mainboard so the response isn't a pure duplicate of `/metagame`."""

    representative_mainboard: list[RepresentativeCard]


class MetagameSnapshot(BaseResponse):
    format: str
    window: WindowOut
    #: The adjacent windows of the same kind, oldest→newest, for the
    #: frontend's prev/next stepper. `null` at either end. Navigate by
    #: re-requesting with `?at=<window.label>`.
    previous_window: WindowOut | None
    next_window: WindowOut | None
    #: Largest archetype first.
    archetypes: list[MetagameArchetype]


class ArchetypeDetailPage(BaseResponse):
    """`GET /archetypes` payload -- the same window framing as
    `MetagameSnapshot` (so the page can carry the prev/next stepper) plus
    the detail rows. The list is a `?limit=&cursor=` slice; the outer
    `Envelope.page` carries `next_cursor`."""

    format: str
    window: WindowOut
    previous_window: WindowOut | None
    next_window: WindowOut | None
    archetypes: list[MetagameArchetypeDetail]


class ArchetypeTrendPoint(BaseResponse):
    window: WindowOut
    #: `None` (not `0`) for a run in which this archetype had no cluster
    #: -- lets a sparkline render a gap.
    deck_share: float | None


class ArchetypeTrend(BaseResponse):
    archetype_id: str
    archetype_name: str
    #: Same as `MetagameArchetype.commanders` -- for the card-image hover
    #: on the trends legend / small-multiples titles.
    commanders: list[CardRef]
    #: Chronological, one point per recent run of this window mode.
    points: list[ArchetypeTrendPoint]
