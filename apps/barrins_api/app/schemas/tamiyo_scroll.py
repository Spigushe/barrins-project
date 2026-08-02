"""Request schemas for the Tamiyo Scroll domain (Competitive MTG Tracking)."""

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.tamiyo_scroll import (
    ArchetypeCategory,
    CardGame,
    ExpectedLevel,
    GameResult,
    SessionType,
)


class UserSettingsUpdate(BaseModel):
    """Payload for PATCH /me/settings — partial update."""

    model_config = ConfigDict(extra="forbid")

    data_shared: bool | None = None
    receive_shared_data: bool | None = None
    active_personal_deck_id: uuid.UUID | None = None


class PersonalDeckCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    # Required, no default (S10/S11) — a new deck must declare both up
    # front; the logging gate only has teeth because neither is guessed.
    game: CardGame
    category: ArchetypeCategory


class PersonalDeckPatch(BaseModel):
    """Payload for PATCH /personal-decks/{id} — partial update, owner-only.

    Rename (S1), and/or set/correct `game`/`category` (S10/S11) — whichever
    fields are provided are applied; the others are left untouched.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    game: CardGame | None = None
    category: ArchetypeCategory | None = None


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
    """Payload shared by POST and PUT /matches — full replacement.

    `decklist_version_id` is ignored on POST (the backend always stamps the
    deck's current latest version, server-side, at creation time) and
    honored on PUT (the match-edit flow allows re-pointing to a different
    version, or clearing it) — see S3.
    """

    model_config = ConfigDict(extra="forbid")

    personal_deck_id: uuid.UUID
    opponent_deck_id: uuid.UUID
    decklist_version_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    on_play: bool
    game1: GameResult | None = None
    game2: GameResult | None = None
    game3: GameResult | None = None
    opening_hand: str | None = None
    turning_point: str | None = None
    final_turn: str | None = None


class SessionCreate(BaseModel):
    """Payload for POST /sessions."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    type: SessionType
    personal_deck_id: uuid.UUID
    notes: str | None = None


class SessionPatch(BaseModel):
    """Payload for PATCH /sessions/{id} — partial update.

    `ended_at` is write-only-as-a-flag: `close`/`reopen` stamp or clear the
    current time server-side; the field itself isn't client-suppliable as
    an arbitrary timestamp — see the route. `reopen` wins if both are sent
    in the same request (not expected from the frontend, which only ever
    sends one at a time via separate actions).
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    notes: str | None = None
    close: bool | None = None
    reopen: bool | None = None


class CardTestWrite(BaseModel):
    """Payload shared by POST and PUT /card-tests — full replacement."""

    model_config = ConfigDict(extra="forbid")

    personal_deck_id: uuid.UUID
    tester: str = Field(min_length=1, max_length=120)
    card_name: str = Field(min_length=1, max_length=255)
    opponent_deck_id: uuid.UUID | None = None
    rating: int = Field(ge=1, le=5)
    notes: str | None = None


class TeamCreate(BaseModel):
    """Payload for POST /teams. Description is set later, from the team
    page (`TeamPatch`) — not at creation (S2 spec)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)


class TeamPatch(BaseModel):
    """Payload for PATCH /teams/{id} — description only, owner-only."""

    model_config = ConfigDict(extra="forbid")

    description: str | None = None


class TeamJoin(BaseModel):
    """Payload for POST /teams/join."""

    model_config = ConfigDict(extra="forbid")

    invite_code: str = Field(min_length=1, max_length=32)


class TeamDelete(BaseModel):
    """Payload for DELETE /teams/{id} — the second confirmation step:
    the owner must re-type the team's exact invite code server-side, not
    just click through a client-side confirmation dialog."""

    model_config = ConfigDict(extra="forbid")

    invite_code: str = Field(min_length=1, max_length=32)


class TeamDeckFlagCreate(BaseModel):
    """Payload for POST /teams/{id}/decks/flags — owner picks an existing
    member's deck; its *name* is what gets flagged into the rotation."""

    model_config = ConfigDict(extra="forbid")

    deck_id: uuid.UUID


class TeamDeckThreadMessageCreate(BaseModel):
    """Payload for POST .../thread/messages."""

    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=4000)
