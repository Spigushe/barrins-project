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

from app.models.scripture import BSSource
from app.schemas.responses_base import BaseResponse


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


class CommanderRef(BaseResponse):
    name: str
    scryfall_id: str | None
    color_identity: list[str]


class DeckCardOut(BaseResponse):
    name: str
    qty: int
    cmc: float | None
    type_line: str | None
    scryfall_id: str | None


class DeckDetail(DeckSummary):
    notes: str | None
    commanders: list[CommanderRef]
    mainboard: list[DeckCardOut]


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
