"""HTTP tests for /bff/tamiyo-scroll/archetype-summary and /matchup-summary."""

from httpx import AsyncClient

from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


async def _setup_match(
    client: AsyncClient, user: User, *, category: str = "aggro"
) -> tuple[str, str]:
    headers = auth_headers(user)
    personal_resp = await client.post(
        f"{BASE}/personal-decks", json={"name": "Mono Red"}, headers=headers
    )
    personal_id = personal_resp.json()["id"]
    meta_resp = await client.post(
        f"{BASE}/meta-decks",
        json={
            "name": "Burn",
            "tier": 1.0,
            "category": category,
            "top8": 1,
            "presence": 5,
            "expected": "as_expected",
        },
        headers=headers,
    )
    meta_id = meta_resp.json()["id"]
    await client.post(
        f"{BASE}/matches",
        json={
            "personal_deck_id": personal_id,
            "opponent_deck_id": meta_id,
            "on_play": True,
            "game1": "win",
            "game2": "loss",
        },
        headers=headers,
    )
    return personal_id, meta_id


class TestArchetypeSummary:
    async def test_returns_all_four_categories(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.get(
            f"{BASE}/archetype-summary", headers=auth_headers(owner_user)
        )
        assert resp.status_code == 200
        categories = {s["category"] for s in resp.json()}
        assert categories == {"aggro", "midrange", "control", "combo"}

    async def test_reflects_journaled_matches(
        self, client: AsyncClient, owner_user: User
    ):
        await _setup_match(client, owner_user, category="control")
        resp = await client.get(
            f"{BASE}/archetype-summary", headers=auth_headers(owner_user)
        )
        control = next(s for s in resp.json() if s["category"] == "control")
        assert control["average_winrate"] == 50.0
        assert len(control["decks"]) == 1

    async def test_excludes_archived_meta_decks(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        _, meta_id = await _setup_match(client, owner_user, category="combo")
        await client.delete(f"{BASE}/meta-decks/{meta_id}", headers=headers)

        resp = await client.get(f"{BASE}/archetype-summary", headers=headers)
        combo = next(s for s in resp.json() if s["category"] == "combo")
        assert combo["decks"] == []
        assert combo["average_winrate"] is None


class TestMatchupSummary:
    async def test_empty_by_default(self, client: AsyncClient, owner_user: User):
        resp = await client.get(
            f"{BASE}/matchup-summary", headers=auth_headers(owner_user)
        )
        assert resp.status_code == 200
        assert resp.json() == {"rows": [], "average_winrate": None}

    async def test_reflects_journaled_matches(
        self, client: AsyncClient, owner_user: User
    ):
        await _setup_match(client, owner_user)
        resp = await client.get(
            f"{BASE}/matchup-summary", headers=auth_headers(owner_user)
        )
        body = resp.json()
        assert len(body["rows"]) == 1
        assert body["rows"][0]["opponent_deck_name"] == "Burn"
        assert body["average_winrate"] == 50.0

    async def test_filters_by_personal_deck_id(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_match(client, owner_user)
        other_personal_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Other Deck"},
            headers=auth_headers(owner_user),
        )
        other_personal_id = other_personal_resp.json()["id"]

        resp = await client.get(
            f"{BASE}/matchup-summary?personal_deck_id={other_personal_id}",
            headers=auth_headers(owner_user),
        )
        assert resp.json() == {"rows": [], "average_winrate": None}

        resp = await client.get(
            f"{BASE}/matchup-summary?personal_deck_id={personal_id}",
            headers=auth_headers(owner_user),
        )
        assert len(resp.json()["rows"]) == 1
