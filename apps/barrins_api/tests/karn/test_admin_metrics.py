"""Tests for the S6 admin Karn Tablets route
(`GET /bff/tamiyo-scroll/admin/metrics/karn-tablets`): admin gate + parity
with the public `/metagame` numbers (ADR-13 -- same `kt_*` tables, same
service).
"""

import pytest
from httpx import AsyncClient

from tests.identity_auth import FakeUser as User
from tests.karn.conftest import INGEST_URL, archetype, headers, payload
from tests.tamiyo_scroll.conftest import BASE, auth_headers

ADMIN_URL = f"{BASE}/admin/metrics/karn-tablets"


@pytest.fixture()
def admin_user() -> User:
    return User(email="admin@karn.example.com", role="admin", username="karn-admin")


@pytest.fixture()
def regular_user() -> User:
    return User(email="user@karn.example.com", role="user", username="karn-user")


class TestAdminGate:
    async def test_unauthenticated_is_401(self, client: AsyncClient):
        resp = await client.get(ADMIN_URL, params={"window": "rolling_30d"})
        assert resp.status_code == 401

    async def test_non_admin_is_403(self, client: AsyncClient, regular_user: User):
        resp = await client.get(
            ADMIN_URL,
            params={"window": "rolling_30d"},
            headers=auth_headers(regular_user),
        )
        assert resp.status_code == 403


class TestAdminData:
    async def test_empty_state(self, client: AsyncClient, admin_user: User):
        resp = await client.get(
            ADMIN_URL,
            params={"window": "banlist_period"},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["window_kind"] == "banlist_period"
        assert body["total_decks"] == 0
        assert body["generated_at"] is None
        assert body["archetypes"] == []

    async def test_matches_public_metagame(self, client: AsyncClient, admin_user: User):
        await client.post(
            INGEST_URL,
            json=payload(
                archetypes=[
                    archetype(1, 40, 60),
                    archetype(2, 20, 60, swap=60, prefix="Other"),
                ]
            ),
            headers=headers(),
        )
        admin = (
            await client.get(
                ADMIN_URL,
                params={"window": "rolling_30d"},
                headers=auth_headers(admin_user),
            )
        ).json()
        public = (
            await client.get(
                "/bff/tolaria-news/metagame", params={"window": "rolling_30d"}
            )
        ).json()["data"]

        assert admin["total_decks"] == 60
        assert [
            (a["id"], a["deck_count"], a["deck_share"]) for a in admin["archetypes"]
        ] == [(a["id"], a["deck_count"], a["deck_share"]) for a in public["archetypes"]]
