"""ORM models for the `bs_*` tables (Barrin's Scripture scraped-tournament domain).

Mirrors the shape of `barrins_scripture.schemas.scraped_object.MTGScrape`
(`apps/barrins_scripture/barrins_scripture/schemas/`) closely enough that
replaying the JSON archive (`mtg_decklist_cache`) through the ingestion
route can reconstruct these tables without a lossy transform (see
docs/project/v2.0.0-bump/t2-scraped-tournament-schema/index.md). Every
table carries a unique constraint on its natural key from that JSON shape
so a replay is an idempotent upsert, not a duplicate insert -- required by
§1.2's maintenance-window containment (a queued scrape retried after a
maintenance window must not double-insert).
"""

import enum
import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BSSource(enum.StrEnum):
    """Site a tournament was scraped from -- matches barrins_scripture's own
    `--source` CLI values, not the archive's `<source_domain>` folder names
    (`mtgo.com`/`mtgtop8.com`).
    """

    mtgo = "mtgo"
    mtgtop8 = "mtgtop8"


class BSDeckBoard(enum.StrEnum):
    """Which board a `bs_deck_cards` row belongs to."""

    mainboard = "mainboard"
    sideboard = "sideboard"


class BSTournament(Base):
    """A scraped tournament (`Tournament` in barrins_scripture's schema)."""

    __tablename__ = "bs_tournaments"
    __table_args__ = (UniqueConstraint("url", name="uq_bs_tournaments_url"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source: Mapped[BSSource] = mapped_column(
        Enum(BSSource, name="bs_source"), nullable=False
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String(120), nullable=False)
    players: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class BSDeck(Base):
    """A deck entered in a tournament (`Deck` in barrins_scripture's schema).

    `result` is a string, not an int: MTGTop8 reports ties past the top
    few places as a bracket range ("5-8", "9-16", ...), which an int
    column can't hold without discarding the upper bound -- see the
    `barrins_scripture` fix this schema was designed against
    (`schemas/deck.py`'s `result: str | None`, `parsers/mtgtop8.py`'s
    `get_deck_from_top8`).
    """

    __tablename__ = "bs_decks"
    __table_args__ = (
        UniqueConstraint("tournament_id", "anchor_uri", name="uq_bs_decks_anchor"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tournament_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bs_tournaments.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    player: Mapped[str] = mapped_column(String(255), nullable=False)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    anchor_uri: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class BSDeckCard(Base):
    """One mainboard/sideboard line of a deck (`CardEntry` in the schema)."""

    __tablename__ = "bs_deck_cards"
    __table_args__ = (
        UniqueConstraint(
            "deck_id", "board", "card_name", name="uq_bs_deck_cards_entry"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bs_decks.id", ondelete="CASCADE"),
        nullable=False,
    )
    board: Mapped[BSDeckBoard] = mapped_column(
        Enum(BSDeckBoard, name="bs_deck_board"), nullable=False
    )
    card_name: Mapped[str] = mapped_column(String(255), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class BSRound(Base):
    """A named round of a bracket (`Round` in the schema, e.g. "Quarterfinals")."""

    __tablename__ = "bs_rounds"
    __table_args__ = (
        UniqueConstraint(
            "tournament_id", "round_name", name="uq_bs_rounds_tournament_name"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tournament_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bs_tournaments.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class BSRoundMatch(Base):
    """A single pairing within a round (`Match` in the schema)."""

    __tablename__ = "bs_round_matches"
    __table_args__ = (
        UniqueConstraint(
            "round_id", "player_1", "player_2", name="uq_bs_round_matches_pairing"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    round_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bs_rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_1: Mapped[str] = mapped_column(String(255), nullable=False)
    player_2: Mapped[str] = mapped_column(String(255), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class BSStanding(Base):
    """A tournament's final standings row (`Standing` in the schema)."""

    __tablename__ = "bs_standings"
    __table_args__ = (
        UniqueConstraint(
            "tournament_id", "player", name="uq_bs_standings_tournament_player"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tournament_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bs_tournaments.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    player: Mapped[str] = mapped_column(String(255), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, nullable=False)
    omwp: Mapped[float] = mapped_column(Float, nullable=False)
    gwp: Mapped[float] = mapped_column(Float, nullable=False)
    ogwp: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
