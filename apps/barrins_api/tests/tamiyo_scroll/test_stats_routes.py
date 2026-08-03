"""HTTP tests for /bff/tamiyo-scroll/archetype-summary and /matchup-summary."""

from httpx import AsyncClient

from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


async def _setup_match(
    client: AsyncClient, user: User, *, category: str = "aggro"
) -> tuple[str, str]:
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

    async def test_filters_by_personal_deck_id(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id, _ = await _setup_match(client, owner_user, category="control")
        other_personal_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Other Deck", "game": "magic", "category": "control"},
            headers=headers,
        )
        other_personal_id = other_personal_resp.json()["id"]

        resp = await client.get(
            f"{BASE}/archetype-summary?personal_deck_id={other_personal_id}",
            headers=headers,
        )
        control = next(s for s in resp.json() if s["category"] == "control")
        assert control["decks"][0]["winrate"] is None

        resp = await client.get(
            f"{BASE}/archetype-summary?personal_deck_id={personal_id}",
            headers=headers,
        )
        control = next(s for s in resp.json() if s["category"] == "control")
        assert control["decks"][0]["winrate"] == 50.0


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
            json={"name": "Other Deck", "game": "magic", "category": "midrange"},
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


class TestSharedDataInStats:
    """No "view as" selector (overhauled 2026-07-30): a sharer's matches for a
    same-named deck are folded into the viewer's own stats, not shown
    separately."""

    async def test_matchup_summary_combines_own_and_shared_matches(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        other_headers = auth_headers(other_user)
        await _setup_match(client, other_user)
        await client.patch(
            f"{BASE}/me/settings", json={"data_shared": True}, headers=other_headers
        )

        owner_headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Mono Red", "game": "magic", "category": "aggro"},
            headers=owner_headers,
        )
        await client.patch(
            f"{BASE}/me/settings",
            json={"receive_shared_data": True},
            headers=owner_headers,
        )

        resp = await client.get(f"{BASE}/matchup-summary", headers=owner_headers)
        body = resp.json()
        assert len(body["rows"]) == 1
        assert body["rows"][0]["opponent_deck_name"] == "Burn"
        assert body["rows"][0]["match_count"] == 1
        assert body["rows"][0]["is_readonly"] is True

    async def test_archetype_summary_includes_shared_matches(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        other_headers = auth_headers(other_user)
        await _setup_match(client, other_user, category="control")
        await client.patch(
            f"{BASE}/me/settings", json={"data_shared": True}, headers=other_headers
        )

        owner_headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Mono Red", "game": "magic", "category": "aggro"},
            headers=owner_headers,
        )
        await client.patch(
            f"{BASE}/me/settings",
            json={"receive_shared_data": True},
            headers=owner_headers,
        )

        resp = await client.get(f"{BASE}/archetype-summary", headers=owner_headers)
        control = next(s for s in resp.json() if s["category"] == "control")
        assert control["average_winrate"] == 50.0
        assert control["decks"][0]["is_readonly"] is True

    async def test_mixed_own_deck_has_shared_data_true_in_both_summaries(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        """A deck the owner ranks themselves that also received a merged
        shared match is "mixed" — flagged via has_shared_data, distinct
        from a fully-foreign (is_readonly) roster line."""
        other_headers = auth_headers(other_user)
        await _setup_match(client, other_user, category="control")
        await client.patch(
            f"{BASE}/me/settings", json={"data_shared": True}, headers=other_headers
        )

        owner_headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Mono Red", "game": "magic", "category": "aggro"},
            headers=owner_headers,
        )
        await client.post(
            f"{BASE}/meta-decks",
            json={
                "name": "Burn",
                "tier": 2.0,
                "category": "control",
                "top8": 0,
                "presence": 0,
                "expected": "as_expected",
            },
            headers=owner_headers,
        )
        await client.patch(
            f"{BASE}/me/settings",
            json={"receive_shared_data": True},
            headers=owner_headers,
        )

        matchup_resp = await client.get(
            f"{BASE}/matchup-summary", headers=owner_headers
        )
        row = matchup_resp.json()["rows"][0]
        assert row["is_readonly"] is False
        assert row["has_shared_data"] is True

        archetype_resp = await client.get(
            f"{BASE}/archetype-summary", headers=owner_headers
        )
        control = next(s for s in archetype_resp.json() if s["category"] == "control")
        assert control["decks"][0]["is_readonly"] is False
        assert control["decks"][0]["has_shared_data"] is True
