"""Add sequence to bs_rounds (bracket-order tracking)

Revision ID: a3c7f912e5b8
Revises: cfef9209e088
Create Date: 2026-08-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3c7f912e5b8"
down_revision: str | Sequence[str] | None = "cfef9209e088"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adds `bs_rounds.sequence`, discovered while building the Tolaria
    News bracket route (T4 iteration 2, ADR-13): `created_at` can't order
    rounds within a tournament (transaction-scoped `now()`, every round
    upserted in one ingest shares a timestamp), and `round_name` is free
    text, not reliably sortable. Backfilled to 0 for any already-ingested
    rows -- those tournaments' bracket order was never recoverable from
    existing data anyway; a future re-scrape/re-ingest will populate the
    real sequence going forward (`_upsert_round`'s upsert is keyed on
    `(tournament_id, round_name)`, so a resubmitted scrape updates the
    existing row's `sequence` in place).
    """
    op.add_column(
        "bs_rounds",
        sa.Column("sequence", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("bs_rounds", "sequence")
