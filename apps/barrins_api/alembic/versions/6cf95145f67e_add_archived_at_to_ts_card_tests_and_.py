"""Add archived_at to ts_card_tests and ts_card_test_evaluations (S17 correction)

Deletion on both tables was shipped as a real SQL DELETE (with
`ts_card_test_evaluations.test_id` cascading, so deleting a card log
destroyed every evaluation logged against it with no way back) —
corrected the same day per Constitution §11.8 (deletion defaults to
archive, an explicit hard delete needs a documented exception, neither
of these tables has one). Existing rows are unaffected: `archived_at`
starts NULL (active) for everything, matching `TSPersonalDeck`/
`TSMetaDeck`'s same nullable, no-default shape.

Revision ID: 6cf95145f67e
Revises: 4f9a00bfb15a
Create Date: 2026-08-24 00:00:06.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6cf95145f67e"
down_revision: str | Sequence[str] | None = "4f9a00bfb15a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ts_card_tests",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ts_card_test_evaluations",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ts_card_test_evaluations", "archived_at")
    op.drop_column("ts_card_tests", "archived_at")
