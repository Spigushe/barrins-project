"""Tests for /bff/tolaria-news/telemetry -- public, no auth required.

The banlist-period boundary/effective-time math itself is independently
tested in `libs/dc_calendar` -- these tests only check the endpoint wires
that math through correctly, not the math's own correctness.
"""

from datetime import date

from httpx import AsyncClient

from app.models.scripture import BSTournament

from .conftest import BASE


class TestGetTelemetry:
    async def test_returns_a_well_formed_season_and_countdown(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get(f"{BASE}/telemetry")
        assert resp.status_code == 200
        data = resp.json()["data"]

        season = data["season"]
        assert season["kind"] == "banlist_period"
        assert date.fromisoformat(season["date_from"]) <= date.fromisoformat(
            season["date_to"]
        )
        assert 1 <= data["season_number"] <= 6
        assert data["season_year"] >= 2016  # the format's 20-life era start

        next_banlist_at = data["next_banlist_at"]
        assert "+" in next_banlist_at or next_banlist_at.endswith("Z")  # UTC offset
        assert date.fromisoformat(next_banlist_at[:10]) > date.fromisoformat(
            season["date_to"]
        )

    async def test_reports_last_sync_via_meta(
        self, client: AsyncClient, duel_commander_tournament: BSTournament
    ) -> None:
        resp = await client.get(f"{BASE}/telemetry")
        assert resp.status_code == 200
        assert resp.json()["meta"]["source_synced_at"] is not None

    async def test_no_authorization_header_required(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/telemetry")
        assert resp.status_code == 200
        assert "Authorization" not in resp.request.headers
