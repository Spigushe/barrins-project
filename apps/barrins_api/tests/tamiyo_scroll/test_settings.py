"""Tests for /bff/tamiyo-scroll/me/settings."""

from httpx import AsyncClient

from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


class TestGetMySettings:
    async def test_creates_default_settings_on_first_access(
        self, client: AsyncClient, owner_user: User
    ):
        """Sharing is opt-out (defaults True); receiving stays opt-in
        (defaults False) — decided 2026-07-30. Auto-archive is opted-in by
        default with a 2-version gap (S14 item 9, revised 2026-08-24)."""
        resp = await client.get(f"{BASE}/me/settings", headers=auth_headers(owner_user))
        assert resp.status_code == 200
        body = resp.json()
        assert body["data_shared"] is True
        assert body["receive_shared_data"] is False
        assert body["active_personal_deck_id"] is None
        assert body["metagame_roster_scope"] == "game"
        assert body["auto_archive_stale_sessions"] is True
        assert body["auto_archive_decklist_version_gap"] == 2

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

    async def test_enables_receiving_shared_data(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.patch(
            f"{BASE}/me/settings",
            json={"receive_shared_data": True},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 200
        assert resp.json()["receive_shared_data"] is True

    async def test_sharing_on_does_not_force_receiving_on(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        resp = await client.patch(
            f"{BASE}/me/settings", json={"data_shared": True}, headers=headers
        )
        assert resp.json()["receive_shared_data"] is False

        resp = await client.patch(
            f"{BASE}/me/settings", json={"receive_shared_data": True}, headers=headers
        )
        assert resp.json()["data_shared"] is True
        assert resp.json()["receive_shared_data"] is True

    async def test_enabling_receive_without_share_returns_422(
        self, client: AsyncClient, owner_user: User
    ):
        """Decided 2026-07-30: receiving requires sharing on the same
        account (distinct from the existing cross-account check on
        GET /shared-users)."""
        headers = auth_headers(owner_user)
        await client.patch(
            f"{BASE}/me/settings", json={"data_shared": False}, headers=headers
        )

        resp = await client.patch(
            f"{BASE}/me/settings", json={"receive_shared_data": True}, headers=headers
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["message"] == "receive_requires_share"

    async def test_disabling_share_while_receive_is_on_returns_422(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        await client.patch(
            f"{BASE}/me/settings",
            json={"data_shared": True, "receive_shared_data": True},
            headers=headers,
        )

        resp = await client.patch(
            f"{BASE}/me/settings", json={"data_shared": False}, headers=headers
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["message"] == "receive_requires_share"

    async def test_disabling_both_together_succeeds(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        await client.patch(
            f"{BASE}/me/settings",
            json={"data_shared": True, "receive_shared_data": True},
            headers=headers,
        )

        resp = await client.patch(
            f"{BASE}/me/settings",
            json={"data_shared": False, "receive_shared_data": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data_shared"] is False
        assert resp.json()["receive_shared_data"] is False

    async def test_sets_active_personal_deck(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Mono Red", "game": "magic", "category": "aggro"},
            headers=headers,
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
            json={"name": "Not Yours", "game": "magic", "category": "midrange"},
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
            f"{BASE}/personal-decks",
            json={"name": "Mono Red", "game": "magic", "category": "aggro"},
            headers=headers,
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

    async def test_sets_metagame_roster_scope(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        resp = await client.patch(
            f"{BASE}/me/settings",
            json={"metagame_roster_scope": "personal_deck"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["metagame_roster_scope"] == "personal_deck"

        resp = await client.patch(f"{BASE}/me/settings", json={}, headers=headers)
        assert resp.json()["metagame_roster_scope"] == "personal_deck"

    async def test_invalid_metagame_roster_scope_returns_422(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.patch(
            f"{BASE}/me/settings",
            json={"metagame_roster_scope": "not-a-scope"},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422

    async def test_extra_field_returns_422(self, client: AsyncClient, owner_user: User):
        resp = await client.patch(
            f"{BASE}/me/settings",
            json={"role": "admin"},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422
