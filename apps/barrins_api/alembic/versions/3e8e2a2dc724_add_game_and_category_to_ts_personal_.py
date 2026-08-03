"""Add game and category to ts_personal_decks (S10/S11)

Revision ID: 3e8e2a2dc724
Revises: ea9cea317439
Create Date: 2026-08-02 18:13:01.314836

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3e8e2a2dc724"
down_revision: str | Sequence[str] | None = "ea9cea317439"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add game (new `ts_card_game` type) and category (reused
    `ts_archetype_category`, already created for `ts_meta_decks`) to
    `ts_personal_decks`; add game (reused `ts_card_game`) to
    `ts_meta_decks`. All three nullable, no backfill.

    `ts_card_game` is created explicitly via raw DDL below, then every
    column referencing it uses `create_type=False` — a plain
    `sa.Enum(...)` passed to `op.add_column` does not reliably emit
    `CREATE TYPE` first (unlike `op.create_table`), confirmed by two
    failed runs against a real database raising `UndefinedObject: type
    "ts_card_game" does not exist` on the very column meant to create it.
    """
    op.execute(
        "CREATE TYPE ts_card_game AS ENUM ("
        "'magic', 'yu_gi_oh', 'pokemon', 'flesh_and_blood', 'one_piece', "
        "'lorcana', 'star_wars_unlimited', 'digimon', 'cardfight_vanguard', "
        "'riftbound', 'other')"
    )
    op.add_column(
        "ts_personal_decks",
        sa.Column(
            "game",
            sa.Enum(
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
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "ts_personal_decks",
        sa.Column(
            "category",
            sa.Enum(
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
    op.add_column(
        "ts_meta_decks",
        sa.Column(
            "game",
            sa.Enum(
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
                create_type=False,
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drops all three columns, then the `ts_card_game` type itself (not
    `ts_archetype_category` — that type is owned by `ts_meta_decks`'s
    original migration)."""
    op.drop_column("ts_meta_decks", "game")
    op.drop_column("ts_personal_decks", "category")
    op.drop_column("ts_personal_decks", "game")
    op.execute("DROP TYPE ts_card_game")
