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
    ResponsePlatformMetrics,
)
from app.services.metrics import compute_platform_metrics

router = APIRouter()


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
