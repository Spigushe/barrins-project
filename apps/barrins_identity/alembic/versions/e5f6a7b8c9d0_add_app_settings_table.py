"""Add app_settings table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-22 04:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

import app.models._types
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Creates the app_settings table (platform.md §17)."""
    op.create_table(
        "app_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("app_key", sa.String(length=64), nullable=False),
        sa.Column(
            "data",
            app.models._types.JSONBCompat(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "app_key"),
    )


def downgrade() -> None:
    """Drops the app_settings table."""
    op.drop_table("app_settings")
