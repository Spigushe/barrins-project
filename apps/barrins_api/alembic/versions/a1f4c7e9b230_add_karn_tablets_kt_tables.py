"""Add Karn Tablets clustering tables (kt_*)

Revision ID: a1f4c7e9b230
Revises: b7d1f4a290ec
Create Date: 2026-08-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1f4c7e9b230"
down_revision: str | Sequence[str] | None = "b7d1f4a290ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Shared by kt_clustering_runs and kt_archetypes — created once, below.
_window_kind = postgresql.ENUM(
    "rolling_30d",
    "banlist_period",
    name="kt_window_kind",
    create_type=False,
)


def upgrade() -> None:
    """Creates the Karn Tablets domain (ADR-13): one row per pushed
    clustering run, a stable per-(format, window) archetype registry, and
    the run→archetype cluster rows.
    """
    _window_kind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "kt_clustering_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("format", sa.String(120), nullable=False),
        sa.Column("window_kind", _window_kind, nullable=False),
        sa.Column("window_label", sa.String(64), nullable=False),
        sa.Column("window_date_from", sa.Date, nullable=False),
        sa.Column("window_date_to", sa.Date, nullable=False),
        sa.Column("algorithm", sa.String(32), nullable=False),
        sa.Column("total_decks", sa.Integer, nullable=False),
        sa.Column("pipeline_version", sa.String(32), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "format",
            "window_kind",
            "window_label",
            "generated_at",
            name="uq_kt_runs_window_generated",
        ),
    )

    op.create_table(
        "kt_archetypes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("format", sa.String(120), nullable=False),
        sa.Column("window_kind", _window_kind, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column(
            "commanders",
            postgresql.JSONB(astext_type=sa.JSON()),
            nullable=False,
        ),
        sa.Column(
            "signature",
            postgresql.JSONB(astext_type=sa.JSON()),
            nullable=False,
        ),
        sa.Column(
            "first_seen_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("kt_clustering_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("kt_clustering_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "format",
            "window_kind",
            "name",
            name="uq_kt_archetypes_format_window_name",
        ),
    )

    op.create_table(
        "kt_run_archetypes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("kt_clustering_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "archetype_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("kt_archetypes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("cluster_id", sa.Integer, nullable=False),
        sa.Column("deck_count", sa.Integer, nullable=False),
        sa.Column("share", sa.Float, nullable=False),
        sa.Column(
            "representative_mainboard",
            postgresql.JSONB(astext_type=sa.JSON()),
            nullable=False,
        ),
        sa.Column(
            "representative_sideboard",
            postgresql.JSONB(astext_type=sa.JSON()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("run_id", "archetype_id", name="uq_kt_run_archetypes"),
    )
    # `(format, window_kind[, ...])` lookups on the other two tables ride
    # their unique constraints' leading columns; only `archetype_id` needs
    # its own index (Postgres doesn't index foreign keys).
    op.create_index(
        "ix_kt_run_archetypes_archetype_id",
        "kt_run_archetypes",
        ["archetype_id"],
    )


def downgrade() -> None:
    """Drops the Karn Tablets domain (reverse FK-dependency order)."""
    op.drop_table("kt_run_archetypes")
    op.drop_table("kt_archetypes")
    op.drop_table("kt_clustering_runs")
    sa.Enum(name="kt_window_kind").drop(op.get_bind(), checkfirst=True)
