"""Session overhaul: dates, hue, location, restore, auto-archive (S14)

Revision ID: b3f6a1d29c47
Revises: f4b6d3a8c17e
Create Date: 2026-08-24 00:00:00.000001

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f6a1d29c47"
down_revision: str | Sequence[str] | None = "f4b6d3a8c17e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """`ts_sessions.ended_at` is renamed to `closed_at` — it's the column
    Close/Reopen have always driven (and what the Status badge reads),
    untouched in behavior/data. A new `started_at`/`ended_at` pair is
    added, purely informational and independent of Close/Reopen, per the
    S14 decision to track a manually-edited end date separately from the
    close workflow state. `started_at` backfills from `created_at`;
    `ended_at` backfills from the old `ended_at` (now `closed_at`) as the
    best available guess for already-closed sessions.
    """
    op.alter_column("ts_sessions", "ended_at", new_column_name="closed_at")
    op.add_column(
        "ts_sessions",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ts_sessions", sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("ts_sessions", sa.Column("hue", sa.Integer(), nullable=True))
    op.add_column("ts_sessions", sa.Column("location", sa.String(255), nullable=True))
    op.create_check_constraint(
        "ck_ts_sessions_hue_range", "ts_sessions", "hue BETWEEN 0 AND 359"
    )
    op.execute("UPDATE ts_sessions SET started_at = created_at")
    op.execute(
        "UPDATE ts_sessions SET ended_at = closed_at WHERE closed_at IS NOT NULL"
    )

    op.add_column(
        "ts_user_settings",
        sa.Column(
            "auto_archive_stale_sessions",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )
    op.add_column(
        "ts_user_settings",
        sa.Column(
            "auto_archive_decklist_version_gap",
            sa.Integer(),
            nullable=False,
            server_default="2",
        ),
    )


def downgrade() -> None:
    op.drop_column("ts_user_settings", "auto_archive_decklist_version_gap")
    op.drop_column("ts_user_settings", "auto_archive_stale_sessions")

    op.drop_constraint("ck_ts_sessions_hue_range", "ts_sessions", type_="check")
    op.drop_column("ts_sessions", "location")
    op.drop_column("ts_sessions", "hue")
    op.drop_column("ts_sessions", "ended_at")
    op.drop_column("ts_sessions", "started_at")
    op.alter_column("ts_sessions", "closed_at", new_column_name="ended_at")
