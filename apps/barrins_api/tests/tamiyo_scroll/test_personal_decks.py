"""Tests for /bff/tamiyo-scroll/personal-decks and its sub-resources."""

import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.tamiyo_scroll import TSPersonalDecklistVersion
from app.models.user import User
from app.services.moxfield import get_moxfield_client
from app.services.moxfield.base import MoxfieldDeckFetch
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

    async def test_moxfield_import_creates_version_from_client(
        self, client: AsyncClient, owner_user: User
    ):
        class _FakeMoxfieldClient:
            async def fetch_decklist(self, deck_url: str) -> MoxfieldDeckFetch:
                return MoxfieldDeckFetch(
                    content="4 Lightning Bolt\n1 Sol Ring",
                    raw_data={"lastUpdatedAtUtc": "2026-07-29T11:54:52.473Z"},
                )

        app.dependency_overrides[get_moxfield_client] = lambda: _FakeMoxfieldClient()
        try:
            deck_id = await _create_deck(client, owner_user)
            headers = auth_headers(owner_user)
            resp = await client.post(
                f"{BASE}/personal-decks/{deck_id}/versions/import-moxfield",
                json={"moxfield_url": "https://moxfield.com/decks/abc123"},
                headers=headers,
            )
        finally:
            app.dependency_overrides.pop(get_moxfield_client, None)

        assert resp.status_code == 201
        body = resp.json()
        assert body["source"] == "moxfield_import"
        assert body["content"] == "4 Lightning Bolt\n1 Sol Ring"
        # First import for this deck — nothing to compare against yet.
        assert body["moxfield_deck_changed_since_last_import"] is None

    async def test_moxfield_import_flags_staleness_when_deck_changed(
        self, client: AsyncClient, owner_user: User
    ):
        class _FakeMoxfieldClient:
            def __init__(self) -> None:
                self.calls = 0

            async def fetch_decklist(self, deck_url: str) -> MoxfieldDeckFetch:
                self.calls += 1
                last_updated = (
                    "2026-07-29T11:54:52.473Z"
                    if self.calls == 1
                    else "2026-07-30T09:00:00.000Z"
                )
                return MoxfieldDeckFetch(
                    content=f"1 Sol Ring (v{self.calls})",
                    raw_data={"lastUpdatedAtUtc": last_updated},
                )

        fake_client = _FakeMoxfieldClient()
        app.dependency_overrides[get_moxfield_client] = lambda: fake_client
        try:
            deck_id = await _create_deck(client, owner_user)
            headers = auth_headers(owner_user)
            payload = {"moxfield_url": "https://moxfield.com/decks/abc123"}
            first = await client.post(
                f"{BASE}/personal-decks/{deck_id}/versions/import-moxfield",
                json=payload,
                headers=headers,
            )
            second = await client.post(
                f"{BASE}/personal-decks/{deck_id}/versions/import-moxfield",
                json=payload,
                headers=headers,
            )
        finally:
            app.dependency_overrides.pop(get_moxfield_client, None)

        assert first.json()["moxfield_deck_changed_since_last_import"] is None
        assert second.json()["moxfield_deck_changed_since_last_import"] is True

    async def test_moxfield_import_flags_no_change_when_deck_unchanged(
        self, client: AsyncClient, owner_user: User
    ):
        class _FakeMoxfieldClient:
            async def fetch_decklist(self, deck_url: str) -> MoxfieldDeckFetch:
                return MoxfieldDeckFetch(
                    content="1 Sol Ring",
                    raw_data={"lastUpdatedAtUtc": "2026-07-29T11:54:52.473Z"},
                )

        app.dependency_overrides[get_moxfield_client] = lambda: _FakeMoxfieldClient()
        try:
            deck_id = await _create_deck(client, owner_user)
            headers = auth_headers(owner_user)
            payload = {"moxfield_url": "https://moxfield.com/decks/abc123"}
            await client.post(
                f"{BASE}/personal-decks/{deck_id}/versions/import-moxfield",
                json=payload,
                headers=headers,
            )
            second = await client.post(
                f"{BASE}/personal-decks/{deck_id}/versions/import-moxfield",
                json=payload,
                headers=headers,
            )
        finally:
            app.dependency_overrides.pop(get_moxfield_client, None)

        assert second.json()["moxfield_deck_changed_since_last_import"] is False

    async def test_moxfield_import_persists_full_raw_response(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        raw = {
            "lastUpdatedAtUtc": "2026-07-29T11:54:52.473Z",
            "mainboard": {"Sol Ring": {"quantity": 1, "prices": {"usd": "1.23"}}},
        }

        class _FakeMoxfieldClient:
            async def fetch_decklist(self, deck_url: str) -> MoxfieldDeckFetch:
                return MoxfieldDeckFetch(content="1 Sol Ring", raw_data=raw)

        app.dependency_overrides[get_moxfield_client] = lambda: _FakeMoxfieldClient()
        try:
            deck_id = await _create_deck(client, owner_user)
            headers = auth_headers(owner_user)
            resp = await client.post(
                f"{BASE}/personal-decks/{deck_id}/versions/import-moxfield",
                json={"moxfield_url": "https://moxfield.com/decks/abc123"},
                headers=headers,
            )
        finally:
            app.dependency_overrides.pop(get_moxfield_client, None)

        version_id = uuid.UUID(resp.json()["id"])
        result = await db_session.execute(
            select(TSPersonalDecklistVersion).where(
                TSPersonalDecklistVersion.id == version_id
            )
        )
        version = result.scalar_one()
        assert version.moxfield_data == raw

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
