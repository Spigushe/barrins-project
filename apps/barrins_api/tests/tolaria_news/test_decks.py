"""Tests for /bff/tolaria-news/decks/{id} -- card resolution + commander derivation."""

import uuid

from httpx import AsyncClient

from app.models.scripture import BSDeck, BSDeckBoard, BSDeckCard

from .conftest import BASE


class TestDeckDetail:
    async def test_resolves_mainboard_cards_against_mj_cards(
        self, client: AsyncClient, duel_commander_deck: BSDeck
    ) -> None:
        resp = await client.get(f"{BASE}/decks/{duel_commander_deck.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["mainboard"] == [
            {
                "name": "Sol Ring",
                "qty": 1,
                "cmc": 1.0,
                "type_line": "Artifact",
                "scryfall_id": "sol-ring-scryfall-id",
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
        names = {c["name"]: c for c in resp.json()["data"]["mainboard"]}
        unresolved = names["Some Unresolvable Card Name"]
        assert unresolved["qty"] == 2
        assert unresolved["cmc"] is None
        assert unresolved["scryfall_id"] is None

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
