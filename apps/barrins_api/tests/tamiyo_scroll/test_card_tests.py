"""Tests for /bff/tamiyo-scroll/card-tests."""

from httpx import AsyncClient

from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


async def _create_personal_deck(
    client: AsyncClient, user: User, *, name: str = "Mono Red"
) -> str:
    resp = await client.post(
        f"{BASE}/personal-decks", json={"name": name}, headers=auth_headers(user)
    )
    return resp.json()["id"]


async def _create_meta_deck(client: AsyncClient, user: User) -> str:
    resp = await client.post(
        f"{BASE}/meta-decks",
        json={
            "name": "Burn",
            "tier": 1.0,
            "category": "aggro",
            "top8": 1,
            "presence": 5,
            "expected": "as_expected",
        },
        headers=auth_headers(user),
    )
    return resp.json()["id"]


class TestCreateCardTest:
    async def test_creates_test_without_matchup(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id = await _create_personal_deck(client, owner_user)
        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "tester": "Alice",
                "card_name": "Lightning Bolt",
                "rating": 4,
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["opponent_deck_id"] is None
        assert body["personal_deck_id"] == personal_id

    async def test_creates_test_with_matchup(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id = await _create_personal_deck(client, owner_user)
        meta_id = await _create_meta_deck(client, owner_user)
        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "tester": "Alice",
                "card_name": "Lightning Bolt",
                "rating": 4,
                "opponent_deck_id": meta_id,
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 201
        assert resp.json()["opponent_deck_id"] == meta_id

    async def test_unknown_matchup_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id = await _create_personal_deck(client, owner_user)
        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "tester": "Alice",
                "card_name": "Lightning Bolt",
                "rating": 4,
                "opponent_deck_id": "00000000-0000-0000-0000-000000000000",
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_unknown_personal_deck_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": "00000000-0000-0000-0000-000000000000",
                "tester": "Alice",
                "card_name": "Lightning Bolt",
                "rating": 4,
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_foreign_personal_deck_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        other_personal_id = await _create_personal_deck(client, other_user)
        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": other_personal_id,
                "tester": "Alice",
                "card_name": "Lightning Bolt",
                "rating": 4,
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_rating_out_of_range_returns_422(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id = await _create_personal_deck(client, owner_user)
        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "tester": "Alice",
                "card_name": "Bolt",
                "rating": 6,
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422


class TestUpdateCardTest:
    async def test_updates_rating(self, client: AsyncClient, owner_user: User):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        create_resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "tester": "Alice",
                "card_name": "Bolt",
                "rating": 4,
            },
            headers=headers,
        )
        test_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/card-tests/{test_id}",
            json={
                "personal_deck_id": personal_id,
                "tester": "Alice",
                "card_name": "Bolt",
                "rating": 2,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["rating"] == 2

    async def test_foreign_card_test_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        create_resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "tester": "Alice",
                "card_name": "Bolt",
                "rating": 4,
            },
            headers=headers,
        )
        test_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/card-tests/{test_id}",
            json={
                "personal_deck_id": personal_id,
                "tester": "Alice",
                "card_name": "Bolt",
                "rating": 2,
            },
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestDeleteCardTest:
    async def test_deletes_own_test(self, client: AsyncClient, owner_user: User):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        create_resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "tester": "Alice",
                "card_name": "Bolt",
                "rating": 4,
            },
            headers=headers,
        )
        test_id = create_resp.json()["id"]

        resp = await client.delete(f"{BASE}/card-tests/{test_id}", headers=headers)
        assert resp.status_code == 204

        list_resp = await client.get(f"{BASE}/card-tests", headers=headers)
        assert list_resp.json() == []

    async def test_unknown_test_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.delete(
            f"{BASE}/card-tests/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404


class TestListCardTests:
    async def test_lists_own_tests(self, client: AsyncClient, owner_user: User):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "tester": "Alice",
                "card_name": "Bolt",
                "rating": 4,
            },
            headers=headers,
        )
        resp = await client.get(f"{BASE}/card-tests", headers=headers)
        assert len(resp.json()) == 1

    async def test_filters_by_personal_deck_id(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_a = await _create_personal_deck(client, owner_user, name="Deck A")
        deck_b = await _create_personal_deck(client, owner_user, name="Deck B")
        await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": deck_a,
                "tester": "Alice",
                "card_name": "Bolt",
                "rating": 4,
            },
            headers=headers,
        )
        await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": deck_b,
                "tester": "Alice",
                "card_name": "Counterspell",
                "rating": 3,
            },
            headers=headers,
        )

        resp = await client.get(
            f"{BASE}/card-tests?personal_deck_id={deck_a}", headers=headers
        )
        names = [t["card_name"] for t in resp.json()]
        assert names == ["Bolt"]

        resp = await client.get(
            f"{BASE}/card-tests?personal_deck_id={deck_b}", headers=headers
        )
        names = [t["card_name"] for t in resp.json()]
        assert names == ["Counterspell"]
