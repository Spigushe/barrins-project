"""Pushes a clustering run's result to `barrins_api`'s
`POST /internal/karn/ingest` (Phase 3 -- see ADR-13's push-based data-flow
decision). Mirrors `barrins_scripture.sweep`'s push pattern
(`X-Scripture-Token` -> `X-Karn-Token`, `requests.post` with a short
timeout, no retry -- a failed push just waits for the next scheduled run).
"""

import logging

import requests

from karn_tablets.pipeline import ClusteringRunResult

logger = logging.getLogger(__name__)

_INGEST_PATH = "/internal/karn/ingest"


def _payload(result: ClusteringRunResult) -> dict[str, object]:
    return {
        "window": {
            "kind": result.window.kind.value,
            "date_from": result.window.date_from.isoformat(),
            "date_to": result.window.date_to.isoformat(),
            "label": result.window.label,
        },
        "algorithm": result.algorithm,
        "total_decks": result.total_decks,
        "pipeline_version": result.pipeline_version,
        "generated_at": result.generated_at.isoformat(),
        "archetypes": [
            {
                "cluster_id": a.cluster_id,
                "deck_count": a.deck_count,
                "share": a.share,
                "representative_mainboard": a.representative_mainboard,
                "representative_sideboard": a.representative_sideboard,
            }
            for a in result.archetypes
        ],
    }


def push(result: ClusteringRunResult, api_url: str, token: str) -> bool:
    """POSTs `result` to `barrins_api`. Returns whether it succeeded.

    Never raises on failure -- logs and returns `False`, same
    fail-and-wait-for-the-next-tick philosophy as the Scripture sweep (no
    retry/backoff here either, this is a scheduled job, not a
    request-response path with a caller waiting on the outcome).
    """
    endpoint = api_url.rstrip("/") + _INGEST_PATH
    headers = {"X-Karn-Token": token}
    try:
        response = requests.post(
            endpoint, json=_payload(result), headers=headers, timeout=30
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.exception(
            "push failed for window %s (%d archetypes)",
            result.window.label,
            len(result.archetypes),
        )
        return False
    logger.info(
        "pushed window %s: %d decks, %d archetypes",
        result.window.label,
        result.total_decks,
        len(result.archetypes),
    )
    return True
