"""Prefix MTGJSON tables with mj_, add mj_import_runs (S8 live progress)

Revision ID: cfef9209e088
Revises: 7d3f9a1c5e26
Create Date: 2026-08-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cfef9209e088"
down_revision: str | Sequence[str] | None = "7d3f9a1c5e26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Renames `sets`/`cards` to `mj_sets`/`mj_cards` (matching the `bs_*`/
    `ts_*` domain-prefix convention, never applied to these two tables
    when S8 first shipped them), and adds `mj_import_runs` -- an
    independently-committed operational log the importer writes progress
    to, so a status poll can see counts advance mid-run instead of
    nothing until the importer's single final commit (see
    `app/services/mtgjson/importer.py`'s `_ImportRunTracker`).

    Table rename only: API paths (`/sets/*`, `/cards/*`) and ORM class
    names (`MTGSet`, `Card`) are unaffected. Safe now because neither
    table has shipped in a release or held real data yet (confirmed empty
    on the dev DB before writing this migration).
    """
    op.rename_table("sets", "mj_sets")
    op.rename_table("cards", "mj_cards")

    # Postgres doesn't rename dependent indexes/constraints along with the
    # table, so do it explicitly for consistency with the new names.
    op.execute("ALTER TABLE mj_sets RENAME CONSTRAINT sets_pkey TO mj_sets_pkey")
    op.execute("ALTER TABLE mj_cards RENAME CONSTRAINT cards_pkey TO mj_cards_pkey")
    op.execute(
        "ALTER TABLE mj_cards RENAME CONSTRAINT cards_set_code_fkey "
        "TO mj_cards_set_code_fkey"
    )
    op.execute("ALTER INDEX ix_cards_set_code RENAME TO ix_mj_cards_set_code")
    op.execute("ALTER INDEX ix_cards_name RENAME TO ix_mj_cards_name")
    op.execute("ALTER INDEX ix_cards_face_name RENAME TO ix_mj_cards_face_name")

    op.create_table(
        "mj_import_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sets_upserted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cards_upserted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
    )


def downgrade() -> None:
    """Drops `mj_import_runs` and reverses the `mj_`-prefix rename."""
    op.drop_table("mj_import_runs")

    op.execute("ALTER INDEX ix_mj_cards_face_name RENAME TO ix_cards_face_name")
    op.execute("ALTER INDEX ix_mj_cards_name RENAME TO ix_cards_name")
    op.execute("ALTER INDEX ix_mj_cards_set_code RENAME TO ix_cards_set_code")
    op.execute(
        "ALTER TABLE mj_cards RENAME CONSTRAINT mj_cards_set_code_fkey "
        "TO cards_set_code_fkey"
    )
    op.execute("ALTER TABLE mj_cards RENAME CONSTRAINT mj_cards_pkey TO cards_pkey")
    op.execute("ALTER TABLE mj_sets RENAME CONSTRAINT mj_sets_pkey TO sets_pkey")

    op.rename_table("mj_cards", "cards")
    op.rename_table("mj_sets", "sets")
