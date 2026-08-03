"""ORM model for the `ts_card_tests` table (feedback on tested cards)."""

import enum
import uuid
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._types import JsonValue, jsonb_column


class GameResult(enum.StrEnum):
    """Result of an individual game within a BO3 match."""

    win = "win"
    loss = "loss"
    draw = "draw"


class ArchetypeCategory(enum.StrEnum):
    """Archetype category — determines the display color on the frontend."""

    aggro = "aggro"
    midrange = "midrange"
    control = "control"
    combo = "combo"


class ExpectedLevel(enum.StrEnum):
    """Expected level of a roster deck relative to the anticipated metagame."""

    as_expected = "as_expected"
    more_expected = "more_expected"
    less_expected = "less_expected"


class DecklistVersionSource(enum.StrEnum):
    """Origin of a personal decklist version."""

    manual = "manual"
    moxfield_import = "moxfield_import"


class SessionType(enum.StrEnum):
    """Kind of a tournament/training session (S9)."""

    tournament = "tournament"
    training = "training"


class CardGame(enum.StrEnum):
    """Card game a personal deck belongs to (S10) — lets ML training data
    be filtered to Magic decks only, while still keeping other games'
    decks in the database rather than discarding them."""

    magic = "magic"
    yu_gi_oh = "yu_gi_oh"
    pokemon = "pokemon"
    flesh_and_blood = "flesh_and_blood"
    one_piece = "one_piece"
    lorcana = "lorcana"
    star_wars_unlimited = "star_wars_unlimited"
    digimon = "digimon"
    cardfight_vanguard = "cardfight_vanguard"
    riftbound = "riftbound"
    other = "other"


# Instance shared between game1/game2/game3 — a single PostgreSQL type
# `ts_game_result` created by the migration, not three.
_game_result_column = Enum(GameResult, name="ts_game_result")


class TSCardTest(Base):
    """Individual feedback on a tested card (`cardTests[]` in the design).

    `tester` is a free-text string (no FK to `users`) — allows crediting
    a teammate without a Barrin account, cf.
    docs/tamiyo_scroll_tracker/00_plan_general.md, Option E.
    `opponent_deck_id` is nullable: the matchup is optional.
    """

    __tablename__ = "ts_card_tests"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_ts_card_tests_rating_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    personal_deck_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_personal_decks.id", ondelete="CASCADE"),
        nullable=True,
    )
    tester: Mapped[str] = mapped_column(String(120), nullable=False)
    card_name: Mapped[str] = mapped_column(String(255), nullable=False)
    opponent_deck_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_meta_decks.id", ondelete="SET NULL"),
        nullable=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TSMatch(Base):
    """BO3 match logged by the user (`matches[]` in the design).

    `date` is generated server-side at creation time (no date field in the
    design's "New match" form) — chronological log, no retroactive entry
    in v1.
    """

    __tablename__ = "ts_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date_type] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    personal_deck_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_personal_decks.id", ondelete="CASCADE"),
        nullable=False,
    )
    opponent_deck_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_meta_decks.id", ondelete="CASCADE"),
        nullable=False,
    )
    decklist_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_personal_decklist_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Defensive DB-level policy only — in normal operation ts_sessions rows
    # are never hard-deleted (soft-delete via archived_at), so this SET NULL
    # fallback exists for integrity, not as the primary "leaving a session"
    # mechanism. Archiving a session leaves this column untouched (S9).
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    on_play: Mapped[bool] = mapped_column(Boolean, nullable=False)
    game1: Mapped[GameResult | None] = mapped_column(_game_result_column, nullable=True)
    game2: Mapped[GameResult | None] = mapped_column(_game_result_column, nullable=True)
    game3: Mapped[GameResult | None] = mapped_column(_game_result_column, nullable=True)
    opening_hand: Mapped[str | None] = mapped_column(Text, nullable=True)
    turning_point: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_turn: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TSMetaDeck(Base):
    """Opponent roster deck ("MUR").

    Carries both the tier/archetype and the expected metagame data
    (Top 8, presence) — a single entity for the two UI sections "Roster"
    and "Expected Metagame" (`decks[]` in the design).

    Deletion = archiving (`archived_at`), never a SQL DELETE — cf.
    docs/tamiyo_scroll_tracker/00_plan_general.md, Option G.
    """

    __tablename__ = "ts_meta_decks"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[Decimal] = mapped_column(
        Numeric(2, 1), nullable=False, default=Decimal("0"), server_default="0"
    )
    category: Mapped[ArchetypeCategory] = mapped_column(
        Enum(ArchetypeCategory, name="ts_archetype_category"), nullable=False
    )
    # Nullable, no backfill — inherited automatically (never user-picked)
    # from whichever personal deck's game a meta deck is created against
    # (match-logging "create opponent" flow, or the active personal deck
    # on the roster quick-add form). A soft data tag for ML export
    # filtering, not an enforced constraint: a meta deck can still be used
    # against a personal deck of a different game, nothing blocks it.
    game: Mapped[CardGame | None] = mapped_column(
        Enum(CardGame, name="ts_card_game", create_type=False), nullable=True
    )
    decklist_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    top8: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    presence: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    expected: Mapped[ExpectedLevel] = mapped_column(
        Enum(ExpectedLevel, name="ts_expected_level"),
        nullable=False,
        default=ExpectedLevel.as_expected,
        server_default=ExpectedLevel.as_expected.value,
    )
    tests_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TSPersonalDeck(Base):
    """A user's personal deck (`myDecks[]` in the design).

    Deletion = archiving (`archived_at`), never a SQL DELETE — cf.
    docs/tamiyo_scroll_tracker/00_plan_general.md, Option G. Preserves
    the history of associated matches/versions for future data science.
    """

    __tablename__ = "ts_personal_decks"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nullable, no default/backfill (S10/S11) — a deck must declare both
    # explicitly at creation; historical decks read NULL until PATCHed.
    # Logging/editing a match on a NULL-game or NULL-category deck is
    # rejected by `_validate_match_refs` (api/tamiyo_scroll/matches.py).
    game: Mapped[CardGame | None] = mapped_column(
        Enum(CardGame, name="ts_card_game"), nullable=True
    )
    category: Mapped[ArchetypeCategory | None] = mapped_column(
        Enum(ArchetypeCategory, name="ts_archetype_category", create_type=False),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TSPersonalDecklistVersion(Base):
    """Versioned decklist version of a personal deck (`decklistVersions[]`).

    Real Moxfield scraping is out of scope for v1 — `moxfield_import`
    produces placeholder content mentioning the provided URL (cf. plan, Non-goals).
    """

    __tablename__ = "ts_personal_decklist_versions"
    __table_args__ = (
        UniqueConstraint("personal_deck_id", "version", name="uq_ts_decklist_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    personal_deck_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_personal_decks.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[DecklistVersionSource] = mapped_column(
        Enum(DecklistVersionSource, name="ts_decklist_version_source"),
        nullable=False,
        default=DecklistVersionSource.manual,
        server_default=DecklistVersionSource.manual.value,
    )
    # Full, unmodified Moxfield API response for this version — only ever
    # set when source == moxfield_import (NULL for manual entries). Kept
    # verbatim (not just the fields used today) so later features can read
    # more of it without a second Moxfield call; see S3's staleness check.
    moxfield_data: Mapped[JsonValue | None] = jsonb_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TSUserSettings(Base):
    """A user's Tamiyo Scroll preferences (1 row/account, created on demand).

    Separate from the `User` model (shared Barrin identity) because these
    preferences are specific to the Tamiyo Scroll tracker — cf.
    docs/tamiyo_scroll_tracker/00_plan_general.md, Option D.

    `data_shared` defaults `True` for newly-created settings rows (per the
    user, 2026-07-30) — sharing is opt-out; receiving stays opt-in
    (`receive_shared_data` defaults `False`). Existing rows are
    unaffected — this is a default for new accounts only, never a
    retroactive opt-in for users who didn't choose it.
    """

    __tablename__ = "ts_user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    data_shared: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    receive_shared_data: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    active_personal_deck_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_personal_decks.id", ondelete="SET NULL"),
        nullable=True,
    )


class TSSession(Base):
    """A named tournament/training session, grouping matches for one deck (S9).

    Matches-only for v1 — no `ts_card_tests.session_id`, cf. S9's resolved
    open question 1: version-scoped card-test analysis is already
    extrapolable from `ts_personal_decklist_versions` without a session
    concept. Deletion = archiving (`archived_at`), same soft-delete pattern
    as `TSPersonalDeck`/`TSMetaDeck` — matches keep their `session_id`
    unchanged when their session is archived.
    """

    __tablename__ = "ts_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    personal_deck_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_personal_decks.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[SessionType] = mapped_column(
        Enum(SessionType, name="ts_session_type"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TSTeam(Base):
    """A team of players sharing decks/reports (S2, "Team Decks").

    Deletion is a hard `DELETE`, unlike every other `ts_*` entity's
    archive-only soft-delete — nothing team-specific needs retaining once
    dissolved (a deck's own match/test history lives on
    `ts_personal_decks`/`ts_matches`, untouched; see
    `TSPersonalDeck.shared_team_id`'s `ON DELETE SET NULL`).
    `owner_id` is `RESTRICT` (not `CASCADE`): a team always needs an
    explicit owner, so deleting that user's account while still owning a
    team must fail loudly rather than orphan the team.
    """

    __tablename__ = "ts_teams"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    invite_code: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TSTeamMember(Base):
    """Membership row (`team_id`, `user_id`).

    Composite PK, no `UNIQUE(user_id)` — multi-team membership is allowed
    (S2 spec, resolved 2026-07-30).
    """

    __tablename__ = "ts_team_members"

    team_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_teams.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TSTeamDeckFlag(Base):
    """A deck *name* flagged into a team's testing rotation (S2, revised
    2026-08-01).

    Sharing is name-based, not per-deck-instance — mirrors
    `sharing_merge.py`'s existing "matched by exact name" convention.
    Flagging one member's "King T'Challa" auto-includes every other team
    member's own "King T'Challa", present or future, with no per-deck
    action needed on their part. `name_key` is the case/whitespace-
    normalized form used for matching and uniqueness; `deck_name` keeps
    the original casing for display (whichever deck the owner picked when
    flagging).
    """

    __tablename__ = "ts_team_deck_flags"
    __table_args__ = (
        UniqueConstraint("team_id", "name_key", name="uq_ts_team_deck_flag"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    deck_name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_key: Mapped[str] = mapped_column(String(255), nullable=False)
    flagged_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TSTeamDeckThread(Base):
    """A discussion thread enabled for one *deck name* within a team.

    Name-keyed (like `TSTeamDeckFlag`), not tied to one physical deck row
    — the thread is "about the King T'Challa matchup", shared by whoever
    in the team owns a same-named deck, not about one specific person's
    copy of it.
    """

    __tablename__ = "ts_team_deck_threads"
    __table_args__ = (
        UniqueConstraint("team_id", "name_key", name="uq_ts_team_deck_thread"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    name_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TSTeamDeckMessage(Base):
    """A single chat-like message within a `TSTeamDeckThread`."""

    __tablename__ = "ts_team_deck_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_team_deck_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TSInviteAttempt(Base):
    """Per-user sliding-window rate-limit state for invite-code redemption.

    Mirrors `EmailVerification`'s DB-backed cooldown/attempts pattern
    (no Redis) — `last_attempt_at` enforces the 1-per-5-seconds rule,
    `window_started_at`/`attempts_in_window` the 5-per-minute rule. One
    row per user, upserted on every attempt.
    """

    __tablename__ = "ts_invite_attempts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    attempts_in_window: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
