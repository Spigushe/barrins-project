"""Add Barrin's Scripture scraped-tournament tables (bs_*)

Revision ID: 49c50188ee55
Revises: ef2a570b4f4f
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "49c50188ee55"
down_revision: str | Sequence[str] | None = "ef2a570b4f4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Creates the Barrin's Scripture domain: tournaments, decks, deck cards,

    rounds, round matches, standings. Mirrors barrins_scripture's MTGScrape
    schema closely enough that replaying the JSON archive can reconstruct
    these tables; every table has a unique constraint on its natural key
    from that JSON so a replay is an idempotent upsert.
    """
    op.create_table(
        "bs_tournaments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source",
            sa.Enum("mtgo", "mtgtop8", name="bs_source"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("format", sa.String(120), nullable=False),
        sa.Column("players", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("url", name="uq_bs_tournaments_url"),
    )

    op.create_table(
        "bs_decks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tournament_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bs_tournaments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("player", sa.String(255), nullable=False),
        # String, not Integer: MTGTop8 reports ties past the top few places
        # as a bracket range ("5-8", "9-16", ...), not a single placement.
        sa.Column("result", sa.String(16), nullable=True),
        sa.Column("anchor_uri", sa.Text, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tournament_id", "anchor_uri", name="uq_bs_decks_anchor"),
    )

    op.create_table(
        "bs_deck_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bs_decks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "board",
            sa.Enum("mainboard", "sideboard", name="bs_deck_board"),
            nullable=False,
        ),
        sa.Column("card_name", sa.String(255), nullable=False),
        sa.Column("count", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "deck_id", "board", "card_name", name="uq_bs_deck_cards_entry"
        ),
    )

    op.create_table(
        "bs_rounds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tournament_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bs_tournaments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("round_name", sa.String(120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tournament_id", "round_name", name="uq_bs_rounds_tournament_name"
        ),
    )

    op.create_table(
        "bs_round_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "round_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bs_rounds.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("player_1", sa.String(255), nullable=False),
        sa.Column("player_2", sa.String(255), nullable=False),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "round_id", "player_1", "player_2", name="uq_bs_round_matches_pairing"
        ),
    )

    op.create_table(
        "bs_standings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tournament_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bs_tournaments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("player", sa.String(255), nullable=False),
        sa.Column("points", sa.Integer, nullable=False),
        sa.Column("wins", sa.Integer, nullable=False),
        sa.Column("losses", sa.Integer, nullable=False),
        sa.Column("draws", sa.Integer, nullable=False),
        sa.Column("omwp", sa.Float, nullable=False),
        sa.Column("gwp", sa.Float, nullable=False),
        sa.Column("ogwp", sa.Float, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tournament_id", "player", name="uq_bs_standings_tournament_player"
        ),
    )


def downgrade() -> None:
    """Drops the Barrin's Scripture domain (reverse order of FK dependencies)."""
    op.drop_table("bs_standings")
    op.drop_table("bs_round_matches")
    op.drop_table("bs_rounds")
    op.drop_table("bs_deck_cards")
    op.drop_table("bs_decks")
    op.drop_table("bs_tournaments")
    sa.Enum(name="bs_deck_board").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="bs_source").drop(op.get_bind(), checkfirst=True)
