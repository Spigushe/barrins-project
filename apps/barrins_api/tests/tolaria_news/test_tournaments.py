"""Tests for /bff/tolaria-news/tournaments* -- public, no auth required."""

import uuid
from datetime import date

from httpx import AsyncClient

from app.models.scripture import BSSource, BSTournament

from .conftest import BASE


class TestListTournaments:
    async def test_returns_real_data_with_no_authorization_header(
        self, client: AsyncClient, duel_commander_tournament: BSTournament
    ) -> None:
        resp = await client.get(f"{BASE}/tournaments")
        assert resp.status_code == 200
        body = resp.json()
        assert [t["id"] for t in body["data"]] == [str(duel_commander_tournament.id)]
        assert body["meta"]["source_synced_at"] is not None
        assert body["page"]["limit"] == 20

    async def test_filters_by_source(
        self, client: AsyncClient, duel_commander_tournament: BSTournament
    ) -> None:
        resp = await client.get(f"{BASE}/tournaments", params={"source": "mtgo"})
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_pagination_cursor_advances(
        self, client: AsyncClient, db_session, duel_commander_tournament
    ) -> None:
        second = BSTournament(
            source=BSSource.mtgo,
            date=date(2026, 4, 8),
            name="Another Duel Commander event",
            url="https://mtgo.com/decklist/another-event",
            format="Duel Commander",
            players=1,
        )
        db_session.add(second)
        await db_session.commit()

        first_page = await client.get(f"{BASE}/tournaments", params={"limit": 1})
        assert first_page.status_code == 200
        first_body = first_page.json()
        assert len(first_body["data"]) == 1
        assert first_body["data"][0]["id"] == str(second.id)  # most recent date first
        cursor = first_body["page"]["next_cursor"]
        assert cursor is not None

        second_page = await client.get(
            f"{BASE}/tournaments", params={"limit": 1, "cursor": cursor}
        )
        second_body = second_page.json()
        assert len(second_body["data"]) == 1
        assert second_body["data"][0]["id"] == str(duel_commander_tournament.id)
        assert second_body["page"]["next_cursor"] is None

    async def test_malformed_cursor_is_400(self, client: AsyncClient) -> None:
        resp = await client.get(
            f"{BASE}/tournaments", params={"cursor": "not-valid-base64!!"}
        )
        assert resp.status_code == 400


class TestTournamentDetail:
    async def test_detail_includes_counts(
        self,
        client: AsyncClient,
        duel_commander_tournament: BSTournament,
        duel_commander_deck,
        standings,
    ) -> None:
        resp = await client.get(f"{BASE}/tournaments/{duel_commander_tournament.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["deck_count"] == 1
        assert data["standing_count"] == 3

    async def test_unknown_id_is_404(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/tournaments/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestTournamentDecksAndStandings:
    async def test_lists_decks(
        self,
        client: AsyncClient,
        duel_commander_tournament: BSTournament,
        duel_commander_deck,
    ) -> None:
        resp = await client.get(
            f"{BASE}/tournaments/{duel_commander_tournament.id}/decks"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["player"] == "A. Nakamura"

    async def test_lists_standings_ordered_by_rank(
        self, client: AsyncClient, duel_commander_tournament: BSTournament, standings
    ) -> None:
        resp = await client.get(
            f"{BASE}/tournaments/{duel_commander_tournament.id}/standings"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert [row["rank"] for row in data] == [1, 2, 3]


class TestNoAuthRequired:
    """Mirrors T4's own UAT concern: a copy-paste from Tamiyo Scroll's
    router could silently add a CurrentUser dependency here -- every
    route must stay reachable with no Authorization header at all."""

    async def test_every_route_ignores_missing_authorization(
        self,
        client: AsyncClient,
        duel_commander_tournament: BSTournament,
        duel_commander_deck,
        standings,
    ) -> None:
        tid = duel_commander_tournament.id
        for path in (
            "/tournaments",
            f"/tournaments/{tid}",
            f"/tournaments/{tid}/decks",
            f"/tournaments/{tid}/standings",
            f"/decks/{duel_commander_deck.id}",
        ):
            resp = await client.get(f"{BASE}{path}")
            assert resp.status_code == 200, path
            assert "Authorization" not in resp.request.headers
