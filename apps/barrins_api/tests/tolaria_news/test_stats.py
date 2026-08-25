"""Tests for /bff/tolaria-news/stats -- public, no auth required."""

from datetime import date

from httpx import AsyncClient

from app.models.scripture import BSDeck, BSSource, BSTournament

from .conftest import BASE


class TestGetStats:
    async def test_zero_when_no_data(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == {"tournaments_count": 0, "decks_count": 0}

    async def test_counts_in_scope_tournaments_and_decks(
        self, client: AsyncClient, db_session, duel_commander_deck: BSDeck
    ) -> None:
        resp = await client.get(f"{BASE}/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == {"tournaments_count": 1, "decks_count": 1}

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
        assert resp.json()["data"] == {"tournaments_count": 1, "decks_count": 1}

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
        assert resp.json()["data"] == {"tournaments_count": 1, "decks_count": 1}

    async def test_no_authorization_header_required(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/stats")
        assert resp.status_code == 200
        assert "Authorization" not in resp.request.headers
