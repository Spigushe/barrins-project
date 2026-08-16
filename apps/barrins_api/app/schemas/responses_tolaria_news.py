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


#: Mirrors `dc_calendar.windowing.WindowKind` plus the "all_time" mode that
#: package doesn't itself have a concept of (it only resolves *a* window,
#: never "every window there's ever been") -- see
#: `app/services/tolaria_news/decks.py::list_trending_commanders`.
TrendWindowMode = Literal["rolling_30d", "banlist_period", "all_time"]


class WindowOut(BaseResponse):
    kind: TrendWindowMode
    label: str
    date_from: date_type
    date_to: date_type


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
