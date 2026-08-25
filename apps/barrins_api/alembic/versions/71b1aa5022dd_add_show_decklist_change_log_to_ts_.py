"""Add show_decklist_change_log to ts_user_settings (S16)

Revision ID: 71b1aa5022dd
Revises: 0fa2b642b5bf
Create Date: 2026-08-24 00:00:04.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "71b1aa5022dd"
down_revision: str | Sequence[str] | None = "0fa2b642b5bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ts_user_settings",
        sa.Column(
            "show_decklist_change_log",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("ts_user_settings", "show_decklist_change_log")
