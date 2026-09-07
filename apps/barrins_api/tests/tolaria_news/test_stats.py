"""Tests for /bff/tolaria-news/stats -- public, no auth required."""

from datetime import date

from httpx import AsyncClient

from app.models.scripture import (
    BSDeck,
    BSDeckBoard,
    BSDeckCard,
    BSSource,
    BSTournament,
)

from .conftest import BASE


async def _deck_with_sideboard(
    db_session,
    tournament: BSTournament,
    player: str,
    sideboard: list[str],
) -> BSDeck:
    """A deck carrying `sideboard` as its command zone (Duel Commander has
    no traditional sideboard) plus one filler mainboard card."""
    deck = BSDeck(
        tournament_id=tournament.id,
        date=tournament.date,
        player=player,
        result=None,
        anchor_uri=f"{tournament.url}#deck_{player.replace(' ', '_').lower()}",
    )
    db_session.add(deck)
    await db_session.flush()
    db_session.add(
        BSDeckCard(
            deck_id=deck.id,
            board=BSDeckBoard.mainboard,
            card_name="Sol Ring",
            count=1,
        )
    )
    db_session.add_all(
        BSDeckCard(
            deck_id=deck.id,
            board=BSDeckBoard.sideboard,
            card_name=name,
            count=1,
        )
        for name in sideboard
    )
    await db_session.commit()
    return deck


class TestGetStats:
    async def test_zero_when_no_data(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == {
            "tournaments_count": 0,
            "decks_count": 0,
            "command_zones_count": 0,
        }

    async def test_counts_in_scope_tournaments_and_decks(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        resp = await client.get(f"{BASE}/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == {
            "tournaments_count": 1,
            "decks_count": 1,
            "command_zones_count": 1,
        }

    async def test_excludes_non_duel_commander_tournaments(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        legacy = BSTournament(
            source=BSSource.mtgo,
            date=date(2026, 4, 9),
            name="Legacy Challenge",
            url="https://mtgo.com/decklist/legacy-challenge",
            format="Legacy",
            players=1,
        )
        db_session.add(legacy)
        await db_session.flush()
        db_session.add(
            BSDeck(
                tournament_id=legacy.id,
                date=legacy.date,
                player="Legacy Pilot",
                result=None,
                anchor_uri=f"{legacy.url}#deck_legacy",
            )
        )
        await db_session.commit()

        resp = await client.get(f"{BASE}/stats")
        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "tournaments_count": 1,
            "decks_count": 1,
            "command_zones_count": 1,
        }

    async def test_excludes_pre_floor_tournaments(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        pre_floor = BSTournament(
            source=BSSource.mtgo,
            date=date(2010, 1, 1),  # before EARLIEST_RELEVANT_DATE (2015-11-01)
            name="Pre-floor Event",
            url="https://mtgo.com/decklist/pre-floor",
            format="Duel Commander",
            players=1,
        )
        db_session.add(pre_floor)
        await db_session.flush()
        db_session.add(
            BSDeck(
                tournament_id=pre_floor.id,
                date=pre_floor.date,
                player="Old Pilot",
                result=None,
                anchor_uri=f"{pre_floor.url}#deck_old",
            )
        )
        await db_session.commit()

        resp = await client.get(f"{BASE}/stats")
        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "tournaments_count": 1,
            "decks_count": 1,
            "command_zones_count": 1,
        }

    async def test_no_authorization_header_required(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/stats")
        assert resp.status_code == 200
        assert "Authorization" not in resp.request.headers


class TestCommandZonesCount:
    async def test_partner_pair_is_one_zone_distinct_from_solo(
        self,
        client: AsyncClient,
        db_session,
        duel_commander_tournament: BSTournament,
    ) -> None:
        await _deck_with_sideboard(
            db_session, duel_commander_tournament, "Solo Pilot", ["Tymna the Weaver"]
        )
        await _deck_with_sideboard(
            db_session,
            duel_commander_tournament,
            "Pair Pilot A",
            ["Thrasios, Triton Hero", "Tymna the Weaver"],
        )
        await _deck_with_sideboard(
            db_session,
            duel_commander_tournament,
            "Pair Pilot B",
            ["Tymna the Weaver", "Thrasios, Triton Hero"],  # same pair, other order
        )

        data = (await client.get(f"{BASE}/stats")).json()["data"]
        # Solo Tymna and the Tymna+Thrasios pair are two zones; the two
        # pair decks share one regardless of card order.
        assert data == {
            "tournaments_count": 1,
            "decks_count": 3,
            "command_zones_count": 2,
        }

    async def test_deck_without_sideboard_does_not_contribute(
        self,
        client: AsyncClient,
        db_session,
        duel_commander_tournament: BSTournament,
    ) -> None:
        deck = BSDeck(
            tournament_id=duel_commander_tournament.id,
            date=duel_commander_tournament.date,
            player="No Commander Parsed",
            result=None,
            anchor_uri=f"{duel_commander_tournament.url}#deck_nc",
        )
        db_session.add(deck)
        await db_session.flush()
        db_session.add(
            BSDeckCard(
                deck_id=deck.id,
                board=BSDeckBoard.mainboard,
                card_name="Sol Ring",
                count=1,
            )
        )
        await db_session.commit()

        data = (await client.get(f"{BASE}/stats")).json()["data"]
        assert data["decks_count"] == 1
        assert data["command_zones_count"] == 0

    async def test_ignores_sideboards_of_out_of_scope_decks(
        self,
        client: AsyncClient,
        db_session,
        duel_commander_deck: BSDeck,
    ) -> None:
        legacy = BSTournament(
            source=BSSource.mtgo,
            date=date(2026, 4, 9),
            name="Legacy Challenge",
            url="https://mtgo.com/decklist/legacy-challenge",
            format="Legacy",
            players=1,
        )
        db_session.add(legacy)
        await db_session.flush()
        await _deck_with_sideboard(
            db_session, legacy, "Legacy Pilot", ["Force of Will", "Daze"]
        )

        data = (await client.get(f"{BASE}/stats")).json()["data"]
        # Only the in-scope Duel Commander deck's zone is counted.
        assert data["command_zones_count"] == 1
