"""Add moxfield_data to ts_personal_decklist_versions (S3)

Revision ID: e7c2b4a9d631
Revises: b6e4d18a5f3c
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7c2b4a9d631"
down_revision: str | Sequence[str] | None = "b6e4d18a5f3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Nullable JSONB — the full Moxfield API response, set only for
    source == moxfield_import; NULL for manual entries and existing rows.
    """
    op.add_column(
        "ts_personal_decklist_versions",
        sa.Column(
            "moxfield_data",
            postgresql.JSONB(astext_type=sa.JSON()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drops `ts_personal_decklist_versions.moxfield_data`."""
    op.drop_column("ts_personal_decklist_versions", "moxfield_data")
