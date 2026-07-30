"""Replace per-sharer ts_receive_opt_ins with a single receive_shared_data toggle

Revision ID: a9f27e6c1b34
Revises: d4e8a1c6f720
Create Date: 2026-07-30 00:00:00.000000

Supersedes S1's original per-sharer opt-in design: the account-settings
popup handoff (z_handoff_params_popup) specifies a single flat "receive"
switch, not a per-sharer list. `ts_receive_opt_ins` never shipped past a
feature branch, so this drops it outright rather than migrating its data.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9f27e6c1b34"
down_revision: str | Sequence[str] | None = "d4e8a1c6f720"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("ts_receive_opt_ins")
    op.add_column(
        "ts_user_settings",
        sa.Column(
            "receive_shared_data", sa.Boolean, nullable=False, server_default="false"
        ),
    )


def downgrade() -> None:
    op.drop_column("ts_user_settings", "receive_shared_data")
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
