"""Route: `POST /internal/karn/ingest` (ADR-13).

Private, backend-only route: the Karn Tablets clustering job
(`apps/karn_tablets`) has no Postgres credential of its own and no
inbound API — it reads `bs_*`/`mj_cards` through a read-only DB user and
pushes each run's result here, the same arrangement Barrin's Scripture
uses for `POST /internal/scripture/ingest` (ADR-5).

Gated by a static shared secret (`X-Karn-Token`,
`app/dependencies/service_auth.py`), not a user JWT — the caller is a
scheduled job, not a logged-in user, and there is no human caller, so
there is no admin-JWT fallback. Not registered under `/api/v1` — the
`/internal/` prefix marks it as never intended for a browser client.
"""

from fastapi import APIRouter

from app.database.session import DatabaseSession
from app.dependencies.service_auth import KarnToken
from app.schemas.karn_ingest import KarnIngestRequest, ResponseKarnIngest
from app.services.karn.ingester import ingest_run

router = APIRouter()


@router.post("/ingest", response_model=ResponseKarnIngest)
async def ingest(
    payload: KarnIngestRequest,
    session: DatabaseSession,
    _karn_auth: KarnToken,
) -> ResponseKarnIngest:
    """Persist one clustering run into `kt_*`.

    Each cluster in the payload is matched to a stable archetype identity
    (`kt_archetypes`) by representative-decklist similarity. Idempotent on
    an exact re-push of the same `(format, window, generated_at)`; a
    re-run with a later `generated_at` is stored as a new run and becomes
    the one reads return.
    """
    result = await ingest_run(session, payload)
    return ResponseKarnIngest(
        run_id=result.run_id,
        archetypes_matched=result.archetypes_matched,
        archetypes_created=result.archetypes_created,
    )
