"""Drop the local auth schema (identity cutover, ADR-20)

Revision ID: d9e1a2c3b4f5
Revises: a1f4c7e9b230
Create Date: 2026-09-01 00:00:00.000000

Since ADR-20 `barrins_api` authenticates purely against `barrins_identity`
JWKS. It no longer owns users: this migration removes the local `users`
table, the `auth_email_verifications` table and the `userrole` enum, and
drops every `ForeignKey("users.id")` constraint from the Tamiyo Scroll
domain tables. The `owner_id` / `user_id` / `author_id` / `flagged_by`
columns are kept as plain `UUID` — they now hold identity user IDs as
opaque references (the migration script preserves UUIDs on copy).

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9e1a2c3b4f5"
down_revision: str | Sequence[str] | None = "a1f4c7e9b230"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (table, column, ON DELETE) for every FK that pointed at `users.id`.
#: The constraint name is PostgreSQL's default `<table>_<column>_fkey`.
_USER_FKS: tuple[tuple[str, str, str], ...] = (
    ("ts_card_tests", "owner_id", "CASCADE"),
    ("ts_matches", "owner_id", "CASCADE"),
    ("ts_meta_decks", "owner_id", "CASCADE"),
    ("ts_personal_decks", "owner_id", "CASCADE"),
    ("ts_user_settings", "user_id", "CASCADE"),
    ("ts_sessions", "owner_id", "CASCADE"),
    ("ts_teams", "owner_id", "RESTRICT"),
    ("ts_team_members", "user_id", "CASCADE"),
    ("ts_team_deck_flags", "flagged_by", "SET NULL"),
    ("ts_team_deck_messages", "author_id", "CASCADE"),
    ("ts_invite_attempts", "user_id", "CASCADE"),
)


def upgrade() -> None:
    """Drop the FK constraints, then the auth tables and enum."""
    for table, column, _ in _USER_FKS:
        op.execute(
            f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_{column}_fkey"
        )

    # auth_email_verifications also FK'd users.id; drop the whole table.
    op.execute(
        "ALTER TABLE auth_email_verifications "
        "DROP CONSTRAINT IF EXISTS auth_email_verifications_user_id_fkey"
    )
    op.drop_table("auth_email_verifications")

    # DROP TABLE removes ix_users_email with it.
    op.drop_table("users")
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """Best-effort recreation of the local auth schema (no data)."""
    userrole = sa.Enum("user", "placeholder", "ml_developer", "admin", name="userrole")
    userrole.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            userrole,
            server_default="user",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "auth_email_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "last_sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    for table, column, ondelete in _USER_FKS:
        op.create_foreign_key(
            f"{table}_{column}_fkey",
            table,
            "users",
            [column],
            ["id"],
            ondelete=ondelete,
        )
