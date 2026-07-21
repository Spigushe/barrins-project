"""Tests for /bff/tamiyo-scroll/me/settings and /shared-users."""

from httpx import AsyncClient

from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


class TestGetMySettings:
    async def test_creates_default_settings_on_first_access(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.get(f"{BASE}/me/settings", headers=auth_headers(owner_user))
        assert resp.status_code == 200
        body = resp.json()
        assert body["data_shared"] is False
        assert body["active_personal_deck_id"] is None

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get(f"{BASE}/me/settings")
        assert resp.status_code == 401


class TestUpdateMySettings:
    async def test_enables_data_sharing(self, client: AsyncClient, owner_user: User):
        resp = await client.patch(
            f"{BASE}/me/settings",
            json={"data_shared": True},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 200
        assert resp.json()["data_shared"] is True

    async def test_sets_active_personal_deck(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_resp = await client.post(
            f"{BASE}/personal-decks", json={"name": "Mono Red"}, headers=headers
        )
        deck_id = deck_resp.json()["id"]

        resp = await client.patch(
            f"{BASE}/me/settings",
            json={"active_personal_deck_id": deck_id},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["active_personal_deck_id"] == deck_id

    async def test_setting_foreign_deck_as_active_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        other_deck_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Not Yours"},
            headers=auth_headers(other_user),
        )
        other_deck_id = other_deck_resp.json()["id"]

        resp = await client.patch(
            f"{BASE}/me/settings",
            json={"active_personal_deck_id": other_deck_id},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_clearing_active_deck_with_explicit_null(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_resp = await client.post(
            f"{BASE}/personal-decks", json={"name": "Mono Red"}, headers=headers
        )
        deck_id = deck_resp.json()["id"]
        await client.patch(
            f"{BASE}/me/settings",
            json={"active_personal_deck_id": deck_id},
            headers=headers,
        )

        resp = await client.patch(
            f"{BASE}/me/settings",
            json={"active_personal_deck_id": None},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["active_personal_deck_id"] is None

    async def test_omitting_field_does_not_change_it(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        await client.patch(
            f"{BASE}/me/settings", json={"data_shared": True}, headers=headers
        )

        resp = await client.patch(f"{BASE}/me/settings", json={}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data_shared"] is True

    async def test_extra_field_returns_422(self, client: AsyncClient, owner_user: User):
        resp = await client.patch(
            f"{BASE}/me/settings",
            json={"role": "admin"},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422


class TestSharedUsers:
    async def test_excludes_self_and_non_sharing_users(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        resp = await client.get(
            f"{BASE}/shared-users", headers=auth_headers(owner_user)
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_lists_users_who_enabled_sharing(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        await client.patch(
            f"{BASE}/me/settings",
            json={"data_shared": True},
            headers=auth_headers(other_user),
        )

        resp = await client.get(
            f"{BASE}/shared-users", headers=auth_headers(owner_user)
        )
        assert resp.status_code == 200
        emails = [u["email"] for u in resp.json()]
        assert emails == ["other@tamiyo-scroll.example.com"]
