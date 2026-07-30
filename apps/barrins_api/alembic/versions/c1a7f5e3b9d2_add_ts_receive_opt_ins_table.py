"""Add ts_receive_opt_ins table (S1: per-sharer receive opt-in)

Revision ID: c1a7f5e3b9d2
Revises: 49c50188ee55
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1a7f5e3b9d2"
down_revision: str | Sequence[str] | None = "49c50188ee55"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Creates `ts_receive_opt_ins` (viewer's opt-in to a specific sharer)."""
    op.create_table(
        "ts_receive_opt_ins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "viewer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sharer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("viewer_id", "sharer_id", name="uq_ts_receive_opt_in"),
    )


def downgrade() -> None:
    """Drops `ts_receive_opt_ins`."""
    op.drop_table("ts_receive_opt_ins")
