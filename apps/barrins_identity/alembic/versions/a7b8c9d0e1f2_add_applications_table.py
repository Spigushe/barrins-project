"""Add applications table + seed the Goblin Guide directory

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-31 00:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Reuse the existing enum type (created by the initial migration) — do not
# emit a second CREATE TYPE.
_userrole = postgresql.ENUM(
    "user",
    "moderator",
    "ml_developer",
    "admin",
    name="userrole",
    create_type=False,
)

# --- seed logos ---------------------------------------------------------------
# Small inline SVGs in the Barrin's house palette. Rendered by the SPA as an
# <img> data URI, so no script/fetch inside them can ever execute. Admins can
# replace these later (see ADR-19).
_LOGO_GOBLIN_GUIDE = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
    "<rect width='64' height='64' rx='10' fill='#26262e'/>"
    "<path d='M32 12 50 20v14c0 11.5-8 18-18 21-10-3-18-9.5-18-21V20z' "
    "fill='none' stroke='#e4e4ea' stroke-width='2.6' stroke-linejoin='round'/>"
    "<circle cx='32' cy='31' r='6' fill='none' stroke='#c9a227' "
    "stroke-width='2.6'/>"
    "<path d='M32 37v9' stroke='#c9a227' stroke-width='2.6' "
    "stroke-linecap='round'/></svg>"
)
_LOGO_TAMIYO_SCROLL = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
    "<rect width='64' height='64' rx='10' fill='#26262e'/>"
    "<path d='M32 18v28M32 18c-3-2-8-3-13-2v26c5-1 10 0 13 2M32 18c3-2 8-3 "
    "13-2v26c-5-1-10 0-13 2' fill='none' stroke='#e4e4ea' stroke-width='2.2' "
    "stroke-linecap='round' stroke-linejoin='round'/>"
    "<path d='M22 27l5 5 6-4 7-5' fill='none' stroke='#c9a227' "
    "stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'/></svg>"
)
_LOGO_TOLARIA_NEWS = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
    "<rect width='64' height='64' rx='10' fill='#0b1220'/>"
    "<path d='M32 12 52 32 32 52 12 32Z' fill='none' stroke='#7be0d6' "
    "stroke-width='2.5'/>"
    "<circle cx='32' cy='32' r='15' fill='none' stroke='#f0ead6' "
    "stroke-opacity='.5' stroke-width='1'/>"
    "<circle cx='32' cy='32' r='6' fill='#7be0d6'/>"
    "<circle cx='32' cy='32' r='2.5' fill='#0b1220'/></svg>"
)
_LOGO_KARN_JUPYTER = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
    "<rect width='64' height='64' rx='10' fill='#26262e'/>"
    "<rect x='18' y='10' width='28' height='44' rx='4' fill='none' "
    "stroke='#e4e4ea' stroke-width='2.4'/>"
    "<path d='M24 20h16M24 27h16' stroke='#4a7fd6' stroke-width='2' "
    "stroke-linecap='round'/>"
    "<path d='M25 44l6-8 5 5 5-9' fill='none' stroke='#c9a227' "
    "stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'/>"
    "<circle cx='25' cy='44' r='2.6' fill='#c9a227'/>"
    "<circle cx='46' cy='32' r='2.6' fill='#c9a227'/></svg>"
)


def upgrade() -> None:
    """Create `applications` (ADR-19) and seed the approved directory."""
    op.create_table(
        "applications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=255), nullable=False),
        sa.Column("logo_svg", sa.Text(), nullable=False),
        sa.Column(
            "needs_authentication",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "is_role_restricted",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("min_role", _userrole, nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.CheckConstraint(
            "NOT is_role_restricted OR (min_role IS NOT NULL AND needs_authentication)",
            name="ck_applications_role_restriction_consistent",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_applications_key"), "applications", ["key"], unique=True)

    seed = sa.table(
        "applications",
        sa.column("id", sa.UUID()),
        sa.column("key", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("url", sa.String()),
        sa.column("logo_svg", sa.Text()),
        sa.column("needs_authentication", sa.Boolean()),
        sa.column("is_role_restricted", sa.Boolean()),
        sa.column("min_role", _userrole),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(
        seed,
        [
            {
                "id": uuid.UUID("0a4b1c00-0000-4000-8000-000000000001"),
                "key": "goblin_guide",
                "name": "Goblin Guide",
                "description": "Sign in and manage your Barrin's account.",
                "url": "https://goblin.barrins-codex.org",
                "logo_svg": _LOGO_GOBLIN_GUIDE,
                "needs_authentication": True,
                "is_role_restricted": False,
                "min_role": None,
                "sort_order": 0,
            },
            {
                "id": uuid.UUID("0a4b1c00-0000-4000-8000-000000000002"),
                "key": "tamiyo_scroll",
                "name": "Tamiyo Scroll",
                "description": "Track your games and analyze your Commander decks.",
                "url": "https://tamiyo.barrins-codex.org",
                "logo_svg": _LOGO_TAMIYO_SCROLL,
                "needs_authentication": True,
                "is_role_restricted": False,
                "min_role": None,
                "sort_order": 10,
            },
            {
                "id": uuid.UUID("0a4b1c00-0000-4000-8000-000000000003"),
                "key": "tolaria_news",
                "name": "Tolaria News",
                "description": (
                    "Duel Commander metagame: decklists, tournament results "
                    "and machine learning exploration."
                ),
                "url": "https://tolaria.barrins-codex.org",
                "logo_svg": _LOGO_TOLARIA_NEWS,
                "needs_authentication": False,
                "is_role_restricted": False,
                "min_role": None,
                "sort_order": 20,
            },
            {
                "id": uuid.UUID("0a4b1c00-0000-4000-8000-000000000004"),
                "key": "karn_jupyter",
                "name": "Karn Tablets",
                "description": "Jupyter data-exploration workbench (ML team only).",
                "url": "https://karn-jupyter.barrins-codex.org",
                "logo_svg": _LOGO_KARN_JUPYTER,
                "needs_authentication": True,
                "is_role_restricted": True,
                "min_role": "ml_developer",
                "sort_order": 30,
            },
        ],
    )


def downgrade() -> None:
    """Drop the applications table (the reused `userrole` type stays)."""
    op.drop_index(op.f("ix_applications_key"), table_name="applications")
    op.drop_table("applications")
