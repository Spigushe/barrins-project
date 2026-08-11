"""Add MTGJSON sets/cards reference tables (S8)

Revision ID: 7d3f9a1c5e26
Revises: 3e8e2a2dc724
Create Date: 2026-08-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d3f9a1c5e26"
down_revision: str | Sequence[str] | None = "3e8e2a2dc724"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Creates the MTGJSON reference domain: sets, cards.

    Primary keys are MTGJSON's own natural identifiers (`sets.code`,
    `cards.id` = MTGJSON's per-printing-per-face uuid) rather than a
    generated surrogate -- see app/models/mtgjson.py's module docstring.
    """
    op.create_table(
        "sets",
        sa.Column("code", sa.String(8), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("release_date", sa.Date, nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("block", sa.String(255), nullable=True),
        sa.Column("base_set_size", sa.Integer, nullable=False),
        sa.Column("total_set_size", sa.Integer, nullable=False),
        sa.Column("keyrune_code", sa.String(16), nullable=False),
        sa.Column(
            "is_online_only",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "set_code",
            sa.String(8),
            sa.ForeignKey("sets.code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("face_name", sa.String(255), nullable=True),
        sa.Column("side", sa.String(1), nullable=True),
        sa.Column(
            "layout", sa.String(32), nullable=False, server_default="normal"
        ),
        sa.Column(
            "other_face_ids",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("type_line", sa.Text, nullable=False),
        sa.Column(
            "types", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"
        ),
        sa.Column(
            "supertypes",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "subtypes",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("mana_cost", sa.String(64), nullable=True),
        sa.Column("mana_value", sa.Float, nullable=True),
        sa.Column(
            "colors", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"
        ),
        sa.Column(
            "color_identity",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("rarity", sa.String(32), nullable=False),
        sa.Column("number", sa.String(16), nullable=False),
        sa.Column("scryfall_id", sa.String(36), nullable=True),
        sa.Column("scryfall_oracle_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_cards_set_code", "cards", ["set_code"])
    op.create_index("ix_cards_name", "cards", ["name"])
    op.create_index("ix_cards_face_name", "cards", ["face_name"])


def downgrade() -> None:
    """Drops the MTGJSON reference domain (reverse order of FK dependencies)."""
    op.drop_index("ix_cards_face_name", table_name="cards")
    op.drop_index("ix_cards_name", table_name="cards")
    op.drop_index("ix_cards_set_code", table_name="cards")
    op.drop_table("cards")
    op.drop_table("sets")
