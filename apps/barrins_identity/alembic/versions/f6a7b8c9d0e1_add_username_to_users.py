"""Add username to users

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-29 00:00:00.000000

Adds the unique `username` handle required by constitution §13.2
(ADR-17 / platform.md Q-03). The service has no production instance yet
(see docs/content/ops/deployment/identity.md), so the column is added
NOT NULL directly with no backfill — there are no existing rows.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add users.username (unique, indexed, NOT NULL)."""
    op.add_column(
        "users",
        sa.Column("username", sa.String(length=64), nullable=False),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)


def downgrade() -> None:
    """Drop users.username."""
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "username")
