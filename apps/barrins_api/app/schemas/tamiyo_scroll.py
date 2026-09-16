"""Request schemas for the Tamiyo Scroll domain (Competitive MTG Tracking)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.tamiyo_scroll import (
    ArchetypeCategory,
    CardGame,
    ExpectedLevel,
    GameResult,
    MetagameRosterScope,
    SessionType,
)


class UserSettingsUpdate(BaseModel):
    """Payload for PATCH /me/settings — partial update."""

    model_config = ConfigDict(extra="forbid")

    data_shared: bool | None = None
    receive_shared_data: bool | None = None
    active_personal_deck_id: uuid.UUID | None = None
    metagame_roster_scope: MetagameRosterScope | None = None
    auto_archive_stale_sessions: bool | None = None
    auto_archive_decklist_version_gap: int | None = Field(default=None, ge=1)
    show_decklist_version_diff: bool | None = None
    validate_removed_card_in_decklist: bool | None = None
    validate_added_card_exists: bool | None = None
    show_decklist_change_log: bool | None = None


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
    """Payload shared by POST and PUT /meta-decks — full replacement.

    `personal_deck_id` is required (F10) — every roster row now carries a
    real, owner-validated FK to the personal deck it was created against;
    it's a stored value, not a soft creation-time hint. Ignored on
    update — a meta deck's owning deck, once set, isn't reassigned by a
    later edit (moving it is a data-migration concern, not a form field).
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    tier: float = Field(ge=0, le=3, multiple_of=0.5)
    category: ArchetypeCategory
    decklist_notes: str | None = None
    top8: int = Field(default=0, ge=0)
    presence: int = Field(default=0, ge=0)
    expected: ExpectedLevel = ExpectedLevel.as_expected
    tests_status: str | None = None
    personal_deck_id: uuid.UUID


class MatchEventWrite(BaseModel):
    """One logged mulligan or misplay (#123/#124, D2's second amendment).

    The comment is per-*event*, not per-game-x-side: each individual
    mulligan/misplay is its own entry with its own optional comment (game
    state, decision, cards in hand) — there is no separate per-game-x-side
    note field anymore. Position within its list (assigned server-side as
    the list index + 1) is what `TSMatchGameEvent.sequence` upserts
    against — see `app/api/tamiyo_scroll/matches.py::_apply_payload`.
    """

    model_config = ConfigDict(extra="forbid")

    comment: str | None = None


class MatchGameWrite(BaseModel):
    """One game within `MatchWrite.games` (#123/#124, full normalization).

    Replaces the old flat `on_play`/`game{N}` fields on `MatchWrite` — one
    entry per played game, `game_number` 1-3.

    `player_mulligans`/`opponent_mulligans`/`player_misplays`/
    `opponent_misplays` are lists of individual logged events (D2's second
    amendment) — gated: only a `moderator`+ caller may submit a non-empty
    list for any of them (D7) — enforced in `app/api/tamiyo_scroll/
    matches.py::_apply_payload`, not here, since that check needs the
    caller's role, not just the payload shape. Each list is a full
    replacement of that side/kind's event log, upserted by position
    (`_apply_payload`), same "full replacement" convention as this
    payload's other list, `MatchWrite.games` itself.
    """

    model_config = ConfigDict(extra="forbid")

    game_number: int = Field(ge=1, le=3)
    on_play: bool | None = None
    result: GameResult | None = None
    # London mulligan (Duel Commander, D4): hand size is `7 - mulligans`,
    # so more than 7 mulligans in one game can't happen.
    player_mulligans: list[MatchEventWrite] = Field(default_factory=list, max_length=7)
    opponent_mulligans: list[MatchEventWrite] = Field(
        default_factory=list, max_length=7
    )
    # No hard game-rule cap on misplays — a generous sanity bound instead.
    player_misplays: list[MatchEventWrite] = Field(default_factory=list, max_length=50)
    opponent_misplays: list[MatchEventWrite] = Field(
        default_factory=list, max_length=50
    )


class MatchWrite(BaseModel):
    """Payload shared by POST and PUT /matches — full replacement.

    `decklist_version_id` is ignored on POST (the backend always stamps the
    deck's current latest version, server-side, at creation time) and
    honored on PUT (the match-edit flow allows re-pointing to a different
    version, or clearing it) — see S3.

    `games` (#123/#124) replaces the old flat `on_play`/`game1`/`game2`/
    `game3` fields — full replacement of the match's per-game log, same
    convention as this payload's other fields: a game number missing from
    `games` is deleted from the match, an included one is upserted.
    """

    model_config = ConfigDict(extra="forbid")

    personal_deck_id: uuid.UUID
    opponent_deck_id: uuid.UUID
    decklist_version_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    games: list[MatchGameWrite] = Field(default_factory=list)
    opening_hand: str | None = None
    turning_point: str | None = None
    final_turn: str | None = None

    @field_validator("games")
    @classmethod
    def _unique_game_numbers(cls, games: list[MatchGameWrite]) -> list[MatchGameWrite]:
        numbers = [g.game_number for g in games]
        if len(numbers) != len(set(numbers)):
            raise ValueError("duplicate_game_number")
        return games


class SessionCreate(BaseModel):
    """Payload for POST /sessions.

    `started_at`/`ended_at`/`hue` mirror `SessionPatch`'s fields of the same
    name (S14: freely client-suppliable, no workflow meaning) — the create
    form reuses the same field set as edit so a session can be fully filled
    in at creation instead of requiring a follow-up PATCH.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    type: SessionType
    personal_deck_id: uuid.UUID
    notes: str | None = None
    location: str | None = Field(default=None, max_length=255)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    hue: int | None = Field(default=None, ge=0, le=359)


class SessionPatch(BaseModel):
    """Payload for PATCH /sessions/{id} — partial update.

    `close`/`reopen` stamp or clear `closed_at` (the Close/Reopen workflow
    state) with the current server time — that field itself isn't
    client-suppliable as an arbitrary timestamp. `reopen` wins if both are
    sent in the same request (not expected from the frontend, which only
    ever sends one at a time via separate actions).

    `started_at`/`ended_at` are unrelated to `close`/`reopen` (S14,
    "track separately") — freely client-suppliable timestamps with no
    workflow meaning, purely "when did this session actually start/end."

    `restore` clears `archived_at`, mirroring `close`/`reopen`'s shape.

    `type` (GitHub issue #126) is editable after creation — a session
    mislabeled tournament/training at creation had no correction path
    before this. `None` leaves it unchanged; there is no "clear" state
    (a session always has a type).
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: SessionType | None = None
    notes: str | None = None
    location: str | None = Field(default=None, max_length=255)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    hue: int | None = Field(default=None, ge=0, le=359)
    close: bool | None = None
    reopen: bool | None = None
    restore: bool | None = None


class CardTestWrite(BaseModel):
    """Payload shared by POST and PUT /card-tests — full replacement.

    S17: narrowed to the card log's own identity fields — the matchup/
    rating fields that used to live here moved to
    `CardTestEvaluationWrite`.
    """

    model_config = ConfigDict(extra="forbid")

    personal_deck_id: uuid.UUID
    removed_card_name: str = Field(min_length=1, max_length=255)
    added_card_name: str = Field(min_length=1, max_length=255)
    notes: str | None = None


class CardTestEvaluationWrite(BaseModel):
    """Payload shared by POST and PUT /card-tests/{test_id}/evaluations —
    full replacement (S17). `opponent_deck_id` is required here, unlike
    the pre-S17 flat `CardTestWrite` field it replaces: an evaluation is
    specifically a match-up.
    """

    model_config = ConfigDict(extra="forbid")

    opponent_deck_id: uuid.UUID
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
