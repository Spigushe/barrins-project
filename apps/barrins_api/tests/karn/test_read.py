"""Tests for the public Tolaria News BFF archetype routes (ADR-13, T4
iteration 2): `/metagame`, `/archetypes`, `/trends`.

Window objects use the BFF-wide `WindowOut` shape (`kind`/`date_from`/
`date_to`), not the provisional `apps/tolaria_news/src/schemas/
karnTablets.ts` guess -- that zod file's own docstring says to reconcile
against the real schema once this ships.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.karn.conftest import BFF, INGEST_URL, archetype, headers, payload

_METAGAME_KEYS = {
    "id",
    "name",
    "commanders",
    "deck_count",
    "deck_share",
    "deck_share_delta",
    "momentum",
}
_CARD_KEYS = {"name", "qty", "scryfall_id", "is_land", "is_signature"}


async def _ingest(client: AsyncClient, body: dict) -> None:
    resp = await client.post(INGEST_URL, json=body, headers=headers())
    assert resp.status_code == 200, resp.text


class TestMetagame:
    async def test_empty_state_is_200_with_current_window(self, client: AsyncClient):
        resp = await client.get(f"{BFF}/metagame", params={"window": "rolling_30d"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["format"] == "Duel Commander"
        assert data["window"]["kind"] == "rolling_30d"
        assert data["archetypes"] == []

    async def test_returns_latest_run_sorted_by_deck_count(self, client: AsyncClient):
        base = datetime(2026, 8, 20, 4, 0, tzinfo=UTC)
        await _ingest(
            client,
            payload(
                generated_at=base,
                label="rolling_30d:2026-08-20",
                archetypes=[archetype(1, 10, 10)],
            ),
        )
        await _ingest(
            client,
            payload(
                generated_at=base + timedelta(days=1),
                label="rolling_30d:2026-08-21",
                archetypes=[
                    archetype(1, 15, 60, swap=2),
                    archetype(2, 45, 60, swap=60, prefix="Big"),
                ],
            ),
        )
        resp = await client.get(f"{BFF}/metagame", params={"window": "rolling_30d"})
        archetypes = resp.json()["data"]["archetypes"]
        assert [a["deck_count"] for a in archetypes] == [45, 15]  # latest run only
        assert all(set(a) == _METAGAME_KEYS for a in archetypes)
        assert all(isinstance(a["id"], str) and len(a["id"]) == 36 for a in archetypes)

    async def test_unknown_format_is_empty(self, client: AsyncClient):
        await _ingest(client, payload(archetypes=[archetype(1, 30, 30)]))
        resp = await client.get(
            f"{BFF}/metagame",
            params={"window": "rolling_30d", "format": "Legacy"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["archetypes"] == []

    async def test_no_auth_required(self, client: AsyncClient):
        resp = await client.get(f"{BFF}/metagame", params={"window": "banlist_period"})
        assert resp.status_code == 200

    async def test_archetype_carries_commanders_with_scryfall_id(
        self, client: AsyncClient, karn_reference_cards: None
    ):
        await _ingest(client, payload(archetypes=[archetype(1, 30, 30)]))
        resp = await client.get(f"{BFF}/metagame", params={"window": "rolling_30d"})
        assert resp.status_code == 200
        assert resp.json()["data"]["archetypes"][0]["commanders"] == [
            {"name": "Commander One", "scryfall_id": "commander-one-id"}
        ]


def _archetype(
    cluster_id: int, deck_count: int, mainboard: dict, commander: str
) -> dict:
    return {
        "cluster_id": cluster_id,
        "deck_count": deck_count,
        "share": round(deck_count / 100, 4),
        "representative_mainboard": mainboard,
        "representative_sideboard": {commander: 1},
    }


class TestArchetypes:
    async def test_includes_representative_mainboard(self, client: AsyncClient):
        await _ingest(client, payload(archetypes=[archetype(1, 30, 30)]))
        resp = await client.get(f"{BFF}/archetypes", params={"window": "rolling_30d"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert {
            "format",
            "window",
            "previous_window",
            "next_window",
            "archetypes",
        } == set(data)
        row = data["archetypes"][0]
        assert _METAGAME_KEYS <= set(row)
        cards = row["representative_mainboard"]
        assert cards and all(_CARD_KEYS == set(c) for c in cards)

    async def test_cards_carry_scryfall_land_and_signature_flags(
        self, client: AsyncClient, karn_reference_cards: None
    ):
        # Command Tower is a land in both archetypes (2/2 >= 33%) -> not
        # signature. Snow-Covered Plains is a *basic* land -> never
        # signature, even though unique to archetype A. Gaea's Cradle is a
        # non-basic land unique to archetype A -> signature. Non-lands are
        # always signature.
        await _ingest(
            client,
            payload(
                total_decks=100,
                archetypes=[
                    _archetype(
                        1,
                        60,
                        {
                            "Snow-Covered Plains": 20,
                            "Gaea's Cradle": 1,
                            "Command Tower": 1,
                            "Sol Ring": 1,
                            "Brainstorm": 1,
                        },
                        "Commander One",
                    ),
                    _archetype(
                        2,
                        40,
                        {"Command Tower": 1, "Ponder": 1},
                        "Commander Two",
                    ),
                ],
            ),
        )
        resp = await client.get(f"{BFF}/archetypes", params={"window": "rolling_30d"})
        assert resp.status_code == 200
        arch_a = next(
            a
            for a in resp.json()["data"]["archetypes"]
            if any(
                c["name"] == "Snow-Covered Plains"
                for c in a["representative_mainboard"]
            )
        )
        cards = {c["name"]: c for c in arch_a["representative_mainboard"]}
        assert cards["Sol Ring"]["scryfall_id"] == "sol-ring-id"
        assert cards["Snow-Covered Plains"]["is_land"] is True
        assert cards["Snow-Covered Plains"]["is_signature"] is False  # basic land
        assert cards["Gaea's Cradle"]["is_signature"] is True  # non-basic, unique
        assert cards["Command Tower"]["is_land"] is True
        assert cards["Command Tower"]["is_signature"] is False  # field-wide land
        assert cards["Brainstorm"]["is_signature"] is True  # non-land

    async def test_paginates_with_opaque_cursor(self, client: AsyncClient):
        await _ingest(
            client,
            payload(
                total_decks=100,
                archetypes=[
                    _archetype(1, 50, {"A 1": 1, "A 2": 1}, "Cmd A"),
                    _archetype(2, 30, {"B 1": 1, "B 2": 1}, "Cmd B"),
                    _archetype(3, 20, {"C 1": 1, "C 2": 1}, "Cmd C"),
                ],
            ),
        )
        first = await client.get(
            f"{BFF}/archetypes", params={"window": "rolling_30d", "limit": 2}
        )
        assert first.status_code == 200
        body = first.json()
        assert [a["deck_count"] for a in body["data"]["archetypes"]] == [50, 30]
        assert body["page"]["limit"] == 2
        cursor = body["page"]["next_cursor"]
        assert cursor

        second = await client.get(
            f"{BFF}/archetypes",
            params={"window": "rolling_30d", "limit": 2, "cursor": cursor},
        )
        assert [a["deck_count"] for a in second.json()["data"]["archetypes"]] == [20]
        assert second.json()["page"]["next_cursor"] is None

    async def test_default_page_returns_every_archetype(self, client: AsyncClient):
        await _ingest(client, payload(archetypes=[archetype(1, 30, 30)]))
        resp = await client.get(f"{BFF}/archetypes", params={"window": "rolling_30d"})
        body = resp.json()
        assert len(body["data"]["archetypes"]) == 1
        assert body["page"] == {"next_cursor": None, "limit": 20}

    async def test_malformed_cursor_is_400(self, client: AsyncClient):
        resp = await client.get(
            f"{BFF}/archetypes",
            params={"window": "rolling_30d", "cursor": "not-base64!!"},
        )
        assert resp.status_code == 400


class TestMomentum:
    async def _two_runs(
        self, client: AsyncClient, first: list[dict], second: list[dict]
    ) -> list[dict]:
        base = datetime(2026, 8, 10, 4, 0, tzinfo=UTC)
        await _ingest(
            client,
            payload(
                generated_at=base,
                label="rolling_30d:2026-08-10",
                archetypes=first,
                total_decks=100,
            ),
        )
        await _ingest(
            client,
            payload(
                generated_at=base + timedelta(days=1),
                label="rolling_30d:2026-08-11",
                archetypes=second,
                total_decks=100,
            ),
        )
        resp = await client.get(f"{BFF}/metagame", params={"window": "rolling_30d"})
        assert resp.status_code == 200
        return resp.json()["data"]["archetypes"]

    async def test_no_previous_run_is_stable_with_null_delta(self, client: AsyncClient):
        await _ingest(
            client, payload(archetypes=[archetype(1, 30, 100)], total_decks=100)
        )
        resp = await client.get(f"{BFF}/metagame", params={"window": "rolling_30d"})
        row = resp.json()["data"]["archetypes"][0]
        assert row["momentum"] == "stable"
        assert row["deck_share_delta"] is None

    async def test_rising_when_share_grows_past_band(self, client: AsyncClient):
        rows = await self._two_runs(
            client, [archetype(1, 30, 100)], [archetype(1, 50, 100)]
        )
        assert rows[0]["momentum"] == "rising"
        assert rows[0]["deck_share_delta"] == pytest.approx(0.2, abs=1e-6)

    async def test_falling_when_share_drops_past_band(self, client: AsyncClient):
        rows = await self._two_runs(
            client, [archetype(1, 50, 100)], [archetype(1, 30, 100)]
        )
        assert rows[0]["momentum"] == "falling"
        assert rows[0]["deck_share_delta"] == pytest.approx(-0.2, abs=1e-6)

    async def test_stable_when_move_is_inside_band(self, client: AsyncClient):
        rows = await self._two_runs(
            client, [archetype(1, 30, 100)], [archetype(1, 31, 100)]
        )
        assert rows[0]["momentum"] == "stable"
        assert rows[0]["deck_share_delta"] == pytest.approx(0.01, abs=1e-6)

    async def test_archetype_absent_from_previous_run_is_new(self, client: AsyncClient):
        rows = await self._two_runs(
            client,
            [archetype(1, 30, 100)],
            [
                archetype(1, 30, 100),
                archetype(2, 20, 100, swap=60, prefix="New", commander="Commander Two"),
            ],
        )
        new_row = next(r for r in rows if r["momentum"] == "new")
        assert new_row["deck_share_delta"] is None
        # The archetype carried over from run 1 is not "new".
        assert any(r["momentum"] != "new" for r in rows)


class TestTrends:
    async def test_point_per_run_with_gaps_as_null(self, client: AsyncClient):
        base = datetime(2026, 8, 18, 4, 0, tzinfo=UTC)
        # Run 1: archetype A only.
        await _ingest(
            client,
            payload(
                generated_at=base,
                label="rolling_30d:2026-08-18",
                archetypes=[archetype(1, 20, 20)],
            ),
        )
        # Run 2: archetype A (matched) + a brand-new archetype B.
        await _ingest(
            client,
            payload(
                generated_at=base + timedelta(days=1),
                label="rolling_30d:2026-08-19",
                archetypes=[
                    archetype(1, 25, 45, swap=1),
                    archetype(2, 20, 45, swap=60, prefix="New"),
                ],
            ),
        )
        resp = await client.get(f"{BFF}/trends", params={"window": "rolling_30d"})
        assert resp.status_code == 200
        trends = {t["archetype_name"]: t for t in resp.json()["data"]}
        assert len(trends) == 2
        for trend in trends.values():
            assert [p["window"]["kind"] for p in trend["points"]] == [
                "rolling_30d",
                "rolling_30d",
            ]
        # The archetype that only appeared in run 2 has a null first point.
        newcomer = next(
            t for t in trends.values() if t["points"][0]["deck_share"] is None
        )
        assert newcomer["points"][1]["deck_share"] is not None

    async def test_empty_when_no_runs(self, client: AsyncClient):
        resp = await client.get(f"{BFF}/trends", params={"window": "rolling_30d"})
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_empty_when_latest_run_has_no_archetypes(self, client: AsyncClient):
        """A quiet window (the pipeline pushes a run with zero
        archetypes) is a valid outcome, not an error."""
        await _ingest(client, payload(archetypes=[], total_decks=0))
        for route in ("metagame", "archetypes", "trends"):
            resp = await client.get(f"{BFF}/{route}", params={"window": "rolling_30d"})
            assert resp.status_code == 200
            body = resp.json()["data"]
            assert (body if route == "trends" else body["archetypes"]) == []


class TestWindowNavigation:
    @staticmethod
    def _period(day_from: str, day_to: str) -> dict:
        return {
            "kind": "banlist_period",
            "date_from": day_from,
            "date_to": day_to,
            "label": f"banlist_period:{day_from}_{day_to}",
        }

    async def _three_periods(self, client: AsyncClient) -> list[dict]:
        periods = [
            self._period("2025-01-28", "2025-03-24"),
            self._period("2025-03-25", "2025-05-26"),
            self._period("2025-05-27", "2025-07-28"),
        ]
        base = datetime(2026, 8, 1, tzinfo=UTC)
        for i, period in enumerate(periods):
            await _ingest(
                client,
                payload(
                    kind="banlist_period",
                    label=period["label"],
                    date_from=period["date_from"],
                    date_to=period["date_to"],
                    generated_at=base + timedelta(days=i),
                    archetypes=[archetype(1, 30 + i, 100)],
                    total_decks=100,
                ),
            )
        return periods

    async def test_latest_window_has_previous_but_no_next(self, client: AsyncClient):
        periods = await self._three_periods(client)
        resp = await client.get(f"{BFF}/metagame", params={"window": "banlist_period"})
        data = resp.json()["data"]
        assert data["window"]["label"] == periods[2]["label"]
        assert data["previous_window"]["label"] == periods[1]["label"]
        assert data["next_window"] is None

    async def test_at_steps_to_a_past_window_with_both_neighbours(
        self, client: AsyncClient
    ):
        periods = await self._three_periods(client)
        resp = await client.get(
            f"{BFF}/metagame",
            params={"window": "banlist_period", "at": periods[1]["label"]},
        )
        data = resp.json()["data"]
        assert data["window"]["label"] == periods[1]["label"]
        assert data["previous_window"]["label"] == periods[0]["label"]
        assert data["next_window"]["label"] == periods[2]["label"]

    async def test_oldest_window_has_no_previous_and_stable_momentum(
        self, client: AsyncClient
    ):
        periods = await self._three_periods(client)
        resp = await client.get(
            f"{BFF}/metagame",
            params={"window": "banlist_period", "at": periods[0]["label"]},
        )
        data = resp.json()["data"]
        assert data["previous_window"] is None
        assert all(a["momentum"] == "stable" for a in data["archetypes"])
        assert all(a["deck_share_delta"] is None for a in data["archetypes"])

    async def test_archetypes_route_carries_the_same_stepper(self, client: AsyncClient):
        periods = await self._three_periods(client)
        resp = await client.get(
            f"{BFF}/archetypes",
            params={"window": "banlist_period", "at": periods[1]["label"]},
        )
        data = resp.json()["data"]
        assert data["window"]["label"] == periods[1]["label"]
        assert data["previous_window"]["label"] == periods[0]["label"]
        assert data["next_window"]["label"] == periods[2]["label"]

    async def test_unknown_at_label_is_404(self, client: AsyncClient):
        await self._three_periods(client)
        for route in ("metagame", "archetypes"):
            resp = await client.get(
                f"{BFF}/{route}",
                params={"window": "banlist_period", "at": "banlist_period:nope"},
            )
            assert resp.status_code == 404
