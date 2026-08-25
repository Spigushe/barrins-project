"""Add metagame_roster_scope to ts_user_settings (F10)

Revision ID: f4b6d3a8c17e
Revises: e91a4c7f2b56
Create Date: 2026-08-18 00:00:00.000001

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4b6d3a8c17e"
down_revision: str | Sequence[str] | None = "e91a4c7f2b56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """New `ts_metagame_roster_scope` type, then the column itself,
    defaulting every existing account to "game" scope (F10's decided
    default — one roster per game, matching the bug report). `CREATE
    TYPE` is issued as raw DDL first — `op.add_column` doesn't reliably
    emit it itself, per the same finding recorded in 3e8e2a2dc724.
    """
    op.execute("CREATE TYPE ts_metagame_roster_scope AS ENUM ('game', 'personal_deck')")
    op.add_column(
        "ts_user_settings",
        sa.Column(
            "metagame_roster_scope",
            sa.Enum(
                "game",
                "personal_deck",
                name="ts_metagame_roster_scope",
                create_type=False,
            ),
            nullable=False,
            server_default="game",
        ),
    )


def downgrade() -> None:
    op.drop_column("ts_user_settings", "metagame_roster_scope")
    op.execute("DROP TYPE ts_metagame_roster_scope")
