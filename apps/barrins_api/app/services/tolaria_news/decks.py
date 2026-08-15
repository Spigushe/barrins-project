"""Deck detail queries backing the Tolaria News BFF.

Joins `bs_deck_cards` (T2, raw `card_name` strings) against `mj_cards`
(S8's MTGJSON import) to surface real card data -- `cmc`/`type_line`/
`scryfall_id`/`color_identity` -- instead of bare strings. Reuses
`app.services.scripture.card_resolver`'s name normalization (the same
logic T3's ingestion route already validates scraped names against) so
this doesn't re-implement accent/Unicode folding a second time.

Commander derivation: confirmed against real fixtures (both MTGO and
MTGTop8) that for Duel Commander tournaments, the `sideboard` board of
`bs_deck_cards` holds exactly the commander(s) -- 1 card solo, 2 for a
partner pair -- since Commander has no traditional sideboard zone.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mtgjson import Card
from app.models.scripture import BSDeck, BSDeckBoard, BSDeckCard, BSTournament
from app.schemas.responses_tolaria_news import (
    CommanderRef,
    DeckCardOut,
    DeckCardTypeGroup,
    DeckDetail,
)
from app.services.decklist_sort import decklist_sort_key, group_by_category
from app.services.scripture.card_resolver import resolve_card_name

#: Mirrors `barrins_scripture.schemas.formats.Formats.DUEL_COMMANDER`
#: (the exact string that source stores into `bs_tournaments.format`).
#: Not imported cross-app on purpose -- `barrins_api` doesn't depend on
#: `barrins_scripture`'s package, only on the string it writes.
_DUEL_COMMANDER_FORMAT = "Duel Commander"


async def _resolved_cards(
    session: AsyncSession, card_rows: Sequence[BSDeckCard]
) -> dict[uuid.UUID, Card | None]:
    """`{bs_deck_cards.id: matching mj_cards row or None}` for every row.

    One resolver pass (per-name, cached) + one batched `mj_cards` query,
    not N+1 queries per card line. When a name resolves to a printing
    that exists more than once (multiple sets), an arbitrary matching
    printing is used -- `cmc`/`type_line`/`color_identity` are the same
    across printings, `scryfall_id` isn't (picks *a* printing's image,
    not necessarily the newest); acceptable for v1, not guaranteed
    "preferred art".
    """
    canonical_by_card_id: dict[uuid.UUID, str] = {}
    for card in card_rows:
        canonical = await resolve_card_name(session, card.card_name)
        if canonical is not None:
            canonical_by_card_id[card.id] = canonical

    names = set(canonical_by_card_id.values())
    if not names:
        return dict.fromkeys(c.id for c in card_rows)

    matches = (
        (
            await session.execute(
                select(Card).where(or_(Card.name.in_(names), Card.face_name.in_(names)))
            )
        )
        .scalars()
        .all()
    )
    card_by_name: dict[str, Card] = {}
    for match in matches:
        card_by_name.setdefault(match.name, match)
        if match.face_name:
            card_by_name.setdefault(match.face_name, match)

    return {
        card.id: card_by_name.get(canonical_by_card_id.get(card.id, ""))
        for card in card_rows
    }


def _as_deck_card_out(card: BSDeckCard, resolved: Card | None) -> DeckCardOut:
    return DeckCardOut(
        name=resolved.name if resolved is not None else card.card_name,
        qty=card.count,
        cmc=resolved.mana_value if resolved is not None else None,
        type_line=resolved.type_line if resolved is not None else None,
        scryfall_id=resolved.scryfall_id if resolved is not None else None,
        mana_cost=resolved.mana_cost if resolved is not None else None,
        text=resolved.text if resolved is not None else None,
        keywords=resolved.keywords if resolved is not None else [],
    )


async def get_deck(session: AsyncSession, deck_id: uuid.UUID) -> DeckDetail | None:
    deck = await session.get(BSDeck, deck_id)
    if deck is None:
        return None
    tournament = await session.get(BSTournament, deck.tournament_id)
    assert (
        tournament is not None
    )  # FK guarantees this (bs_decks.tournament_id NOT NULL)

    card_rows = (
        (await session.execute(select(BSDeckCard).where(BSDeckCard.deck_id == deck_id)))
        .scalars()
        .all()
    )
    resolved = await _resolved_cards(session, card_rows)

    sorted_mainboard = sorted(
        (
            _as_deck_card_out(c, resolved[c.id])
            for c in card_rows
            if c.board == BSDeckBoard.mainboard
        ),
        key=lambda c: decklist_sort_key(c.type_line, c.cmc, c.name),
    )
    mainboard = [
        DeckCardTypeGroup(category=category, count=len(group), cards=group)
        for category, group in group_by_category(
            sorted_mainboard, lambda c: c.type_line
        )
    ]

    commanders: list[CommanderRef] = []
    if tournament.format == _DUEL_COMMANDER_FORMAT:
        for c in card_rows:
            if c.board != BSDeckBoard.sideboard:
                continue
            match = resolved[c.id]
            commanders.append(
                CommanderRef(
                    name=match.name if match is not None else c.card_name,
                    scryfall_id=match.scryfall_id if match is not None else None,
                    color_identity=match.color_identity if match is not None else [],
                    mana_cost=match.mana_cost if match is not None else None,
                    text=match.text if match is not None else None,
                    keywords=match.keywords if match is not None else [],
                )
            )

    return DeckDetail(
        id=deck.id,
        tournament_id=deck.tournament_id,
        date=deck.date,
        player=deck.player,
        result=deck.result,
        anchor_uri=deck.anchor_uri,
        notes=deck.notes,
        commanders=commanders,
        mainboard=mainboard,
    )
