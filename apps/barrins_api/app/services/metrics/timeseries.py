"""Time-bucketed comparison for the S6 admin dashboard (added 2026-08-02).

Extends `aggregates.py`'s three flat all-time counts with the same three
counts broken down per period — day-by-day (last 30 days), weekly (last
12 weeks), and monthly (last 12 months) — per `docs/project/v2.0.0-bump/
s6-admin-metrics-dashboard/index.md`'s "Added requirement (2026-08-02)".
Not a new metric: same three sources (`User`, `TSPersonalDeck`,
`TSMatch`), just grouped by `created_at` bucket instead of collapsed to
one number.

Same performance discipline as `aggregates.py`: every bucket is computed
server-side via `GROUP BY func.date_trunc(...)`, never a row-fetching
`SELECT *` counted in Python — see `_bucket_count_statement` and
`TestBucketStatementShape` in `tests/tamiyo_scroll/test_admin_metrics.py`.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models.tamiyo_scroll import TSMatch, TSPersonalDeck
from app.models.user import User

Granularity = Literal["day", "week", "month"]

# Bucketing windows (index.md: "last 30 days" / "last 12 weeks" / "last 12
# months"). The month window is a day-count approximation (12 * ~30.44),
# not calendar-exact — it only bounds the query to avoid scanning the
# entire table, `date_trunc('month', ...)` still buckets by real calendar
# month, so an approximate lower edge costs nothing but a few extra rows.
DAILY_WINDOW = timedelta(days=30)
WEEKLY_WINDOW = timedelta(weeks=12)
MONTHLY_WINDOW = timedelta(days=365)

_WINDOW_BY_GRANULARITY: dict[Granularity, timedelta] = {
    "day": DAILY_WINDOW,
    "week": WEEKLY_WINDOW,
    "month": MONTHLY_WINDOW,
}


@dataclass(frozen=True)
class TimeseriesPoint:
    """One bucket's count, keyed by the bucket's start instant."""

    period_start: datetime
    count: int


@dataclass(frozen=True)
class MetricTimeseries:
    daily: list[TimeseriesPoint]
    weekly: list[TimeseriesPoint]
    monthly: list[TimeseriesPoint]


@dataclass(frozen=True)
class PlatformMetricsTimeseries:
    accounts: MetricTimeseries
    personal_decks: MetricTimeseries
    matches: MetricTimeseries


def _bucket_count_statement(
    column: InstrumentedAttribute[datetime], granularity: Granularity, since: datetime
) -> Select[tuple[datetime, int]]:
    """`SELECT date_trunc(granularity, column), count(*) ... GROUP BY ...`

    Never a row-fetching `SELECT *` — only the truncated timestamp and a
    `count(*)` are selected, aggregated server-side.
    """
    bucket = func.date_trunc(granularity, column)
    # Labeled "value" rather than "count" — `Row` already exposes a
    # `count()` method, which would shadow a same-named attribute access
    # below (`row.count` would resolve to the method, not the column).
    return (
        select(bucket.label("period_start"), func.count().label("value"))
        .where(column >= since)
        .group_by(bucket)
        .order_by(bucket)
    )


async def _fetch_buckets(
    session: AsyncSession,
    column: InstrumentedAttribute[datetime],
    granularity: Granularity,
    now: datetime,
) -> list[TimeseriesPoint]:
    since = now - _WINDOW_BY_GRANULARITY[granularity]
    result = await session.execute(_bucket_count_statement(column, granularity, since))
    return [
        TimeseriesPoint(period_start=row.period_start, count=row.value)
        for row in result
    ]


async def _compute_metric_timeseries(
    session: AsyncSession, column: InstrumentedAttribute[datetime], now: datetime
) -> MetricTimeseries:
    return MetricTimeseries(
        daily=await _fetch_buckets(session, column, "day", now),
        weekly=await _fetch_buckets(session, column, "week", now),
        monthly=await _fetch_buckets(session, column, "month", now),
    )


async def compute_platform_metrics_timeseries(
    session: AsyncSession,
) -> PlatformMetricsTimeseries:
    """Day/week/month bucketed counts for accounts, personal decks, matches.

    Each of the three metrics' `created_at` is bucketed independently by
    day (last 30 days), week (last 12 weeks), and month (last 12 months).
    """
    now = datetime.now(UTC)
    return PlatformMetricsTimeseries(
        accounts=await _compute_metric_timeseries(session, User.created_at, now),
        personal_decks=await _compute_metric_timeseries(
            session, TSPersonalDeck.created_at, now
        ),
        matches=await _compute_metric_timeseries(session, TSMatch.created_at, now),
    )
