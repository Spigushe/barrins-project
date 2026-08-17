"""Set of every tournament URL already ingested into `bs_tournaments`.

Backs `GET /internal/scripture/ingested-urls`, read by Barrin's Scripture's
sweep (`--fast-forward`, `--mode full` only) to skip re-POSTing tournaments
that are already upserted -- the POST is idempotent (T2) so re-submitting
them is a correctness no-op, but still pays a full HTTP + DB round trip per
file, which `--fast-forward` avoids for a bulk-replay-sized archive.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scripture import BSTournament


async def fetch_ingested_tournament_urls(session: AsyncSession) -> list[str]:
    """Every `bs_tournaments.url` currently in the database."""
    result = await session.scalars(select(BSTournament.url))
    return list(result.all())
