"""Route: `POST /internal/scripture/ingest` (T3).

Private, backend-only route (§1.2, decided 2026-07-25): Barrin's Scripture
never holds a `DATABASE_URL` of its own — every scraped tournament reaches
`bs_*` through this route instead. Called by Barrin's Scripture's periodic
sweep (recent-files ticks, or full-archive bulk replay), never by the
scraper directly (2026-08-07 decision superseding the original
push+maintenance-gate+backoff design — see
docs/project/v2.0.0-bump/t3-scripture-ingestion-pipeline/index.md). A
sweep tick that gets a 5xx here just fails that tick; the next tick
retries the same (idempotent) file, so this route needs no
maintenance-flag special-casing.

Gated by a static shared secret (`X-Scripture-Token`,
`app/dependencies/service_auth.py`), not a user JWT — the caller is
another Barrin's-ecosystem service, not a logged-in user. Not registered
under `/api/v1` (unlike the public/BFF routes) — `/internal/` marks it as
never intended for a browser client.
"""

from fastapi import APIRouter

from app.database.session import DatabaseSession
from app.dependencies.service_auth import ScriptureToken
from app.schemas.scripture_ingest import (
    ResponseScriptureIngest,
    ScriptureIngestRequest,
)
from app.services.scripture.ingester import ingest_scrape

router = APIRouter()


@router.post("/ingest", response_model=ResponseScriptureIngest)
async def ingest(
    payload: ScriptureIngestRequest,
    session: DatabaseSession,
    _scripture_auth: ScriptureToken,
) -> ResponseScriptureIngest:
    """Upsert one scraped tournament (one JSON archive file) into `bs_*`.

    Idempotent — safe to re-submit the same file (a sweep retry, a
    bulk-replay overlapping a previous run, an MTGO decklist edited within
    its ~3-day mutability window, ...) without duplicating rows.
    """
    result = await ingest_scrape(session, payload)
    return ResponseScriptureIngest(
        tournament_id=result.tournament_id,
        decks_upserted=result.decks_upserted,
        deck_cards_upserted=result.deck_cards_upserted,
        rounds_upserted=result.rounds_upserted,
        round_matches_upserted=result.round_matches_upserted,
        standings_upserted=result.standings_upserted,
        skipped_card_names=result.skipped_card_names,
    )
