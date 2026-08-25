"""Add show_decklist_version_diff to ts_user_settings (S15)

Revision ID: a1d5f8c3e947
Revises: b3f6a1d29c47
Create Date: 2026-08-24 00:00:00.000001

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1d5f8c3e947"
down_revision: str | Sequence[str] | None = "b3f6a1d29c47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Toggle for the version-diff view (S15) — defaults True for every
    existing account (2026-08-24 decision, unlike the other
    `ts_user_settings` booleans which stay non-retroactive)."""
    op.add_column(
        "ts_user_settings",
        sa.Column(
            "show_decklist_version_diff",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )


def downgrade() -> None:
    op.drop_column("ts_user_settings", "show_decklist_version_diff")
