"""Tests for auto-archiving stale sessions on decklist import (S14 item 9)."""

from httpx import AsyncClient

from app.services.tamiyo_scroll.session_auto_archive import session_is_stale
from tests.identity_auth import FakeUser as User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


class TestSessionIsStale:
    def test_no_matches_yet_is_never_stale(self):
        assert session_is_stale(None, max_version=5, threshold=1) is False

    def test_stale_once_gap_reaches_threshold(self):
        assert session_is_stale(1, max_version=3, threshold=2) is True

    def test_not_stale_below_threshold(self):
        assert session_is_stale(1, max_version=2, threshold=2) is False


async def _setup_decks(client: AsyncClient, user: User) -> tuple[str, str]:
    headers = auth_headers(user)
    personal_resp = await client.post(
        f"{BASE}/personal-decks",
        json={"name": "Mono Red", "game": "magic", "category": "aggro"},
        headers=headers,
    )
    personal_id = personal_resp.json()["id"]
    meta_resp = await client.post(
        f"{BASE}/meta-decks",
        json={
            "name": "Burn",
            "tier": 1.0,
            "category": "aggro",
            "top8": 1,
            "presence": 5,
            "expected": "as_expected",
            "personal_deck_id": personal_id,
        },
        headers=headers,
    )
    return personal_id, meta_resp.json()["id"]


async def _enable_auto_archive(client: AsyncClient, user: User, gap: int = 2) -> None:
    resp = await client.patch(
        f"{BASE}/me/settings",
        json={
            "auto_archive_stale_sessions": True,
            "auto_archive_decklist_version_gap": gap,
        },
        headers=auth_headers(user),
    )
    assert resp.status_code == 200


class TestSweepOnDecklistImport:
    async def test_archives_once_gap_reaches_threshold(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        await _enable_auto_archive(client, owner_user, gap=2)

        # v1
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "1 Mountain"},
            headers=headers,
        )
        session_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = session_resp.json()["id"]
        # Match created while v1 is latest — auto-stamped decklist_version_id = v1.
        await client.post(
            f"{BASE}/matches",
            json={
                "personal_deck_id": personal_id,
                "opponent_deck_id": meta_id,
                "on_play": True,
                "game1": "win",
                "session_id": session_id,
            },
            headers=headers,
        )

        # v2 — gap is now 1, below the threshold of 2.
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "2 Mountain"},
            headers=headers,
        )
        resp = await client.get(f"{BASE}/sessions", headers=headers)
        assert [s["id"] for s in resp.json()] == [session_id]

        # v3 — gap is now 2, meets the threshold.
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "3 Mountain"},
            headers=headers,
        )
        resp = await client.get(f"{BASE}/sessions", headers=headers)
        assert resp.json() == []
        resp = await client.get(
            f"{BASE}/sessions?include_archived=true", headers=headers
        )
        assert resp.json()[0]["archived_at"] is not None

    async def test_no_op_when_not_opted_in(self, client: AsyncClient, owner_user: User):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)

        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "1 Mountain"},
            headers=headers,
        )
        session_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = session_resp.json()["id"]
        await client.post(
            f"{BASE}/matches",
            json={
                "personal_deck_id": personal_id,
                "opponent_deck_id": meta_id,
                "on_play": True,
                "game1": "win",
                "session_id": session_id,
            },
            headers=headers,
        )

        for content in ["2 Mountain", "3 Mountain", "4 Mountain"]:
            await client.post(
                f"{BASE}/personal-decks/{personal_id}/versions",
                json={"content": content},
                headers=headers,
            )

        resp = await client.get(f"{BASE}/sessions", headers=headers)
        assert [s["id"] for s in resp.json()] == [session_id]

    async def test_session_with_no_matches_is_never_archived(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        await _enable_auto_archive(client, owner_user, gap=1)

        session_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = session_resp.json()["id"]

        for content in ["1 Mountain", "2 Mountain", "3 Mountain"]:
            await client.post(
                f"{BASE}/personal-decks/{personal_id}/versions",
                json={"content": content},
                headers=headers,
            )

        resp = await client.get(f"{BASE}/sessions", headers=headers)
        assert [s["id"] for s in resp.json()] == [session_id]
