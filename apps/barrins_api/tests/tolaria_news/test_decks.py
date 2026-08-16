"""Tests for /bff/tolaria-news/decks -- global index, and /decks/{id} --
card resolution + commander derivation."""

import uuid
from datetime import date, timedelta

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


class TestTrendingCommanders:
    async def _tournament(self, db_session, *, event_date: date) -> BSTournament:
        t = BSTournament(
            source=BSSource.mtgo,
            date=event_date,
            name=f"Trend Event {event_date.isoformat()}",
            url=f"https://mtgo.com/decklist/trend-{uuid.uuid4()}",
            format="Duel Commander",
            players=1,
        )
        db_session.add(t)
        await db_session.flush()
        return t

    async def _deck(
        self,
        db_session,
        tournament: BSTournament,
        *,
        player: str,
        deck_date: date,
        commanders: list[str],
    ) -> BSDeck:
        deck = BSDeck(
            tournament_id=tournament.id,
            date=deck_date,
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

    async def test_default_mode_is_rolling_30d_ranked_by_deck_count(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        today = date.today()
        tournament = await self._tournament(db_session, event_date=today)
        await self._deck(
            db_session,
            tournament,
            player="P1",
            deck_date=today,
            commanders=["Tymna the Weaver"],
        )
        await self._deck(
            db_session,
            tournament,
            player="P2",
            deck_date=today,
            commanders=["Tymna the Weaver"],
        )
        await self._deck(
            db_session,
            tournament,
            player="P3",
            deck_date=today,
            commanders=["Sol Ring"],
        )

        resp = await client.get(f"{BASE}/decks/commanders/trending")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["window"]["kind"] == "rolling_30d"
        series = body["series"]
        assert series[0]["commanders"][0]["name"] == "Tymna the Weaver"
        assert series[0]["total_deck_count"] == 2
        assert series[1]["commanders"][0]["name"] == "Sol Ring"
        assert series[1]["total_deck_count"] == 1

    async def test_partner_pair_groups_as_one_series_regardless_of_card_order(
        self, client: AsyncClient, db_session, mtg_cards
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

        today = date.today()
        tournament = await self._tournament(db_session, event_date=today)
        await self._deck(
            db_session,
            tournament,
            player="P1",
            deck_date=today,
            commanders=["Tymna the Weaver", "Kraum, Ludevic's Opus"],
        )
        await self._deck(
            db_session,
            tournament,
            player="P2",
            deck_date=today,
            commanders=["Kraum, Ludevic's Opus", "Tymna the Weaver"],  # reversed order
        )

        resp = await client.get(f"{BASE}/decks/commanders/trending")
        body = resp.json()["data"]
        assert len(body["series"]) == 1
        assert body["series"][0]["total_deck_count"] == 2
        assert {c["name"] for c in body["series"][0]["commanders"]} == {
            "Tymna the Weaver",
            "Kraum, Ludevic's Opus",
        }

    async def test_caps_at_top_ten(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        today = date.today()
        tournament = await self._tournament(db_session, event_date=today)
        extra_cards = [
            Card(
                id=uuid.uuid4(),
                set_code="TST",
                name=f"Trend Card {i}",
                type_line="Legendary Creature — Test",
                mana_cost="{1}",
                mana_value=1,
                color_identity=[],
                rarity="common",
                number=str(10 + i),
                scryfall_id=f"trend-card-{i}-scryfall-id",
            )
            for i in range(9)
        ]
        db_session.add_all(extra_cards)
        await db_session.commit()

        all_names = ["Tymna the Weaver", "Sol Ring", *(c.name for c in extra_cards)]
        for name in all_names:
            await self._deck(
                db_session,
                tournament,
                player=f"Pilot {name}",
                deck_date=today,
                commanders=[name],
            )

        resp = await client.get(f"{BASE}/decks/commanders/trending")
        assert len(resp.json()["data"]["series"]) == 10

    async def test_bucket_with_no_decks_reports_null_not_zero(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        today = date.today()
        tournament = await self._tournament(db_session, event_date=today)
        await self._deck(
            db_session,
            tournament,
            player="P1",
            deck_date=today,
            commanders=["Tymna the Weaver"],
        )

        resp = await client.get(f"{BASE}/decks/commanders/trending")
        points = resp.json()["data"]["series"][0]["points"]
        assert any(p["deck_count"] is None for p in points)
        assert any(p["deck_count"] == 1 for p in points)

    async def test_excludes_non_duel_commander_tournaments(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        today = date.today()
        legacy_tournament = BSTournament(
            source=BSSource.mtgo,
            date=today,
            name="Legacy Trend Challenge",
            url=f"https://mtgo.com/decklist/legacy-trend-{uuid.uuid4()}",
            format="Legacy",
            players=1,
        )
        db_session.add(legacy_tournament)
        await db_session.flush()
        await self._deck(
            db_session,
            legacy_tournament,
            player="Legacy Pilot",
            deck_date=today,
            commanders=["Tymna the Weaver"],
        )

        resp = await client.get(f"{BASE}/decks/commanders/trending")
        assert resp.json()["data"]["series"] == []

    async def test_banlist_period_offset_shifts_to_an_earlier_period(
        self, client: AsyncClient
    ) -> None:
        current = await client.get(
            f"{BASE}/decks/commanders/trending", params={"mode": "banlist_period"}
        )
        previous = await client.get(
            f"{BASE}/decks/commanders/trending",
            params={"mode": "banlist_period", "period_offset": 1},
        )
        current_window = current.json()["data"]["window"]
        previous_window = previous.json()["data"]["window"]
        assert current_window["label"] != previous_window["label"]
        assert previous_window["date_to"] < current_window["date_from"]

    async def test_all_time_spans_from_earliest_tournament(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        old_date = date.today() - timedelta(days=400)
        tournament = await self._tournament(db_session, event_date=old_date)
        await self._deck(
            db_session,
            tournament,
            player="Old Pilot",
            deck_date=old_date,
            commanders=["Tymna the Weaver"],
        )

        resp = await client.get(
            f"{BASE}/decks/commanders/trending", params={"mode": "all_time"}
        )
        body = resp.json()["data"]
        assert body["window"]["date_from"] == old_date.isoformat()
        assert len(body["series"][0]["points"]) > 1

    async def test_all_time_with_no_tournaments_returns_empty_series(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get(
            f"{BASE}/decks/commanders/trending", params={"mode": "all_time"}
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["series"] == []

    async def test_custom_mode_requires_date_from(self, client: AsyncClient) -> None:
        resp = await client.get(
            f"{BASE}/decks/commanders/trending", params={"mode": "custom"}
        )
        assert resp.status_code == 400

    async def test_custom_mode_rejects_date_to_before_date_from(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get(
            f"{BASE}/decks/commanders/trending",
            params={
                "mode": "custom",
                "date_from": "2026-05-01",
                "date_to": "2026-04-01",
            },
        )
        assert resp.status_code == 400

    async def test_custom_mode_without_date_to_defaults_to_today(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        today = date.today()
        tournament = await self._tournament(db_session, event_date=today)
        await self._deck(
            db_session,
            tournament,
            player="P1",
            deck_date=today,
            commanders=["Tymna the Weaver"],
        )

        resp = await client.get(
            f"{BASE}/decks/commanders/trending",
            params={"mode": "custom", "date_from": today.isoformat()},
        )
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["window"]["date_from"] == today.isoformat()
        assert body["window"]["date_to"] == today.isoformat()
        assert body["series"][0]["total_deck_count"] == 1

    async def test_custom_mode_short_range_buckets_weekly(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        today = date.today()
        tournament = await self._tournament(db_session, event_date=today)
        await self._deck(
            db_session,
            tournament,
            player="P1",
            deck_date=today,
            commanders=["Tymna the Weaver"],
        )

        resp = await client.get(
            f"{BASE}/decks/commanders/trending",
            params={
                "mode": "custom",
                "date_from": (today - timedelta(days=14)).isoformat(),
                "date_to": today.isoformat(),
            },
        )
        body = resp.json()["data"]
        points = body["series"][0]["points"]
        # 15 inclusive days -> 3 weekly buckets (7 + 7 + 1).
        assert len(points) == 3

    async def test_custom_mode_long_range_buckets_by_banlist_period(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        today = date.today()
        old_date = today - timedelta(days=400)
        tournament = await self._tournament(db_session, event_date=old_date)
        await self._deck(
            db_session,
            tournament,
            player="Old Pilot",
            deck_date=old_date,
            commanders=["Tymna the Weaver"],
        )

        resp = await client.get(
            f"{BASE}/decks/commanders/trending",
            params={"mode": "custom", "date_from": old_date.isoformat()},
        )
        body = resp.json()["data"]
        assert body["window"]["date_from"] == old_date.isoformat()
        assert body["window"]["date_to"] == today.isoformat()
        # A 400+ day span buckets by banlist period, not by week.
        assert 1 < len(body["series"][0]["points"]) < 20


class TestStaples:
    async def _tournament(
        self,
        db_session,
        *,
        event_date: date,
        source: BSSource = BSSource.mtgtop8,
        players: int = 1,
        name: str = "Staples Event",
        format_: str = "Duel Commander",
    ) -> BSTournament:
        t = BSTournament(
            source=source,
            date=event_date,
            name=name,
            url=f"https://example.com/{uuid.uuid4()}",
            format=format_,
            players=players,
        )
        db_session.add(t)
        await db_session.commit()
        await db_session.refresh(t)
        return t

    async def _deck(
        self,
        db_session,
        tournament: BSTournament,
        *,
        player: str,
        mainboard: tuple[str, ...] = (),
    ) -> BSDeck:
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
                    board=BSDeckBoard.mainboard,
                    card_name=name,
                    count=1,
                )
                for name in mainboard
            ]
        )
        await db_session.commit()
        await db_session.refresh(deck)
        return deck

    async def test_narrow_window_pools_every_tournament_regardless_of_size(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        small_mtgtop8 = await self._tournament(
            db_session, event_date=date(2026, 1, 3), source=BSSource.mtgtop8, players=8
        )
        await self._deck(
            db_session, small_mtgtop8, player="P1", mainboard=("Sol Ring",)
        )
        small_mtgo = await self._tournament(
            db_session,
            event_date=date(2026, 1, 5),
            source=BSSource.mtgo,
            players=0,
            name="Duel Commander League",
        )
        await self._deck(db_session, small_mtgo, player="P2", mainboard=("Sol Ring",))

        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-01-10"},  # 9-day span
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["tournaments_considered"] == 2
        assert data["decks_considered"] == 2
        assert data["rows"][0]["name"] == "Sol Ring"
        assert data["rows"][0]["deck_count"] == 2
        assert data["rows"][0]["percentage"] == 100.0

    async def test_wide_window_gates_mtgtop8_by_player_count_but_not_mtgo(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        below = await self._tournament(
            db_session,
            event_date=date(2025, 6, 1),
            source=BSSource.mtgtop8,
            players=50,
            name="Below Threshold",
        )
        await self._deck(db_session, below, player="P1", mainboard=("Sol Ring",))
        boundary = await self._tournament(
            db_session,
            event_date=date(2025, 6, 15),
            source=BSSource.mtgtop8,
            players=80,
            name="Exactly At Threshold",
        )
        await self._deck(db_session, boundary, player="P2", mainboard=("Sol Ring",))
        above = await self._tournament(
            db_session,
            event_date=date(2025, 7, 1),
            source=BSSource.mtgtop8,
            players=81,
            name="Above Threshold",
        )
        await self._deck(db_session, above, player="P3", mainboard=("Sol Ring",))
        league = await self._tournament(
            db_session,
            event_date=date(2025, 8, 1),
            source=BSSource.mtgo,
            players=0,
            name="Duel Commander League",
        )
        await self._deck(db_session, league, player="P4", mainboard=("Sol Ring",))

        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2025-01-01", "date_to": "2026-06-01"},  # >65 days
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        # "above" (81 players) and "league" (mtgo, any player count) qualify;
        # "below" (50) and "boundary" (exactly 80, not > 80) don't.
        assert data["tournaments_considered"] == 2
        assert data["decks_considered"] == 2

    async def test_span_boundary_at_65_days(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        small = await self._tournament(
            db_session, event_date=date(2026, 1, 2), source=BSSource.mtgtop8, players=5
        )
        await self._deck(db_session, small, player="P1", mainboard=("Sol Ring",))

        ungated = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-03-06"},  # 64-day span
        )
        assert ungated.json()["data"]["tournaments_considered"] == 1

        gated = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-03-07"},  # 65-day span
        )
        assert gated.json()["data"]["tournaments_considered"] == 0

    async def test_mtgtop8_tournament_named_mtgo_is_excluded_as_duplicate(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        mirror = await self._tournament(
            db_session,
            event_date=date(2026, 1, 3),
            source=BSSource.mtgtop8,
            players=200,
            name="Duel Commander MTGO League",
        )
        await self._deck(db_session, mirror, player="P1", mainboard=("Sol Ring",))

        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-01-10"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["tournaments_considered"] == 0
        assert data["rows"] == []

    async def test_tournaments_outside_window_are_excluded(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        outside = await self._tournament(
            db_session, event_date=date(2025, 12, 31), players=200
        )
        await self._deck(db_session, outside, player="P1", mainboard=("Sol Ring",))

        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-01-10"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "date_from": "2026-01-01",
            "date_to": "2026-01-10",
            "tournaments_considered": 0,
            "decks_considered": 0,
            "min_percentage": 65.0,
            "rows": [],
        }

    async def test_non_duel_commander_tournaments_are_excluded(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        legacy = await self._tournament(
            db_session, event_date=date(2026, 1, 3), players=200, format_="Legacy"
        )
        await self._deck(db_session, legacy, player="P1", mainboard=("Sol Ring",))

        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-01-10"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["tournaments_considered"] == 0

    async def test_percentage_is_computed_across_the_pooled_deck_count(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        t1 = await self._tournament(db_session, event_date=date(2026, 1, 3), players=10)
        await self._deck(db_session, t1, player="P1", mainboard=("Sol Ring",))
        await self._deck(db_session, t1, player="P2", mainboard=("Sol Ring",))
        t2 = await self._tournament(db_session, event_date=date(2026, 1, 5), players=10)
        await self._deck(db_session, t2, player="P3", mainboard=("Sol Ring",))
        await self._deck(db_session, t2, player="P4")  # doesn't run it

        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-01-10"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["tournaments_considered"] == 2
        assert data["decks_considered"] == 4
        assert data["min_percentage"] == 65.0
        assert data["rows"] == [
            {
                "name": "Sol Ring",
                "cmc": 1.0,
                "type_line": "Artifact",
                "scryfall_id": "sol-ring-scryfall-id",
                "mana_cost": "{1}",
                "text": None,
                "keywords": [],
                "deck_count": 3,
                "percentage": 75.0,
            }
        ]

    async def test_falls_back_to_45_percent_when_65_percent_yields_no_rows(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        t1 = await self._tournament(db_session, event_date=date(2026, 1, 3), players=10)
        await self._deck(db_session, t1, player="P1", mainboard=("Sol Ring",))
        await self._deck(db_session, t1, player="P2")  # Sol Ring in 1 of 2 -> 50%

        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-01-10"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["min_percentage"] == 45.0
        assert data["rows"] == [
            {
                "name": "Sol Ring",
                "cmc": 1.0,
                "type_line": "Artifact",
                "scryfall_id": "sol-ring-scryfall-id",
                "mana_cost": "{1}",
                "text": None,
                "keywords": [],
                "deck_count": 1,
                "percentage": 50.0,
            }
        ]

    async def test_min_percentage_and_fallback_are_overridable_via_query_params(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        t1 = await self._tournament(db_session, event_date=date(2026, 1, 3), players=10)
        await self._deck(db_session, t1, player="P1", mainboard=("Sol Ring",))
        await self._deck(db_session, t1, player="P2")  # Sol Ring in 1 of 2 -> 50%

        # Sol Ring's 50% is below the default 65% primary floor (which
        # would normally fall back to 45%) -- passing an explicit 40%
        # primary floor should include it directly, no fallback needed.
        resp = await client.get(
            f"{BASE}/decks/staples",
            params={
                "date_from": "2026-01-01",
                "date_to": "2026-01-10",
                "min_percentage": 40,
                "fallback_min_percentage": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["min_percentage"] == 40.0
        assert [row["name"] for row in data["rows"]] == ["Sol Ring"]

    async def test_reports_the_fallback_floor_even_when_it_also_yields_no_rows(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        t1 = await self._tournament(db_session, event_date=date(2026, 1, 3), players=10)
        await self._deck(db_session, t1, player="P1", mainboard=("Sol Ring",))
        await self._deck(db_session, t1, player="P2")
        await self._deck(db_session, t1, player="P3")
        await self._deck(db_session, t1, player="P4")
        # Sol Ring in 1 of 4 decks -> 25%, below both the 65% primary and
        # the 45% fallback floor -- still empty even after the retry.

        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-01-10"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["min_percentage"] == 45.0
        assert data["rows"] == []

    async def test_card_below_percentage_threshold_is_excluded(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        t1 = await self._tournament(db_session, event_date=date(2026, 1, 3), players=10)
        await self._deck(
            db_session, t1, player="P1", mainboard=("Sol Ring", "Tymna the Weaver")
        )
        await self._deck(db_session, t1, player="P2", mainboard=("Sol Ring",))
        await self._deck(db_session, t1, player="P3", mainboard=("Sol Ring",))
        await self._deck(db_session, t1, player="P4")

        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-01-10"},
        )
        assert resp.status_code == 200
        names = [row["name"] for row in resp.json()["data"]["rows"]]
        assert names == ["Sol Ring"]

    async def test_land_cards_are_excluded(
        self, client: AsyncClient, db_session, mtg_cards
    ) -> None:
        db_session.add(
            Card(
                id=uuid.uuid4(),
                set_code="TST",
                name="Command Tower",
                type_line="Land",
                mana_cost=None,
                mana_value=0,
                color_identity=[],
                rarity="common",
                number="3",
                scryfall_id="command-tower-scryfall-id",
            )
        )
        await db_session.commit()
        t1 = await self._tournament(db_session, event_date=date(2026, 1, 3), players=10)
        await self._deck(
            db_session, t1, player="P1", mainboard=("Sol Ring", "Command Tower")
        )

        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-01-10"},
        )
        assert resp.status_code == 200
        names = [row["name"] for row in resp.json()["data"]["rows"]]
        assert names == ["Sol Ring"]

    async def test_results_are_capped_at_sixty(
        self, client: AsyncClient, db_session
    ) -> None:
        t1 = await self._tournament(db_session, event_date=date(2026, 1, 3), players=10)
        cards = tuple(f"Unique Card {i}" for i in range(61))
        await self._deck(db_session, t1, player="P1", mainboard=cards)

        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-01", "date_to": "2026-01-10"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]["rows"]) == 60

    async def test_date_to_before_date_from_is_400(self, client: AsyncClient) -> None:
        resp = await client.get(
            f"{BASE}/decks/staples",
            params={"date_from": "2026-01-10", "date_to": "2026-01-01"},
        )
        assert resp.status_code == 400

    async def test_missing_params_is_422(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/decks/staples")
        assert resp.status_code == 422
