"""Landing-page headline counts backing the Tolaria News BFF."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scripture import BSDeck, BSTournament
from app.schemas.responses_tolaria_news import StatsResponse
from app.services.tolaria_news.decks import (
    DUEL_COMMANDER_FORMAT,
    EARLIEST_RELEVANT_DATE,
    exclude_mtgtop8_mtgo_mirrors,
)


def _in_scope_tournament_ids():
    return select(BSTournament.id).where(
        BSTournament.format == DUEL_COMMANDER_FORMAT,
        BSTournament.date >= EARLIEST_RELEVANT_DATE,
        exclude_mtgtop8_mtgo_mirrors(),
    )


async def get_stats(session: AsyncSession) -> StatsResponse:
    """Tournaments/decks recorded from `EARLIEST_RELEVANT_DATE` onward --
    same in-scope dataset every other Tolaria News endpoint defaults to,
    so the landing page's headline numbers describe what a visitor
    actually sees browsing the rest of the site."""
    tournament_ids = _in_scope_tournament_ids().subquery()

    tournaments_count = (
        await session.execute(select(func.count()).select_from(tournament_ids))
    ).scalar_one()
    decks_count = (
        await session.execute(
            select(func.count())
            .select_from(BSDeck)
            .where(BSDeck.tournament_id.in_(select(tournament_ids.c.id)))
        )
    ).scalar_one()

    return StatsResponse(
        tournaments_count=tournaments_count,
        decks_count=decks_count,
    )
