"""Tests for /bff/tamiyo-scroll/matches."""

from httpx import AsyncClient

from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


async def _setup_decks(client: AsyncClient, user: User) -> tuple[str, str]:
    headers = auth_headers(user)
    personal_resp = await client.post(
        f"{BASE}/personal-decks", json={"name": "Mono Red"}, headers=headers
    )
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
        headers=headers,
    )
    return personal_resp.json()["id"], meta_resp.json()["id"]


def _match_payload(personal_deck_id: str, opponent_deck_id: str, **overrides) -> dict:
    payload = {
        "personal_deck_id": personal_deck_id,
        "opponent_deck_id": opponent_deck_id,
        "on_play": True,
        "game1": "win",
        "game2": "loss",
        "game3": "win",
    }
    payload.update(overrides)
    return payload


class TestCreateMatch:
    async def test_creates_match(self, client: AsyncClient, owner_user: User):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["personal_deck_id"] == personal_id
        assert body["opponent_deck_id"] == meta_id
        assert body["date"] is not None

    async def test_unknown_personal_deck_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        _, meta_id = await _setup_decks(client, owner_user)
        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload("00000000-0000-0000-0000-000000000000", meta_id),
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_unknown_opponent_deck_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, "00000000-0000-0000-0000-000000000000"),
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_foreign_deck_ids_return_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, other_user)
        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404


class TestListMatches:
    async def test_lists_own_matches(self, client: AsyncClient, owner_user: User):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        resp = await client.get(f"{BASE}/matches", headers=headers)
        assert len(resp.json()) == 1


class TestUpdateMatch:
    async def test_updates_match(self, client: AsyncClient, owner_user: User):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        match_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/matches/{match_id}",
            json=_match_payload(personal_id, meta_id, on_play=False, game3=None),
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["on_play"] is False
        assert resp.json()["game3"] is None

    async def test_foreign_match_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        match_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/matches/{match_id}",
            json=_match_payload(personal_id, meta_id),
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestDeleteMatch:
    async def test_deletes_own_match(self, client: AsyncClient, owner_user: User):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        match_id = create_resp.json()["id"]

        resp = await client.delete(f"{BASE}/matches/{match_id}", headers=headers)
        assert resp.status_code == 204

        list_resp = await client.get(f"{BASE}/matches", headers=headers)
        assert list_resp.json() == []

    async def test_unknown_match_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.delete(
            f"{BASE}/matches/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404
