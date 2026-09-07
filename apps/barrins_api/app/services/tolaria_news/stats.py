"""Landing-page headline counts backing the Tolaria News BFF."""

from sqlalchemy import distinct, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scripture import BSDeck, BSDeckBoard, BSDeckCard, BSTournament
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

    # Distinct command zones: for each in-scope deck, the ordered array of
    # its sideboard card names (the commander, or a partner pair -- Duel
    # Commander has no traditional sideboard, see
    # `app.services.tolaria_news.decks`'s module docstring), then how many
    # distinct such arrays exist. Decks with no sideboard row drop out of
    # the GROUP BY on their own. Names are already canonicalized at
    # Scripture ingest, so no `mj_cards` join is needed. A malformed
    # sideboard (a bad scrape with 3+ cards) counts as its own zone --
    # acceptable noise for a headline figure.
    deck_zones = (
        select(
            func.array_agg(
                aggregate_order_by(BSDeckCard.card_name, BSDeckCard.card_name.asc())
            ).label("zone")
        )
        .select_from(BSDeckCard)
        .join(BSDeck, BSDeckCard.deck_id == BSDeck.id)
        .where(
            BSDeckCard.board == BSDeckBoard.sideboard,
            BSDeck.tournament_id.in_(select(tournament_ids.c.id)),
        )
        .group_by(BSDeckCard.deck_id)
        .subquery()
    )
    command_zones_count = (
        await session.execute(select(func.count(distinct(deck_zones.c.zone))))
    ).scalar_one()

    return StatsResponse(
        tournaments_count=tournaments_count,
        decks_count=decks_count,
        command_zones_count=command_zones_count,
    )
