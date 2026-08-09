"""On-disk size of every `bs_*` table (Barrin's Scripture domain).

Backs `GET /internal/scripture/db-metrics`, read by both Barrin's
Scripture's own ops tooling and admins (`verify_scripture_or_admin`).
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scripture import (
    BSDeck,
    BSDeckCard,
    BSRound,
    BSRoundMatch,
    BSStanding,
    BSTournament,
)

#: Every `bs_*` table name, sourced from each model's `__tablename__`
#: rather than a `pg_catalog` scan filtered by a `LIKE 'bs_%'` naming
#: guess. Order matches the ingester's FK order
#: (tournament -> decks/rounds -> ...).
_BS_TABLE_NAMES: tuple[str, ...] = (
    BSTournament.__tablename__,
    BSDeck.__tablename__,
    BSDeckCard.__tablename__,
    BSRound.__tablename__,
    BSRoundMatch.__tablename__,
    BSStanding.__tablename__,
)


@dataclass(frozen=True)
class TableSize:
    table_name: str
    #: `pg_total_relation_size` — table heap + indexes + TOAST, i.e. what
    #: actually consumes disk, not just the bare heap
    #: (`pg_relation_size`).
    size_bytes: int
    #: Live `count(*)` — `size_bytes` alone can't tell an ingestion that
    #: wrote zero rows apart from one that wrote a few small ones.
    row_count: int


async def compute_scripture_db_metrics(session: AsyncSession) -> list[TableSize]:
    """Size + row count per `bs_*` table, in `_BS_TABLE_NAMES` order."""
    sizes = []
    for table_name in _BS_TABLE_NAMES:
        size = await session.scalar(
            text("SELECT pg_total_relation_size(CAST(:table_name AS regclass))"),
            {"table_name": table_name},
        )
        # table_name is sourced from each model's __tablename__ (_BS_TABLE_NAMES
        # above), never request input, so building the FROM clause this way
        # carries no injection risk despite not being parametrized — a bind
        # parameter can't stand in for an identifier here.
        row_count = await session.scalar(
            text(f"SELECT count(*) FROM {table_name}")  # noqa: S608
        )
        sizes.append(
            TableSize(
                table_name=table_name,
                size_bytes=size or 0,
                row_count=row_count or 0,
            )
        )
    return sizes
