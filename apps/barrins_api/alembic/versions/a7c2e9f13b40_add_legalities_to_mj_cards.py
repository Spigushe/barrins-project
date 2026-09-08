"""Add legalities to mj_cards (Duel-Commander banlist filter on card search)

`GET /cards/search-by-name-prefix?exclude_banned_in=duelcommander` needs
each card's per-format legality, which MTGJSON's `AllPrintings.json` has
always carried but the importer never mapped in. Same shape and
backfill story as `b7d1f4a290ec` (text/keywords for Karn Tablets):
NOT NULL with a `'{}'` server default so existing rows are valid
immediately, then a re-run of the idempotent `POST /mtgjson/import`
populates the real values. The search filter treats an empty map as
"nothing to hide", so it is a no-op until that re-import lands.

Revision ID: a7c2e9f13b40
Revises: 6cf95145f67e
Create Date: 2026-09-07 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a7c2e9f13b40"
down_revision: str | Sequence[str] | None = "6cf95145f67e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mj_cards",
        sa.Column(
            "legalities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("mj_cards", "legalities")
