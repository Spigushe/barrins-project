"""Add text/keywords/power/toughness/loyalty to mj_cards

Revision ID: b7d1f4a290ec
Revises: a3c7f912e5b8
Create Date: 2026-08-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d1f4a290ec"
down_revision: str | Sequence[str] | None = "a3c7f912e5b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adds columns MTGJSON's source data already has but S8's importer
    never mapped: oracle text, keywords, power, toughness, loyalty --
    needed by Karn Tablets' functional-classification feature engineering
    (T6, ADR-13). Nullable, no backfill here -- re-running the existing
    idempotent `POST /mtgjson/import` populates them for every card.
    """
    op.add_column("mj_cards", sa.Column("text", sa.Text, nullable=True))
    op.add_column(
        "mj_cards",
        sa.Column(
            "keywords",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column("mj_cards", sa.Column("power", sa.String(16), nullable=True))
    op.add_column("mj_cards", sa.Column("toughness", sa.String(16), nullable=True))
    op.add_column("mj_cards", sa.Column("loyalty", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("mj_cards", "loyalty")
    op.drop_column("mj_cards", "toughness")
    op.drop_column("mj_cards", "power")
    op.drop_column("mj_cards", "keywords")
    op.drop_column("mj_cards", "text")
