"""Add game and category to ts_personal_decks (S10/S11)

Revision ID: b3f6d2a8c451
Revises: ea9cea317439
Create Date: 2026-08-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f6d2a8c451"
down_revision: str | Sequence[str] | None = "ea9cea317439"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Both nullable, no backfill — existing decks read NULL until PATCHed.

    `game` creates a new `ts_card_game` type; `category` reuses the
    existing `ts_archetype_category` type created for `ts_meta_decks`
    (`create_type=False` — must not recreate it).
    """
    op.add_column(
        "ts_personal_decks",
        sa.Column(
            "game",
            postgresql.ENUM(
                "magic",
                "yu_gi_oh",
                "pokemon",
                "flesh_and_blood",
                "one_piece",
                "lorcana",
                "star_wars_unlimited",
                "digimon",
                "cardfight_vanguard",
                "riftbound",
                "other",
                name="ts_card_game",
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "ts_personal_decks",
        sa.Column(
            "category",
            postgresql.ENUM(
                "aggro",
                "midrange",
                "control",
                "combo",
                name="ts_archetype_category",
                create_type=False,
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drops both columns, then the new `ts_card_game` type (not
    `ts_archetype_category` — that type is owned by `ts_meta_decks`)."""
    op.drop_column("ts_personal_decks", "category")
    op.drop_column("ts_personal_decks", "game")
    sa.Enum(name="ts_card_game").drop(op.get_bind(), checkfirst=True)
