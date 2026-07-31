"""Add ts_sessions table + session_id on ts_matches (S9)

Revision ID: f3b8c1d5a742
Revises: e7c2b4a9d631
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3b8c1d5a742"
down_revision: str | Sequence[str] | None = "e7c2b4a9d631"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """New ts_sessions table (soft-deleted via archived_at, same pattern as
    ts_personal_decks/ts_meta_decks) + a nullable session_id FK on
    ts_matches (ON DELETE SET NULL — defensive only, sessions are never
    hard-deleted in normal operation).
    """
    op.create_table(
        "ts_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "personal_deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_personal_decks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "type",
            sa.Enum("tournament", "training", name="ts_session_type"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ts_matches",
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drops `ts_matches.session_id` and the `ts_sessions` table/enum."""
    op.drop_column("ts_matches", "session_id")
    op.drop_table("ts_sessions")
    sa.Enum(name="ts_session_type").drop(op.get_bind(), checkfirst=True)
