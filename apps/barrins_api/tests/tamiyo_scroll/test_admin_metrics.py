"""Tests for the S6 admin usage/metrics dashboard.

Covers both layers: the HTTP route (`app/api/tamiyo_scroll/admin.py`,
`GET /bff/tamiyo-scroll/admin/metrics`) and the underlying aggregation
service (`app/services/metrics/`).
"""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.models.tamiyo_scroll import TSPersonalDeck
from app.models.user import User, UserRole
from app.services.metrics.aggregates import _count_statement
from tests.tamiyo_scroll.conftest import BASE, auth_headers

ADMIN_METRICS_URL = f"{BASE}/admin/metrics"


@pytest.fixture()
async def admin_user(db_session) -> User:
    user = User(
        email="admin@tamiyo-scroll.example.com",
        hashed_password=hash_password("Admin#Pass1word"),
        role=UserRole.admin,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestAdminGate:
    async def test_non_admin_gets_403(self, client: AsyncClient, owner_user: User):
        resp = await client.get(ADMIN_METRICS_URL, headers=auth_headers(owner_user))
        assert resp.status_code == 403

    async def test_unauthenticated_gets_401(self, client: AsyncClient):
        resp = await client.get(ADMIN_METRICS_URL)
        assert resp.status_code == 401


class TestAdminMetrics:
    async def test_admin_sees_correct_aggregate_counts(
        self,
        client: AsyncClient,
        db_session,
        admin_user: User,
        owner_user: User,
        other_user: User,
    ):
        """Seeds two personal decks and two matches across two accounts,
        then asserts the admin dashboard's counts match a manual count."""
        owner_headers = auth_headers(owner_user)
        other_headers = auth_headers(other_user)

        deck_a = (
            await client.post(
                f"{BASE}/personal-decks",
                json={"name": "Mono Red", "game": "magic", "category": "aggro"},
                headers=owner_headers,
            )
        ).json()
        deck_b = (
            await client.post(
                f"{BASE}/personal-decks",
                json={
                    "name": "Azorius Control",
                    "game": "magic",
                    "category": "control",
                },
                headers=other_headers,
            )
        ).json()

        meta_resp = await client.post(
            f"{BASE}/meta-decks",
            json={
                "name": "Burn",
                "tier": 1.0,
                "category": "aggro",
                "top8": 1,
                "presence": 5,
                "expected": "as_expected",
            },
            headers=owner_headers,
        )
        meta_id = meta_resp.json()["id"]
        other_meta_resp = await client.post(
            f"{BASE}/meta-decks",
            json={
                "name": "Burn",
                "tier": 1.0,
                "category": "aggro",
                "top8": 1,
                "presence": 5,
                "expected": "as_expected",
            },
            headers=other_headers,
        )
        other_meta_id = other_meta_resp.json()["id"]

        await client.post(
            f"{BASE}/matches",
            json={
                "personal_deck_id": deck_a["id"],
                "opponent_deck_id": meta_id,
                "on_play": True,
                "game1": "win",
                "game2": "loss",
            },
            headers=owner_headers,
        )
        await client.post(
            f"{BASE}/matches",
            json={
                "personal_deck_id": deck_b["id"],
                "opponent_deck_id": other_meta_id,
                "on_play": False,
                "game1": "loss",
                "game2": "loss",
            },
            headers=other_headers,
        )

        resp = await client.get(ADMIN_METRICS_URL, headers=auth_headers(admin_user))
        assert resp.status_code == 200
        body = resp.json()

        # 3 accounts: admin_user + owner_user + other_user.
        assert body["total_accounts"] == {"value": 3, "source": "tamiyo_scroll"}
        assert body["total_personal_decks"] == {"value": 2, "source": "tamiyo_scroll"}
        assert body["total_matches"] == {"value": 2, "source": "tamiyo_scroll"}

    async def test_archived_personal_decks_still_count_as_created(
        self, client: AsyncClient, admin_user: User, owner_user: User
    ):
        """Personal decks soft-delete via `archived_at` (never a SQL DELETE) —
        the total must reflect everything ever created, archived or not."""
        owner_headers = auth_headers(owner_user)
        deck = (
            await client.post(
                f"{BASE}/personal-decks",
                json={"name": "Mono Red", "game": "magic", "category": "aggro"},
                headers=owner_headers,
            )
        ).json()
        await client.delete(
            f"{BASE}/personal-decks/{deck['id']}", headers=owner_headers
        )

        resp = await client.get(ADMIN_METRICS_URL, headers=auth_headers(admin_user))
        assert resp.json()["total_personal_decks"]["value"] == 1


class TestCountStatementShape:
    """Sanity check (not a performance test): the service must query with a
    bare `COUNT(*)`, never something that pulls full row sets into Python
    memory — this would silently regress under real data volume."""

    def test_count_statement_is_a_bare_count_not_a_row_fetch(self):
        stmt = _count_statement(TSPersonalDeck)
        compiled = str(stmt).lower()

        assert "count(*)" in compiled
        # A row-fetching regression (e.g. `select(TSPersonalDeck)`) would
        # select every mapped column instead of a single count(*) column.
        assert "ts_personal_decks.id" not in compiled
        assert "ts_personal_decks.name" not in compiled
