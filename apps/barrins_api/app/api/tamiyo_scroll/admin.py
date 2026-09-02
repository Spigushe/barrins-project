"""Admin-only usage/metrics dashboard (S6).

Ships embedded in `barrins_api`/`tamiyo_scroll` for v2.0.0, gated by the
existing `AdminUser` role dependency — no new auth work (`index.md`
§1.7). Exactly the three staged adoption signals, nothing more (deeper
metrics — active users, sharing adoption, retention... — are explicitly
deferred, not v2.0.0).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.database.session import DatabaseSession
from app.dependencies.auth import AdminUser
from app.models.karn import KTWindowKind
from app.schemas.responses_tamiyo_scroll import (
    ResponseAggregateMetric,
    ResponseKarnArchetypeShare,
    ResponseKarnDeckTypeDistribution,
    ResponseMetricTimeseries,
    ResponseMetricTimeseriesPoint,
    ResponsePlatformMetrics,
    ResponsePlatformMetricsTimeseries,
)
from app.services.karn import read as karn_read
from app.services.metrics import (
    MetricTimeseries,
    compute_platform_metrics,
    compute_platform_metrics_timeseries,
)

router = APIRouter()

_KARN_DEFAULT_FORMAT = "Duel Commander"


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
    """Total personal decks / matches ever created, platform-wide.

    Aggregate-only, computed entirely from data the backend already holds
    for its normal function — no new data collection (constitution §51,
    Privacy/Data Retention & Analytics Policy). "Total accounts" left with
    the local `users` table (ADR-20).
    """
    metrics = await compute_platform_metrics(session)
    return ResponsePlatformMetrics(
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
    """Day/week/month bucketed comparison of the same counts above
    (added 2026-08-02, `index.md`'s "Added requirement" section) — not a
    new metric, the same personal-decks/matches counts grouped by
    `created_at` bucket instead of collapsed to one all-time total.
    """
    timeseries = await compute_platform_metrics_timeseries(session)
    return ResponsePlatformMetricsTimeseries(
        personal_decks=_to_response_timeseries(timeseries.personal_decks),
        matches=_to_response_timeseries(timeseries.matches),
    )


@router.get(
    "/admin/metrics/karn-tablets",
    response_model=ResponseKarnDeckTypeDistribution,
)
async def get_karn_tablets_distribution(
    session: DatabaseSession,
    _admin: AdminUser,
    window: Annotated[Literal["rolling_30d", "banlist_period"], Query()],
    fmt: Annotated[str, Query(alias="format")] = _KARN_DEFAULT_FORMAT,
) -> ResponseKarnDeckTypeDistribution:
    """Deck-type share of the latest Karn Tablets clustering run for the
    given `(format, window)` — the exact numbers the public Tolaria News
    `/metagame` route serves (ADR-13: S6 and Tolaria News read the same
    `kt_*` tables through the same service, never a separate computation).

    Aggregate-only, derived from data the backend already stores for the
    clustering pipeline — no new collection (Constitution §51).
    """
    snapshot = await karn_read.metagame_snapshot(session, fmt, KTWindowKind(window))
    return ResponseKarnDeckTypeDistribution(
        format=snapshot.fmt,
        window_kind=snapshot.window.kind.value,
        window_label=snapshot.window.label,
        window_date_from=snapshot.window.date_from,
        window_date_to=snapshot.window.date_to,
        total_decks=snapshot.total_decks,
        generated_at=snapshot.synced_at,
        archetypes=[
            ResponseKarnArchetypeShare(
                id=str(row.id),
                name=row.name,
                deck_count=row.deck_count,
                deck_share=row.share,
            )
            for row in snapshot.archetypes
        ],
    )
