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
        default=False,
        server_default="false",
    )
    active_personal_deck_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ts_personal_decks.id", ondelete="SET NULL"),
        nullable=True,
    )
