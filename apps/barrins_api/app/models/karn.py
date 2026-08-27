"""ORM models for the `kt_*` tables (Karn Tablets metagame-clustering domain).

Karn Tablets (`apps/karn_tablets`) is a scheduled clustering job with no
inbound API and no Postgres credential of its own — it pushes each run's
result to `POST /internal/karn/ingest` and `barrins_api` owns the storage
(ADR-13, mirroring the `bs_*` / Barrin's Scripture arrangement of ADR-5).

Three tables:

- `kt_clustering_runs` — one row per pushed run, carrying the §45.2
  provenance (window, algorithm, pipeline version, generated-at).
- `kt_archetypes` — a stable, cross-run archetype registry per
  `(format, window_kind)`. A run's raw `cluster_id` is not a stable
  identity; the ingester matches each cluster to an archetype here by
  representative-decklist similarity (see
  `app/services/karn/ingester.py`).
- `kt_run_archetypes` — one row per cluster within a run, linking it to
  the archetype it was matched to and carrying its share / representative
  decklist.
"""

import enum
import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._types import JsonValue, jsonb_column


class KTWindowKind(enum.StrEnum):
    """Which windowing strategy a clustering run used (ADR-13 — both ship).

    Matches `dc_calendar.windowing.WindowKind` / the `--window` CLI values
    `apps/karn_tablets` sends in its push payload.
    """

    rolling_30d = "rolling_30d"
    banlist_period = "banlist_period"


#: One shared `Enum` type object, referenced by both tables that use it, so
#: `Base.metadata.create_all` (the test harness) emits the
#: `CREATE TYPE kt_window_kind` exactly once.
_window_kind_enum = Enum(KTWindowKind, name="kt_window_kind")

#: `bs_tournaments.format` is `String(120)`; a Karn Tablets run is scoped
#: to one format string and this column stores the same values.
_FORMAT_MAX_LENGTH = 120


class KTClusteringRun(Base):
    """One clustering run pushed by `apps/karn_tablets` (ADR-13)."""

    __tablename__ = "kt_clustering_runs"
    __table_args__ = (
        UniqueConstraint(
            "format",
            "window_kind",
            "window_label",
            "generated_at",
            name="uq_kt_runs_window_generated",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    #: Stamped by the ingester. The frozen CLI contract carries no format
    #: field yet, so today this is always "Duel Commander"
    #: (`INGEST_DEFAULT_FORMAT`); the column and the read APIs are
    #: format-scoped from v1 so a multi-format pipeline needs no schema or
    #: contract change later.
    format: Mapped[str] = mapped_column(String(_FORMAT_MAX_LENGTH), nullable=False)
    window_kind: Mapped[KTWindowKind] = mapped_column(_window_kind_enum, nullable=False)
    #: `dc_calendar.windowing.Window.label` — e.g. a banlist-season
    #: `"<year>-<number>"` or a rolling-window label.
    window_label: Mapped[str] = mapped_column(String(64), nullable=False)
    window_date_from: Mapped[date_type] = mapped_column(Date, nullable=False)
    window_date_to: Mapped[date_type] = mapped_column(Date, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    total_decks: Mapped[int] = mapped_column(Integer, nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(32), nullable=False)
    #: From the payload — when the pipeline produced this result (§45.2
    #: provenance). Reads return the row with the greatest `generated_at`
    #: per `(format, window_kind)`.
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class KTArchetype(Base):
    """A stable archetype identity, tracked across runs of one
    `(format, window_kind)` so `/trends` can follow an archetype's share
    over time. `name` is auto-generated from the archetype's representative
    cards on first sighting and is admin-renamable later (no rename
    endpoint yet).
    """

    __tablename__ = "kt_archetypes"
    __table_args__ = (
        UniqueConstraint(
            "format",
            "window_kind",
            "name",
            name="uq_kt_archetypes_format_window_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    format: Mapped[str] = mapped_column(String(_FORMAT_MAX_LENGTH), nullable=False)
    window_kind: Mapped[KTWindowKind] = mapped_column(_window_kind_enum, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    #: The archetype's commander card name(s), sorted (from a run's
    #: representative *sideboard*). In Duel Commander this is the primary
    #: identity: two clusters with the same commanders are the same
    #: archetype regardless of 99-card list drift. Empty list for data
    #: with no commander.
    commanders: Mapped[JsonValue] = jsonb_column(nullable=False)
    #: Secondary matching fingerprint: the most recent run's top-N
    #: mainboard card names, sorted. Compared set-wise (Jaccard) only when
    #: `commanders` can't decide the match.
    signature: Mapped[JsonValue] = jsonb_column(nullable=False)
    first_seen_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("kt_clustering_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    last_seen_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("kt_clustering_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class KTRunArchetype(Base):
    """One cluster within a run, matched to a stable `KTArchetype`."""

    __tablename__ = "kt_run_archetypes"
    __table_args__ = (
        UniqueConstraint("run_id", "archetype_id", name="uq_kt_run_archetypes"),
        # `run_id` lookups ride the unique constraint's leading column;
        # `archetype_id` needs its own index (Postgres doesn't index FKs)
        # for the trend share query and the RESTRICT FK check.
        Index("ix_kt_run_archetypes_archetype_id", "archetype_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("kt_clustering_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    archetype_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("kt_archetypes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    #: The run-local, unstable cluster integer from the push payload —
    #: kept only for debugging / tracing back to the pipeline's own logs.
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)
    deck_count: Mapped[int] = mapped_column(Integer, nullable=False)
    #: `deck_count / run.total_decks`, in [0, 1] (as sent by the pipeline).
    share: Mapped[float] = mapped_column(Float, nullable=False)
    representative_mainboard: Mapped[JsonValue] = jsonb_column(nullable=False)
    representative_sideboard: Mapped[JsonValue] = jsonb_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
