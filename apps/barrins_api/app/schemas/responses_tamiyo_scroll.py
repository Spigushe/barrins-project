"""Response schemas for the Tamiyo Scroll domain (Competitive MTG Tracking)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import computed_field

from app.models.tamiyo_scroll import (
    ArchetypeCategory,
    DecklistVersionSource,
    ExpectedLevel,
    GameResult,
)
from app.schemas.responses_base import BaseResponse


class ResponseUserSettings(BaseResponse):
    data_shared: bool
    receive_shared_data: bool
    active_personal_deck_id: uuid.UUID | None


class ResponsePersonalDeck(BaseResponse):
    id: uuid.UUID
    name: str
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
