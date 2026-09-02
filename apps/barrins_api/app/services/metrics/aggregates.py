"""Aggregate usage counts for the admin dashboard (S6).

Two numbers ship after the identity cutover (ADR-20): total personal
decks, total matches. "Total accounts" was dropped along with the local
`users` table — `barrins_api` no longer stores or counts users. Restoring
it means a dedicated `barrins_identity` admin count endpoint (future
work). Deeper metrics (active users, sharing adoption, retention...) are
explicitly deferred, not built here.

Unlike `services/tamiyo_scroll/stats.py` (pure functions over
already-loaded ORM objects), these are plain `COUNT(*)` aggregates over
entire tables — loading every row into Python just to call `len()` on
it would defeat the purpose and regress under real data volume. The
query builders below stay pure/synchronous and unit-testable on their
own (no DB touched, no ORM objects loaded); only `compute_platform_metrics`
is async and talks to the database, and even then only to execute a
`COUNT(*)`, never a row-fetching `SELECT *`.
"""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tamiyo_scroll import TSMatch, TSPersonalDeck

# v2.0.0 only ever populates "tamiyo_scroll" — every current account,
# personal deck, and match belongs to this one app. The literal exists so
# a v3.0.0 externalization (aggregating across multiple source apps) is
# an additive Literal member, not a schema break.
MetricSource = Literal["tamiyo_scroll"]


@dataclass(frozen=True)
class AggregateMetric:
    """A single aggregate count, tagged with the app/source it came from.

    The `source` tag is a forward-compatibility seam for v3.0.0 (this
    whole service externalizing into a standalone cross-app application,
    `index.md` §1.7) — deliberately just one extra field, nothing more
    elaborate, since nothing before v3.0.0 needs more than that.
    """

    value: int
    source: MetricSource


@dataclass(frozen=True)
class PlatformMetrics:
    total_personal_decks: AggregateMetric
    total_matches: AggregateMetric


def _count_statement(model: type) -> Select[tuple[int]]:
    """`SELECT count(*) FROM <model>` — never a row-fetching `SELECT *`."""
    return select(func.count()).select_from(model)


async def compute_platform_metrics(session: AsyncSession) -> PlatformMetrics:
    """Total personal decks / matches ever created.

    Each number is one `COUNT(*)` executed server-side. Personal decks
    and matches are never hard-deleted in this domain (personal decks
    soft-delete via `archived_at`, matches are never deleted at all — see
    their model docstrings), so a plain row count already means "ever
    created," matching the spec's wording exactly — no extra filtering
    needed.
    """
    total_personal_decks = await session.scalar(_count_statement(TSPersonalDeck))
    total_matches = await session.scalar(_count_statement(TSMatch))

    return PlatformMetrics(
        total_personal_decks=AggregateMetric(
            value=total_personal_decks or 0, source="tamiyo_scroll"
        ),
        total_matches=AggregateMetric(value=total_matches or 0, source="tamiyo_scroll"),
    )
