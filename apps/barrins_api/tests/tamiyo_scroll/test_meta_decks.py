"""Tests for /bff/tamiyo-scroll/meta-decks."""

from httpx import AsyncClient

from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers

_PAYLOAD = {
    "name": "Burn",
    "tier": 1.5,
    "category": "aggro",
    "top8": 3,
    "presence": 12,
    "expected": "as_expected",
}


async def _create_meta_deck(client: AsyncClient, user: User, **overrides) -> dict:
    payload = {**_PAYLOAD, **overrides}
    resp = await client.post(
        f"{BASE}/meta-decks", json=payload, headers=auth_headers(user)
    )
    assert resp.status_code == 201
    return resp.json()


class TestListMetaDecks:
    async def test_empty_by_default(self, client: AsyncClient, owner_user: User):
        resp = await client.get(f"{BASE}/meta-decks", headers=auth_headers(owner_user))
        assert resp.json() == []

    async def test_excludes_archived_by_default(
        self, client: AsyncClient, owner_user: User
    ):
        deck = await _create_meta_deck(client, owner_user)
        headers = auth_headers(owner_user)
        await client.delete(f"{BASE}/meta-decks/{deck['id']}", headers=headers)

        resp = await client.get(f"{BASE}/meta-decks", headers=headers)
        assert resp.json() == []

        resp = await client.get(
            f"{BASE}/meta-decks?include_archived=true", headers=headers
        )
        assert len(resp.json()) == 1


class TestCreateMetaDeck:
    async def test_creates_deck_with_conversion(
        self, client: AsyncClient, owner_user: User
    ):
        deck = await _create_meta_deck(client, owner_user, top8=3, presence=12)
        assert deck["conversion"] == 25.0

    async def test_zero_presence_conversion_is_none(
        self, client: AsyncClient, owner_user: User
    ):
        deck = await _create_meta_deck(client, owner_user, top8=0, presence=0)
        assert deck["conversion"] is None

    async def test_invalid_tier_step_returns_422(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.post(
            f"{BASE}/meta-decks",
            json={**_PAYLOAD, "tier": 1.3},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422

    async def test_invalid_category_returns_422(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.post(
            f"{BASE}/meta-decks",
            json={**_PAYLOAD, "category": "not-a-category"},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422


class TestUpdateMetaDeck:
    async def test_updates_fields(self, client: AsyncClient, owner_user: User):
        deck = await _create_meta_deck(client, owner_user)
        headers = auth_headers(owner_user)
        resp = await client.put(
            f"{BASE}/meta-decks/{deck['id']}",
            json={**_PAYLOAD, "name": "Burn Renamed", "tier": 2.0},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Burn Renamed"
        assert resp.json()["tier"] == 2.0

    async def test_foreign_deck_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        deck = await _create_meta_deck(client, owner_user)
        resp = await client.put(
            f"{BASE}/meta-decks/{deck['id']}",
            json=_PAYLOAD,
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestArchiveMetaDeck:
    async def test_archives_own_deck(self, client: AsyncClient, owner_user: User):
        deck = await _create_meta_deck(client, owner_user)
        resp = await client.delete(
            f"{BASE}/meta-decks/{deck['id']}", headers=auth_headers(owner_user)
        )
        assert resp.status_code == 204

    async def test_foreign_deck_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        deck = await _create_meta_deck(client, owner_user)
        resp = await client.delete(
            f"{BASE}/meta-decks/{deck['id']}", headers=auth_headers(other_user)
        )
        assert resp.status_code == 404
