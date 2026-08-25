"""Add card-test validation settings to ts_user_settings (S16)

Revision ID: 0fa2b642b5bf
Revises: 7b7e7c53f1a5
Create Date: 2026-08-24 00:00:03.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0fa2b642b5bf"
down_revision: str | Sequence[str] | None = "7b7e7c53f1a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ts_user_settings",
        sa.Column(
            "validate_removed_card_in_decklist",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )
    op.add_column(
        "ts_user_settings",
        sa.Column(
            "validate_added_card_exists",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("ts_user_settings", "validate_added_card_exists")
    op.drop_column("ts_user_settings", "validate_removed_card_in_decklist")
