"""Admin-only usage/metrics dashboard (S6).

Ships embedded in `barrins_api`/`tamiyo_scroll` for v2.0.0, gated by the
existing `AdminUser` role dependency — no new auth work (`index.md`
§1.7). Exactly the three staged adoption signals, nothing more (deeper
metrics — active users, sharing adoption, retention... — are explicitly
deferred, not v2.0.0).
"""

from fastapi import APIRouter

from app.database.session import DatabaseSession
from app.dependencies.auth import AdminUser
from app.schemas.responses_tamiyo_scroll import (
    ResponseAggregateMetric,
    ResponseMetricTimeseries,
    ResponseMetricTimeseriesPoint,
    ResponsePlatformMetrics,
    ResponsePlatformMetricsTimeseries,
)
from app.services.metrics import (
    MetricTimeseries,
    compute_platform_metrics,
    compute_platform_metrics_timeseries,
)

router = APIRouter()


def _to_response_timeseries(metric: MetricTimeseries) -> ResponseMetricTimeseries:
    return ResponseMetricTimeseries(
        daily=[
            ResponseMetricTimeseriesPoint(period_start=p.period_start, count=p.count)
            for p in metric.daily
        ],
        weekly=[
            ResponseMetricTimeseriesPoint(period_start=p.period_start, count=p.count)
            for p in metric.weekly
        ],
        monthly=[
            ResponseMetricTimeseriesPoint(period_start=p.period_start, count=p.count)
            for p in metric.monthly
        ],
    )


@router.get("/admin/metrics", response_model=ResponsePlatformMetrics)
async def get_platform_metrics(
    session: DatabaseSession,
    _admin: AdminUser,
) -> ResponsePlatformMetrics:
    """Total accounts / personal decks / matches ever created, platform-wide.

    Aggregate-only, computed entirely from data the backend already holds
    for its normal function — no new data collection (constitution §51,
    Privacy/Data Retention & Analytics Policy).
    """
    metrics = await compute_platform_metrics(session)
    return ResponsePlatformMetrics(
        total_accounts=ResponseAggregateMetric(
            value=metrics.total_accounts.value, source=metrics.total_accounts.source
        ),
        total_personal_decks=ResponseAggregateMetric(
            value=metrics.total_personal_decks.value,
            source=metrics.total_personal_decks.source,
        ),
        total_matches=ResponseAggregateMetric(
            value=metrics.total_matches.value, source=metrics.total_matches.source
        ),
    )


@router.get(
    "/admin/metrics/timeseries", response_model=ResponsePlatformMetricsTimeseries
)
async def get_platform_metrics_timeseries(
    session: DatabaseSession,
    _admin: AdminUser,
) -> ResponsePlatformMetricsTimeseries:
    """Day/week/month bucketed comparison of the same three counts above
    (added 2026-08-02, `index.md`'s "Added requirement" section) — not a
    new metric, the same accounts/personal-decks/matches counts grouped
    by `created_at` bucket instead of collapsed to one all-time total.
    """
    timeseries = await compute_platform_metrics_timeseries(session)
    return ResponsePlatformMetricsTimeseries(
        accounts=_to_response_timeseries(timeseries.accounts),
        personal_decks=_to_response_timeseries(timeseries.personal_decks),
        matches=_to_response_timeseries(timeseries.matches),
    )
