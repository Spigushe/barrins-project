"""Add decklist_version_id to ts_matches (S3)

Revision ID: d4e8a1c6f720
Revises: c1a7f5e3b9d2
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e8a1c6f720"
down_revision: str | Sequence[str] | None = "c1a7f5e3b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Nullable FK — existing matches stay NULL, no backfill."""
    op.add_column(
        "ts_matches",
        sa.Column(
            "decklist_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_personal_decklist_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drops `ts_matches.decklist_version_id`."""
    op.drop_column("ts_matches", "decklist_version_id")
