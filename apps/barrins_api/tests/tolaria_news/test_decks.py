"""Tests for /bff/tolaria-news/decks/{id} -- card resolution + commander derivation."""

import uuid

from httpx import AsyncClient

from app.models.mtgjson import Card
from app.models.scripture import BSDeck, BSDeckBoard, BSDeckCard

from .conftest import BASE


def _flatten_mainboard(data: dict) -> list[dict]:
    """`mainboard`'s cards, in group order -- for tests that only care
    about resolved card data, not the grouping itself."""
    return [card for group in data["mainboard"] for card in group["cards"]]


class TestDeckDetail:
    async def test_resolves_mainboard_cards_against_mj_cards(
        self, client: AsyncClient, duel_commander_deck: BSDeck
    ) -> None:
        resp = await client.get(f"{BASE}/decks/{duel_commander_deck.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["mainboard"] == [
            {
                "category": "artifact",
                "count": 1,
                "cards": [
                    {
                        "name": "Sol Ring",
                        "qty": 1,
                        "cmc": 1.0,
                        "type_line": "Artifact",
                        "scryfall_id": "sol-ring-scryfall-id",
                        "mana_cost": "{1}",
                        "text": None,
                        "keywords": [],
                    }
                ],
            }
        ]

    async def test_derives_commander_from_sideboard_on_duel_commander(
        self, client: AsyncClient, duel_commander_deck: BSDeck
    ) -> None:
        resp = await client.get(f"{BASE}/decks/{duel_commander_deck.id}")
        assert resp.status_code == 200
        commanders = resp.json()["data"]["commanders"]
        assert len(commanders) == 1
        assert commanders[0]["name"] == "Tymna the Weaver"
        assert commanders[0]["color_identity"] == ["W", "B"]
        assert commanders[0]["mana_cost"] == "{1}{W}{B}"
        assert commanders[0]["text"] is None
        assert commanders[0]["keywords"] == []

    async def test_unresolved_card_name_falls_back_to_raw_string(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        db_session.add(
            BSDeckCard(
                deck_id=duel_commander_deck.id,
                board=BSDeckBoard.mainboard,
                card_name="Some Unresolvable Card Name",
                count=2,
            )
        )
        await db_session.commit()

        resp = await client.get(f"{BASE}/decks/{duel_commander_deck.id}")
        assert resp.status_code == 200
        names = {c["name"]: c for c in _flatten_mainboard(resp.json()["data"])}
        unresolved = names["Some Unresolvable Card Name"]
        assert unresolved["qty"] == 2
        assert unresolved["cmc"] is None
        assert unresolved["scryfall_id"] is None
        # Unresolved -> no `type_line` to categorize -> falls into "other".
        other_group = next(
            g for g in resp.json()["data"]["mainboard"] if g["category"] == "other"
        )
        assert other_group["count"] == 1

    async def test_groups_mainboard_by_type_then_sorts_by_cmc_then_name(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        """Duel Commander display order: grouped into type sections
        (planeswalker, battle, creature, ...), each
        sorted by mana value then name -- a creature (however cheap) always
        groups before a planeswalker's more expensive artifact/land
        neighbors, and `mainboard` already has "Sol Ring" (Artifact, mv1)
        from the fixture to sort against."""
        db_session.add_all(
            [
                Card(
                    id=uuid.uuid4(),
                    set_code="TST",
                    name="Nissa Test",
                    type_line="Legendary Planeswalker — Nissa",
                    mana_cost=None,
                    mana_value=5,
                    color_identity=[],
                    rarity="mythic",
                    number="90",
                    scryfall_id="nissa-test-scryfall-id",
                ),
                Card(
                    id=uuid.uuid4(),
                    set_code="TST",
                    name="Zeta Low",
                    type_line="Creature — Beast",
                    mana_cost=None,
                    mana_value=1,
                    color_identity=[],
                    rarity="common",
                    number="91",
                    scryfall_id="zeta-low-scryfall-id",
                ),
                Card(
                    id=uuid.uuid4(),
                    set_code="TST",
                    name="Alpha High",
                    type_line="Creature — Beast",
                    mana_cost=None,
                    mana_value=5,
                    color_identity=[],
                    rarity="common",
                    number="92",
                    scryfall_id="alpha-high-scryfall-id",
                ),
            ]
        )
        db_session.add_all(
            [
                BSDeckCard(
                    deck_id=duel_commander_deck.id,
                    board=BSDeckBoard.mainboard,
                    card_name=name,
                    count=1,
                )
                for name in ("Nissa Test", "Zeta Low", "Alpha High")
            ]
        )
        await db_session.commit()

        resp = await client.get(f"{BASE}/decks/{duel_commander_deck.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert [(g["category"], g["count"]) for g in data["mainboard"]] == [
            ("planeswalker", 1),
            ("creature", 2),
            ("artifact", 1),
        ]
        assert [c["name"] for c in _flatten_mainboard(data)] == [
            "Nissa Test",  # planeswalker
            "Zeta Low",  # creature, mv1
            "Alpha High",  # creature, mv5
            "Sol Ring",  # artifact
        ]

    async def test_non_commander_format_has_no_commanders(
        self, client: AsyncClient, db_session, duel_commander_tournament, mtg_cards
    ) -> None:
        duel_commander_tournament.format = "Legacy"
        db_session.add(duel_commander_tournament)
        await db_session.commit()

        deck = BSDeck(
            tournament_id=duel_commander_tournament.id,
            date=duel_commander_tournament.date,
            player="Legacy Pilot",
            result=None,
            anchor_uri=f"{duel_commander_tournament.url}#deck_legacy",
        )
        db_session.add(deck)
        await db_session.flush()
        db_session.add(
            BSDeckCard(
                deck_id=deck.id,
                board=BSDeckBoard.sideboard,
                card_name="Sol Ring",
                count=1,
            )
        )
        await db_session.commit()
        await db_session.refresh(deck)

        resp = await client.get(f"{BASE}/decks/{deck.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["commanders"] == []

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/decks/{uuid.uuid4()}")
        assert resp.status_code == 404
