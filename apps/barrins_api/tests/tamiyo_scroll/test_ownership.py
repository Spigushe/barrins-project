"""Tests for the read-only sharing model (resolve_owner).

Cf. docs/tamiyo_scroll_tracker/00_plan_general.md, Option B: `owner_id` is
never accepted by write routes, even when explicitly passed.
"""

from httpx import AsyncClient

from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


class TestReadAccessWithoutSharing:
    async def test_non_shared_owner_returns_403(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        resp = await client.get(
            f"{BASE}/personal-decks?owner_id={other_user.id}",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 403

    async def test_unknown_owner_id_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.get(
            f"{BASE}/personal-decks?owner_id=00000000-0000-0000-0000-000000000000",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404


class TestReadAccessWithSharing:
    async def test_shared_owner_data_is_readable(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        other_headers = auth_headers(other_user)
        await client.patch(
            f"{BASE}/me/settings", json={"data_shared": True}, headers=other_headers
        )
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Other's Deck"},
            headers=other_headers,
        )

        resp = await client.get(
            f"{BASE}/personal-decks?owner_id={other_user.id}",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 200
        assert [d["name"] for d in resp.json()] == ["Other's Deck"]

    async def test_own_data_readable_without_owner_param(
        self, client: AsyncClient, owner_user: User
    ):
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "My Deck"},
            headers=auth_headers(owner_user),
        )
        resp = await client.get(
            f"{BASE}/personal-decks?owner_id={owner_user.id}",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 200
        assert [d["name"] for d in resp.json()] == ["My Deck"]


class TestWriteRoutesIgnoreOwnerParam:
    async def test_owner_id_on_write_route_has_no_effect(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        """`owner_id` in the query string on a write route has no effect.

        The parameter isn't declared anywhere in the route signature ->
        FastAPI ignores it and the resource is created for `current_user`,
        never for `owner_id`.
        """
        other_headers = auth_headers(other_user)
        await client.patch(
            f"{BASE}/me/settings", json={"data_shared": True}, headers=other_headers
        )

        resp = await client.post(
            f"{BASE}/personal-decks?owner_id={other_user.id}",
            json={"name": "Sneaky Deck"},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 201

        owner_decks = await client.get(
            f"{BASE}/personal-decks", headers=auth_headers(owner_user)
        )
        assert [d["name"] for d in owner_decks.json()] == ["Sneaky Deck"]

        other_decks = await client.get(f"{BASE}/personal-decks", headers=other_headers)
        assert other_decks.json() == []
