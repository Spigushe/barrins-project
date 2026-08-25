"""Shared fixtures for the Tolaria News BFF tests."""

import uuid
from datetime import date

import pytest

from app.models.mtgjson import Card, MTGSet
from app.models.scripture import (
    BSDeck,
    BSDeckBoard,
    BSDeckCard,
    BSRound,
    BSRoundMatch,
    BSSource,
    BSStanding,
    BSTournament,
)

BASE = "/bff/tolaria-news"


@pytest.fixture()
async def mtg_cards(db_session) -> None:
    """Real-shaped `mj_cards` rows the deck-card join resolves against."""
    mtg_set = MTGSet(
        code="TST",
        name="Test Set",
        release_date=date(2026, 1, 1),
        type="expansion",
        base_set_size=10,
        total_set_size=10,
        keyrune_code="tst",
    )
    db_session.add(mtg_set)
    await db_session.flush()

    db_session.add_all(
        [
            Card(
                id=uuid.uuid4(),
                set_code="TST",
                name="Sol Ring",
                type_line="Artifact",
                mana_cost="{1}",
                mana_value=1,
                color_identity=[],
                rarity="uncommon",
                number="1",
                scryfall_id="sol-ring-scryfall-id",
            ),
            Card(
                id=uuid.uuid4(),
                set_code="TST",
                name="Tymna the Weaver",
                type_line="Legendary Creature — Human Warrior",
                mana_cost="{1}{W}{B}",
                mana_value=3,
                color_identity=["W", "B"],
                rarity="rare",
                number="2",
                scryfall_id="tymna-scryfall-id",
            ),
        ]
    )
    await db_session.commit()


@pytest.fixture()
async def duel_commander_tournament(db_session) -> BSTournament:
    t = BSTournament(
        source=BSSource.mtgtop8,
        date=date(2026, 4, 7),
        name="CDF DC 2026 Main Event",
        url="https://mtgtop8.com/event?e=87792&f=EDH",
        format="Duel Commander",
        players=1,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest.fixture()
async def duel_commander_deck(
    db_session, duel_commander_tournament: BSTournament, mtg_cards: None
) -> BSDeck:
    deck = BSDeck(
        tournament_id=duel_commander_tournament.id,
        date=duel_commander_tournament.date,
        player="A. Nakamura",
        result="1",
        anchor_uri=f"{duel_commander_tournament.url}#deck_anakamura",
    )
    db_session.add(deck)
    await db_session.flush()
    db_session.add_all(
        [
            BSDeckCard(
                deck_id=deck.id,
                board=BSDeckBoard.mainboard,
                card_name="Sol Ring",
                count=1,
            ),
            BSDeckCard(
                deck_id=deck.id,
                board=BSDeckBoard.sideboard,
                card_name="Tymna the Weaver",
                count=1,
            ),
        ]
    )
    await db_session.commit()
    await db_session.refresh(deck)
    return deck


@pytest.fixture()
async def bracket(db_session, duel_commander_tournament: BSTournament) -> None:
    semis = BSRound(
        tournament_id=duel_commander_tournament.id,
        round_name="Semifinals",
        sequence=0,
    )
    finals = BSRound(
        tournament_id=duel_commander_tournament.id,
        round_name="Finals",
        sequence=1,
    )
    db_session.add_all([semis, finals])
    await db_session.flush()
    db_session.add_all(
        [
            BSRoundMatch(
                round_id=semis.id,
                player_1="A. Nakamura",
                player_2="B. Costa",
                result="2-1",
            ),
            BSRoundMatch(
                round_id=finals.id,
                player_1="A. Nakamura",
                player_2="C. Dubois",
                result="2-0",
            ),
        ]
    )
    await db_session.commit()


@pytest.fixture()
async def standings(db_session, duel_commander_tournament: BSTournament) -> None:
    db_session.add_all(
        [
            BSStanding(
                tournament_id=duel_commander_tournament.id,
                rank=rank,
                player=f"Player {rank}",
                points=10 - rank,
                wins=3,
                losses=rank,
                draws=0,
                omwp=0.5,
                gwp=0.5,
                ogwp=0.5,
            )
            for rank in range(1, 4)
        ]
    )
    await db_session.commit()
