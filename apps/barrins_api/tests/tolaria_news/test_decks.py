"""Tests for /bff/tolaria-news/decks -- global index, and /decks/{id} --
card resolution + commander derivation."""

import uuid
from datetime import date

from httpx import AsyncClient

from app.models.mtgjson import Card
from app.models.scripture import BSDeck, BSDeckBoard, BSDeckCard, BSSource, BSTournament

from .conftest import BASE


def _flatten_mainboard(data: dict) -> list[dict]:
    """`mainboard`'s cards, in group order -- for tests that only care
    about resolved card data, not the grouping itself."""
    return [card for group in data["mainboard"] for card in group["cards"]]


class TestListDecks:
    async def _second_deck(self, db_session) -> BSDeck:
        """A deck under a second, later-dated Duel Commander tournament --
        for cross-tournament ordering/filter assertions."""
        tournament = BSTournament(
            source=BSSource.mtgo,
            date=date(2026, 4, 8),
            name="Another Duel Commander event",
            url="https://mtgo.com/decklist/another-event",
            format="Duel Commander",
            players=1,
        )
        db_session.add(tournament)
        await db_session.flush()
        deck = BSDeck(
            tournament_id=tournament.id,
            date=tournament.date,
            player="B. Costa",
            result=None,
            anchor_uri=f"{tournament.url}#deck_costa",
        )
        db_session.add(deck)
        await db_session.commit()
        await db_session.refresh(deck)
        return deck

    async def test_lists_decks_across_tournaments_most_recent_first(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        second_deck = await self._second_deck(db_session)

        resp = await client.get(f"{BASE}/decks")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert [row["id"] for row in data] == [
            str(second_deck.id),
            str(duel_commander_deck.id),
        ]
        assert data[0]["tournament_name"] == "Another Duel Commander event"
        assert data[0]["tournament_source"] == "mtgo"

    async def test_filters_by_player_substring(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        await self._second_deck(db_session)

        resp = await client.get(f"{BASE}/decks", params={"player": "nakamura"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert [row["id"] for row in data] == [str(duel_commander_deck.id)]

    async def test_filters_by_source(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        second_deck = await self._second_deck(db_session)

        resp = await client.get(f"{BASE}/decks", params={"source": "mtgo"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert [row["id"] for row in data] == [str(second_deck.id)]

    async def test_filters_by_date_range(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        await self._second_deck(db_session)

        resp = await client.get(
            f"{BASE}/decks",
            params={"date_from": "2026-04-07", "date_to": "2026-04-07"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert [row["id"] for row in data] == [str(duel_commander_deck.id)]

    async def test_excludes_decks_from_non_duel_commander_tournament(
        self, client: AsyncClient, db_session, duel_commander_tournament: BSTournament
    ) -> None:
        legacy_tournament = BSTournament(
            source=BSSource.mtgo,
            date=date(2026, 4, 9),
            name="Legacy Challenge",
            url="https://mtgo.com/decklist/legacy-challenge",
            format="Legacy",
            players=1,
        )
        db_session.add(legacy_tournament)
        await db_session.flush()
        db_session.add(
            BSDeck(
                tournament_id=legacy_tournament.id,
                date=legacy_tournament.date,
                player="Legacy Pilot",
                result=None,
                anchor_uri=f"{legacy_tournament.url}#deck_legacy",
            )
        )
        await db_session.commit()

        resp = await client.get(f"{BASE}/decks")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_pagination_cursor_advances(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        second_deck = await self._second_deck(db_session)

        first_page = await client.get(f"{BASE}/decks", params={"limit": 1})
        assert first_page.status_code == 200
        first_body = first_page.json()
        assert len(first_body["data"]) == 1
        assert first_body["data"][0]["id"] == str(second_deck.id)  # most recent first
        cursor = first_body["page"]["next_cursor"]
        assert cursor is not None

        second_page = await client.get(
            f"{BASE}/decks", params={"limit": 1, "cursor": cursor}
        )
        second_body = second_page.json()
        assert len(second_body["data"]) == 1
        assert second_body["data"][0]["id"] == str(duel_commander_deck.id)
        assert second_body["page"]["next_cursor"] is None

    async def test_malformed_cursor_is_400(self, client: AsyncClient) -> None:
        resp = await client.get(
            f"{BASE}/decks", params={"cursor": "not-valid-base64!!"}
        )
        assert resp.status_code == 400

    async def test_empty_result_when_no_decks(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/decks")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def _deck_with_commanders(
        self,
        db_session,
        tournament: BSTournament,
        player: str,
        commanders: list[str],
    ) -> BSDeck:
        """A deck under `tournament` whose sideboard is exactly
        `commanders` -- for commander/color filter assertions."""
        deck = BSDeck(
            tournament_id=tournament.id,
            date=tournament.date,
            player=player,
            result=None,
            anchor_uri=f"{tournament.url}#deck_{uuid.uuid4()}",
        )
        db_session.add(deck)
        await db_session.flush()
        db_session.add_all(
            [
                BSDeckCard(
                    deck_id=deck.id,
                    board=BSDeckBoard.sideboard,
                    card_name=name,
                    count=1,
                )
                for name in commanders
            ]
        )
        await db_session.commit()
        await db_session.refresh(deck)
        return deck

    async def test_filters_by_exact_commander_name(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        await self._second_deck(db_session)  # no commander at all

        resp = await client.get(
            f"{BASE}/decks", params={"commander": "Tymna the Weaver"}
        )
        assert resp.status_code == 200
        assert [row["id"] for row in resp.json()["data"]] == [
            str(duel_commander_deck.id)
        ]

    async def test_colors_filter_exact_match_single_commander(
        self, client: AsyncClient, duel_commander_deck: BSDeck
    ) -> None:
        """`duel_commander_deck`'s commander (Tymna the Weaver, from the
        `mtg_cards` fixture) is W/B."""
        resp = await client.get(f"{BASE}/decks", params={"colors": ["W", "B"]})
        assert resp.status_code == 200
        assert [row["id"] for row in resp.json()["data"]] == [
            str(duel_commander_deck.id)
        ]

    async def test_colors_filter_excludes_subset_and_superset(
        self, client: AsyncClient, duel_commander_deck: BSDeck
    ) -> None:
        """Exact match, not "contains"/"any of": a W/B deck matches
        neither a narrower (W only) nor a wider (W/B/U) request."""
        subset = await client.get(f"{BASE}/decks", params={"colors": ["W"]})
        assert subset.json()["data"] == []

        superset = await client.get(f"{BASE}/decks", params={"colors": ["W", "B", "U"]})
        assert superset.json()["data"] == []

    async def test_colors_filter_matches_union_of_partner_commanders(
        self,
        client: AsyncClient,
        db_session,
        duel_commander_tournament: BSTournament,
        mtg_cards,
    ) -> None:
        db_session.add(
            Card(
                id=uuid.uuid4(),
                set_code="TST",
                name="Kraum, Ludevic's Opus",
                type_line="Legendary Creature — Zombie Horror",
                mana_cost="{1}{U}{R}",
                mana_value=3,
                color_identity=["U", "R"],
                rarity="rare",
                number="3",
                scryfall_id="kraum-scryfall-id",
            )
        )
        await db_session.commit()

        partner_deck = await self._deck_with_commanders(
            db_session,
            duel_commander_tournament,
            "Partner Pilot",
            ["Tymna the Weaver", "Kraum, Ludevic's Opus"],
        )

        matches = await client.get(
            f"{BASE}/decks", params={"colors": ["W", "U", "B", "R"]}
        )
        assert [row["id"] for row in matches.json()["data"]] == [str(partner_deck.id)]

        # Dropping one color makes the filter a strict subset of the
        # partner pair's real (W/U/B/R) identity -- still not an exact
        # match, so it's excluded.
        narrower = await client.get(f"{BASE}/decks", params={"colors": ["W", "U", "B"]})
        assert narrower.json()["data"] == []

    async def test_combines_commander_and_colors_filters(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        await self._second_deck(db_session)

        resp = await client.get(
            f"{BASE}/decks",
            params={"commander": "Tymna the Weaver", "colors": ["W", "B"]},
        )
        assert resp.status_code == 200
        assert [row["id"] for row in resp.json()["data"]] == [
            str(duel_commander_deck.id)
        ]

    async def test_colors_filter_paginates_normally(
        self,
        client: AsyncClient,
        db_session,
        duel_commander_tournament: BSTournament,
        duel_commander_deck: BSDeck,
    ) -> None:
        second = await self._deck_with_commanders(
            db_session,
            duel_commander_tournament,
            "Second Tymna Pilot",
            ["Tymna the Weaver"],
        )

        first_page = await client.get(
            f"{BASE}/decks", params={"colors": ["W", "B"], "limit": 1}
        )
        assert first_page.status_code == 200
        first_body = first_page.json()
        assert len(first_body["data"]) == 1
        cursor = first_body["page"]["next_cursor"]
        assert cursor is not None

        second_page = await client.get(
            f"{BASE}/decks", params={"colors": ["W", "B"], "limit": 1, "cursor": cursor}
        )
        second_body = second_page.json()
        assert len(second_body["data"]) == 1
        assert second_body["page"]["next_cursor"] is None
        assert {first_body["data"][0]["id"], second_body["data"][0]["id"]} == {
            str(duel_commander_deck.id),
            str(second.id),
        }


class TestListCommanders:
    async def test_returns_distinct_sorted_commander_names(
        self, client: AsyncClient, duel_commander_deck: BSDeck
    ) -> None:
        resp = await client.get(f"{BASE}/decks/commanders")
        assert resp.status_code == 200
        assert resp.json()["data"] == ["Tymna the Weaver"]

    async def test_excludes_non_duel_commander_tournaments(
        self, client: AsyncClient, db_session
    ) -> None:
        legacy_tournament = BSTournament(
            source=BSSource.mtgo,
            date=date(2026, 4, 9),
            name="Legacy Challenge",
            url="https://mtgo.com/decklist/legacy-challenge-commanders",
            format="Legacy",
            players=1,
        )
        db_session.add(legacy_tournament)
        await db_session.flush()
        deck = BSDeck(
            tournament_id=legacy_tournament.id,
            date=legacy_tournament.date,
            player="Legacy Pilot",
            result=None,
            anchor_uri=f"{legacy_tournament.url}#deck_legacy",
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

        resp = await client.get(f"{BASE}/decks/commanders")
        assert resp.status_code == 200
        assert resp.json()["data"] == []


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
