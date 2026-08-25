"""Pivot ts_card_tests to removed/added card names (S16)

`tester`/`card_name` are renamed to `removed_card_name`/
`added_card_name`, repurposing the table from "who tested which card" to
"which card was removed and which was added". Per the user's 2026-08-24
decision, existing rows are kept as-is under the new column names --
they predate the pivot and carry pre-pivot data, a documented migration
artifact (see docs/project/v2.0.0-bump/s16-tested-card-changelog).

Revision ID: 7b7e7c53f1a5
Revises: a1d5f8c3e947
Create Date: 2026-08-24 00:00:02.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7b7e7c53f1a5"
down_revision: str | Sequence[str] | None = "a1d5f8c3e947"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "ts_card_tests",
        "tester",
        new_column_name="removed_card_name",
        existing_type=sa.String(120),
        type_=sa.String(255),
    )
    op.alter_column(
        "ts_card_tests",
        "card_name",
        new_column_name="added_card_name",
        existing_type=sa.String(255),
    )


def downgrade() -> None:
    op.alter_column(
        "ts_card_tests",
        "added_card_name",
        new_column_name="card_name",
        existing_type=sa.String(255),
    )
    op.alter_column(
        "ts_card_tests",
        "removed_card_name",
        new_column_name="tester",
        existing_type=sa.String(255),
        type_=sa.String(120),
    )
