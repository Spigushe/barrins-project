"""Tests for /bff/tamiyo-scroll/personal-decks and its sub-resources."""

from httpx import AsyncClient

from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


async def _create_deck(client: AsyncClient, user: User, name: str = "Mono Red") -> str:
    resp = await client.post(
        f"{BASE}/personal-decks", json={"name": name}, headers=auth_headers(user)
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestListPersonalDecks:
    async def test_empty_by_default(self, client: AsyncClient, owner_user: User):
        resp = await client.get(
            f"{BASE}/personal-decks", headers=auth_headers(owner_user)
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_lists_own_decks(self, client: AsyncClient, owner_user: User):
        await _create_deck(client, owner_user, "Mono Red")
        resp = await client.get(
            f"{BASE}/personal-decks", headers=auth_headers(owner_user)
        )
        assert [d["name"] for d in resp.json()] == ["Mono Red"]

    async def test_excludes_archived_by_default(
        self, client: AsyncClient, owner_user: User
    ):
        deck_id = await _create_deck(client, owner_user)
        headers = auth_headers(owner_user)
        await client.delete(f"{BASE}/personal-decks/{deck_id}", headers=headers)

        resp = await client.get(f"{BASE}/personal-decks", headers=headers)
        assert resp.json() == []

        resp = await client.get(
            f"{BASE}/personal-decks?include_archived=true", headers=headers
        )
        assert len(resp.json()) == 1
        assert resp.json()[0]["archived_at"] is not None

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get(f"{BASE}/personal-decks")
        assert resp.status_code == 401


class TestCreatePersonalDeck:
    async def test_creates_deck(self, client: AsyncClient, owner_user: User):
        resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Boros Aggro"},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Boros Aggro"
        assert body["archived_at"] is None

    async def test_blank_name_returns_422(self, client: AsyncClient, owner_user: User):
        resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": ""},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422


class TestArchivePersonalDeck:
    async def test_archives_own_deck(self, client: AsyncClient, owner_user: User):
        deck_id = await _create_deck(client, owner_user)
        resp = await client.delete(
            f"{BASE}/personal-decks/{deck_id}", headers=auth_headers(owner_user)
        )
        assert resp.status_code == 204

    async def test_foreign_deck_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        deck_id = await _create_deck(client, owner_user)
        resp = await client.delete(
            f"{BASE}/personal-decks/{deck_id}", headers=auth_headers(other_user)
        )
        assert resp.status_code == 404

    async def test_unknown_deck_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.delete(
            f"{BASE}/personal-decks/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404


class TestDecklistVersions:
    async def test_create_first_version_is_v1(
        self, client: AsyncClient, owner_user: User
    ):
        deck_id = await _create_deck(client, owner_user)
        headers = auth_headers(owner_user)
        resp = await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": "4 Lightning Bolt"},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["version"] == 1
        assert body["source"] == "manual"

    async def test_second_version_increments(
        self, client: AsyncClient, owner_user: User
    ):
        deck_id = await _create_deck(client, owner_user)
        headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": "v1 content"},
            headers=headers,
        )
        resp = await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": "v2 content"},
            headers=headers,
        )
        assert resp.json()["version"] == 2

    async def test_list_versions_newest_first(
        self, client: AsyncClient, owner_user: User
    ):
        deck_id = await _create_deck(client, owner_user)
        headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": "v1"},
            headers=headers,
        )
        await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": "v2"},
            headers=headers,
        )
        resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/versions", headers=headers
        )
        assert [v["version"] for v in resp.json()] == [2, 1]

    async def test_moxfield_import_creates_placeholder_content(
        self, client: AsyncClient, owner_user: User
    ):
        deck_id = await _create_deck(client, owner_user)
        headers = auth_headers(owner_user)
        resp = await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions/import-moxfield",
            json={"moxfield_url": "https://moxfield.com/decks/abc123"},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["source"] == "moxfield_import"
        assert "https://moxfield.com/decks/abc123" in body["content"]

    async def test_delete_version(self, client: AsyncClient, owner_user: User):
        deck_id = await _create_deck(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": "v1"},
            headers=headers,
        )
        version_id = create_resp.json()["id"]

        resp = await client.delete(
            f"{BASE}/personal-decks/{deck_id}/versions/{version_id}", headers=headers
        )
        assert resp.status_code == 204

        list_resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/versions", headers=headers
        )
        assert list_resp.json() == []

    async def test_delete_unknown_version_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        deck_id = await _create_deck(client, owner_user)
        resp = await client.delete(
            f"{BASE}/personal-decks/{deck_id}/versions/"
            "00000000-0000-0000-0000-000000000000",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_foreign_deck_versions_return_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        deck_id = await _create_deck(client, owner_user)
        resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/versions",
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestDecklistView:
    async def test_no_version_returns_empty_list(
        self, client: AsyncClient, owner_user: User
    ):
        deck_id = await _create_deck(client, owner_user)
        resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/decklist-view",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_colors_lines_from_card_tests(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_id = await _create_deck(client, owner_user)
        await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": "4 Lightning Bolt\n2 Duress"},
            headers=headers,
        )
        await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": deck_id,
                "tester": "Alice",
                "card_name": "Lightning Bolt",
                "rating": 5,
            },
            headers=headers,
        )
        await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": deck_id,
                "tester": "Bob",
                "card_name": "Duress",
                "rating": 1,
            },
            headers=headers,
        )

        resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/decklist-view", headers=headers
        )
        assert resp.status_code == 200
        lines = {line["line"]: line["status"] for line in resp.json()}
        assert lines == {
            "4 Lightning Bolt": "validated",
            "2 Duress": "rejected",
        }

    async def test_ignores_card_tests_from_other_personal_decks(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_id = await _create_deck(client, owner_user)
        other_deck_id = await _create_deck(client, owner_user, name="Other Deck")
        await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": "4 Lightning Bolt"},
            headers=headers,
        )
        await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": other_deck_id,
                "tester": "Alice",
                "card_name": "Lightning Bolt",
                "rating": 5,
            },
            headers=headers,
        )

        resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/decklist-view", headers=headers
        )
        assert resp.status_code == 200
        lines = {line["line"]: line["status"] for line in resp.json()}
        assert lines == {"4 Lightning Bolt": "neutral"}

    async def test_uses_latest_version_only(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_id = await _create_deck(client, owner_user)
        await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": "old content"},
            headers=headers,
        )
        await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": "new content"},
            headers=headers,
        )
        resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/decklist-view", headers=headers
        )
        assert [line["line"] for line in resp.json()] == ["new content"]
