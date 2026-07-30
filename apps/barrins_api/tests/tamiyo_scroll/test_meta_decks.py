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


async def _share_a_match(
    client: AsyncClient, sharer: User, receiver: User, *, opponent_name: str
) -> None:
    """`sharer` logs a match for "King T'Challa" against `opponent_name`, then
    shares; `receiver` (same-named personal deck) enables receiving."""
    sharer_headers = auth_headers(sharer)
    personal_resp = await client.post(
        f"{BASE}/personal-decks", json={"name": "King T'Challa"}, headers=sharer_headers
    )
    personal_id = personal_resp.json()["id"]
    meta_deck = await _create_meta_deck(
        client, sharer, name=opponent_name, tier=2.5, category="control"
    )
    await client.post(
        f"{BASE}/matches",
        json={
            "personal_deck_id": personal_id,
            "opponent_deck_id": meta_deck["id"],
            "on_play": True,
            "game1": "win",
        },
        headers=sharer_headers,
    )
    await client.patch(
        f"{BASE}/me/settings", json={"data_shared": True}, headers=sharer_headers
    )
    await client.patch(
        f"{BASE}/me/settings",
        json={"receive_shared_data": True},
        headers=auth_headers(receiver),
    )


class TestSharedRosterMerge:
    """No "view as" selector (overhauled 2026-07-30): a sharer's roster entry
    merges into the viewer's own matching-name entry, or is added as a new
    read-only line when the viewer has none of that name."""

    async def test_own_ranking_wins_when_names_match(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        owner_headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "King T'Challa"},
            headers=owner_headers,
        )
        own_deck = await _create_meta_deck(
            client, owner_user, name="Boros Energy", tier=1.0, category="aggro"
        )
        await _share_a_match(
            client, sharer=other_user, receiver=owner_user, opponent_name="Boros Energy"
        )

        resp = await client.get(f"{BASE}/meta-decks", headers=owner_headers)
        assert resp.status_code == 200
        matching = [d for d in resp.json() if d["name"] == "Boros Energy"]
        assert len(matching) == 1
        assert matching[0]["id"] == own_deck["id"]
        assert matching[0]["tier"] == 1.0
        assert matching[0]["is_readonly"] is False

    async def test_archiving_own_matched_deck_falls_back_to_a_read_only_line(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        """Regression (2026-07-30): archiving the owner's own name-matched
        roster entry must not silently drop the foreign match's opponent —
        it should fall back to a fresh read-only line instead."""
        owner_headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "King T'Challa"},
            headers=owner_headers,
        )
        own_deck = await _create_meta_deck(
            client, owner_user, name="Boros Energy", tier=1.0, category="aggro"
        )
        await _share_a_match(
            client, sharer=other_user, receiver=owner_user, opponent_name="Boros Energy"
        )

        await client.delete(
            f"{BASE}/meta-decks/{own_deck['id']}", headers=owner_headers
        )

        resp = await client.get(f"{BASE}/meta-decks", headers=owner_headers)
        assert resp.status_code == 200
        matching = [d for d in resp.json() if d["name"] == "Boros Energy"]
        assert len(matching) == 1
        assert matching[0]["id"] != own_deck["id"]
        assert matching[0]["is_readonly"] is True

        matches_resp = await client.get(f"{BASE}/matches", headers=owner_headers)
        [match] = matches_resp.json()
        # The match's opponent must resolve to a roster entry that's
        # actually present in the (non-archived) roster listing — never a
        # dangling id that only ever resolves to "?" on the frontend.
        assert match["opponent_deck_id"] == matching[0]["id"]

    async def test_foreign_roster_entry_added_read_only_when_no_name_match(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        owner_headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "King T'Challa"},
            headers=owner_headers,
        )
        await _share_a_match(
            client, sharer=other_user, receiver=owner_user, opponent_name="Boros Energy"
        )

        resp = await client.get(f"{BASE}/meta-decks", headers=owner_headers)
        assert resp.status_code == 200
        matching = [d for d in resp.json() if d["name"] == "Boros Energy"]
        assert len(matching) == 1
        assert matching[0]["is_readonly"] is True
        # Never the sharer's email (GDPR/privacy) — a generic label when
        # they have no display_name set.
        assert matching[0]["shared_by"] == "a kind user"
        assert "other@tamiyo-scroll.example.com" not in resp.text
        assert matching[0]["tier"] == 2.5

    async def test_no_merge_without_a_matching_personal_deck_name(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        owner_headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Not King T'Challa"},
            headers=owner_headers,
        )
        await _share_a_match(
            client, sharer=other_user, receiver=owner_user, opponent_name="Boros Energy"
        )

        resp = await client.get(f"{BASE}/meta-decks", headers=owner_headers)
        assert resp.json() == []
