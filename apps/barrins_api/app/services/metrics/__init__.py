"""Platform usage/metrics aggregation (S6 — admin dashboard).

Self-contained (not folded into `app/services/tamiyo_scroll/`) even
though every metric it computes for v2.0.0 happens to be Tamiyo Scroll
data: `index.md` §1.7 confirmed this whole area externalizes into a
standalone cross-app application in v3.0.0, accessed via Barrin's
Identity/Goblin Guide. Keeping it in its own top-level package now
makes that a lift-and-shift later, not a rewrite.
"""

from app.services.metrics.aggregates import (
    AggregateMetric,
    PlatformMetrics,
    compute_platform_metrics,
)

__all__ = ["AggregateMetric", "PlatformMetrics", "compute_platform_metrics"]
