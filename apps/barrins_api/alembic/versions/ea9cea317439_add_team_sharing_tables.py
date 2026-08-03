"""Add team-sharing tables (S2)

Revision ID: ea9cea317439
Revises: f3b8c1d5a742
Create Date: 2026-08-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ea9cea317439"
down_revision: str | Sequence[str] | None = "f3b8c1d5a742"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """New ts_teams/ts_team_members/ts_team_deck_flags/ts_team_deck_threads/
    ts_team_deck_messages/ts_invite_attempts tables.

    Team-deck sharing is name-based (revised 2026-08-01, before this
    migration ever shipped): a `ts_team_deck_flags` row flags a deck
    *name* into a team's testing rotation, matched against every team
    member's own personal decks by name at read time (mirrors
    `sharing_merge.py`'s existing convention) — no FK column on
    ts_personal_decks itself.

    Unlike every other ts_* entity, ts_teams has no archived_at: team
    deletion is a hard DELETE (see TSTeam's docstring).
    """
    op.create_table(
        "ts_teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("invite_code", sa.String(8), nullable=False, unique=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "ts_team_members",
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_teams.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "ts_team_deck_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("deck_name", sa.String(255), nullable=False),
        sa.Column("name_key", sa.String(255), nullable=False),
        sa.Column(
            "flagged_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("team_id", "name_key", name="uq_ts_team_deck_flag"),
    )

    op.create_table(
        "ts_team_deck_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name_key", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("team_id", "name_key", name="uq_ts_team_deck_thread"),
    )

    op.create_table(
        "ts_team_deck_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_team_deck_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "ts_invite_attempts",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "window_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "attempts_in_window", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "last_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Drops every table created above, in FK order."""
    op.drop_table("ts_invite_attempts")
    op.drop_table("ts_team_deck_messages")
    op.drop_table("ts_team_deck_threads")
    op.drop_table("ts_team_deck_flags")
    op.drop_table("ts_team_members")
    op.drop_table("ts_teams")
