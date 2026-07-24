"""Add Tamiyo Scroll tracker tables (ts_*)

Revision ID: ef2a570b4f4f
Revises: bef3351513a5
Create Date: 2026-07-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ef2a570b4f4f"
down_revision: str | Sequence[str] | None = "bef3351513a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Creates the Tamiyo Scroll domain: personal decks, opponent roster, match

    log, tested card feedback, user preferences.
    """
    op.create_table(
        "ts_meta_decks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tier", sa.Numeric(2, 1), nullable=False, server_default="0"),
        sa.Column(
            "category",
            sa.Enum(
                "aggro", "midrange", "control", "combo", name="ts_archetype_category"
            ),
            nullable=False,
        ),
        sa.Column("decklist_notes", sa.Text, nullable=True),
        sa.Column("top8", sa.Integer, nullable=False, server_default="0"),
        sa.Column("presence", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "expected",
            sa.Enum(
                "as_expected",
                "more_expected",
                "less_expected",
                name="ts_expected_level",
            ),
            nullable=False,
            server_default="as_expected",
        ),
        sa.Column("tests_status", sa.Text, nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "ts_personal_decks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "ts_card_tests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tester", sa.String(120), nullable=False),
        sa.Column("card_name", sa.String(255), nullable=False),
        sa.Column(
            "opponent_deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_meta_decks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "personal_deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_personal_decks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_ts_card_tests_rating_range"),
    )

    op.create_table(
        "ts_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "date",
            sa.Date,
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
        sa.Column(
            "personal_deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_personal_decks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opponent_deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_meta_decks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("on_play", sa.Boolean, nullable=False),
        sa.Column(
            "game1", sa.Enum("win", "loss", "draw", name="ts_game_result"), nullable=True
        ),
        sa.Column(
            "game2",
            sa.Enum("win", "loss", "draw", name="ts_game_result", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "game3",
            sa.Enum("win", "loss", "draw", name="ts_game_result", create_type=False),
            nullable=True,
        ),
        sa.Column("opening_hand", sa.Text, nullable=True),
        sa.Column("turning_point", sa.Text, nullable=True),
        sa.Column("final_turn", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "ts_personal_decklist_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "personal_deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_personal_decks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "source",
            sa.Enum("manual", "moxfield_import", name="ts_decklist_version_source"),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("personal_deck_id", "version", name="uq_ts_decklist_version"),
    )

    op.create_table(
        "ts_user_settings",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("data_shared", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "active_personal_deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_personal_decks.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drops the Tamiyo Scroll domain (reverse order of FK dependencies)."""
    op.drop_table("ts_user_settings")
    op.drop_table("ts_personal_decklist_versions")
    op.drop_table("ts_matches")
    op.drop_table("ts_card_tests")
    op.drop_table("ts_personal_decks")
    op.drop_table("ts_meta_decks")
    sa.Enum(name="ts_game_result").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ts_archetype_category").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ts_expected_level").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ts_decklist_version_source").drop(op.get_bind(), checkfirst=True)
