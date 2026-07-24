"""Request schemas for the Tamiyo Scroll domain (Competitive MTG Tracking)."""

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.tamiyo_scroll import ArchetypeCategory, ExpectedLevel, GameResult


class UserSettingsUpdate(BaseModel):
    """Payload for PATCH /me/settings — partial update."""

    model_config = ConfigDict(extra="forbid")

    data_shared: bool | None = None
    active_personal_deck_id: uuid.UUID | None = None


class PersonalDeckCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)


class DecklistVersionCreate(BaseModel):
    """Payload for POST .../versions — manual entry of the decklist text."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)


class MoxfieldImportRequest(BaseModel):
    """Payload for POST .../versions/import-moxfield.

    v1: no real scraping — the created version's content is a
    placeholder mentioning the provided URL (cf. plan, Non-goals).
    """

    model_config = ConfigDict(extra="forbid")

    moxfield_url: str = Field(min_length=1)


class MetaDeckWrite(BaseModel):
    """Payload shared by POST and PUT /meta-decks — full replacement."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    tier: float = Field(ge=0, le=3, multiple_of=0.5)
    category: ArchetypeCategory
    decklist_notes: str | None = None
    top8: int = Field(default=0, ge=0)
    presence: int = Field(default=0, ge=0)
    expected: ExpectedLevel = ExpectedLevel.as_expected
    tests_status: str | None = None


class MatchWrite(BaseModel):
    """Payload shared by POST and PUT /matches — full replacement."""

    model_config = ConfigDict(extra="forbid")

    personal_deck_id: uuid.UUID
    opponent_deck_id: uuid.UUID
    on_play: bool
    game1: GameResult | None = None
    game2: GameResult | None = None
    game3: GameResult | None = None
    opening_hand: str | None = None
    turning_point: str | None = None
    final_turn: str | None = None


class CardTestWrite(BaseModel):
    """Payload shared by POST and PUT /card-tests — full replacement."""

    model_config = ConfigDict(extra="forbid")

    personal_deck_id: uuid.UUID
    tester: str = Field(min_length=1, max_length=120)
    card_name: str = Field(min_length=1, max_length=255)
    opponent_deck_id: uuid.UUID | None = None
    rating: int = Field(ge=1, le=5)
    notes: str | None = None
