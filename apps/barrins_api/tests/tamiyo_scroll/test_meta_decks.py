"""Tests for /bff/tamiyo-scroll/meta-decks."""

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers, create_active_personal_deck

_PAYLOAD = {
    "name": "Burn",
    "tier": 1.5,
    "category": "aggro",
    "top8": 3,
    "presence": 12,
    "expected": "as_expected",
}


async def _create_meta_deck(
    client: AsyncClient, user: User, personal_deck_id: str, **overrides
) -> dict:
    payload = {**_PAYLOAD, "personal_deck_id": personal_deck_id, **overrides}
    resp = await client.post(
        f"{BASE}/meta-decks", json=payload, headers=auth_headers(user)
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
async def active_deck(client: AsyncClient, owner_user: User) -> dict:
    """Owner's active personal deck (magic) — required for GET /meta-decks
    to return anything at all under F10's scoping."""
    return await create_active_personal_deck(client, owner_user, "Burn Deck")


class TestListMetaDecks:
    async def test_empty_with_no_active_deck(
        self, client: AsyncClient, owner_user: User
    ):
        """No active_personal_deck_id selected -> [] (Constitution §15's
        "no deck selected -> no data" rule, extended to the roster)."""
        resp = await client.get(f"{BASE}/meta-decks", headers=auth_headers(owner_user))
        assert resp.json() == []

    async def test_empty_when_no_deck_of_that_game_exists(
        self, client: AsyncClient, owner_user: User, active_deck: dict
    ):
        resp = await client.get(f"{BASE}/meta-decks", headers=auth_headers(owner_user))
        assert resp.json() == []

    async def test_excludes_archived_by_default(
        self, client: AsyncClient, owner_user: User, active_deck: dict
    ):
        deck = await _create_meta_deck(client, owner_user, active_deck["id"])
        headers = auth_headers(owner_user)
        await client.delete(f"{BASE}/meta-decks/{deck['id']}", headers=headers)

        resp = await client.get(f"{BASE}/meta-decks", headers=headers)
        assert resp.json() == []

        resp = await client.get(
            f"{BASE}/meta-decks?include_archived=true", headers=headers
        )
        assert len(resp.json()) == 1

    async def test_game_scope_merges_same_name_rows_across_own_decks(
        self, client: AsyncClient, owner_user: User
    ):
        """Default scope ("game"): roster entries created against two of
        the owner's own (same-game) decks, sharing a name, collapse into
        one line — F10 item 4."""
        headers = auth_headers(owner_user)
        deck_a = await create_active_personal_deck(client, owner_user, "Deck A")
        await _create_meta_deck(
            client, owner_user, deck_a["id"], name="Boros Energy", tier=1.0
        )
        deck_b = await create_active_personal_deck(client, owner_user, "Deck B")
        await _create_meta_deck(
            client, owner_user, deck_b["id"], name="Boros Energy", tier=2.0
        )

        resp = await client.get(f"{BASE}/meta-decks", headers=headers)
        assert resp.status_code == 200
        matching = [d for d in resp.json() if d["name"] == "Boros Energy"]
        assert len(matching) == 1
        # The more recently created/updated row (Deck B's) wins the tie.
        assert matching[0]["tier"] == 2.0

    async def test_switching_active_deck_to_a_different_game_clears_roster(
        self, client: AsyncClient, owner_user: User
    ):
        """The bug this item fixes: switching the active deck to a
        different card game must not leak the previous game's roster."""
        headers = auth_headers(owner_user)
        magic_deck = await create_active_personal_deck(
            client, owner_user, "Magic Deck", game="magic"
        )
        await _create_meta_deck(client, owner_user, magic_deck["id"], name="Burn")

        resp = await client.get(f"{BASE}/meta-decks", headers=headers)
        assert [d["name"] for d in resp.json()] == ["Burn"]

        await create_active_personal_deck(
            client, owner_user, "Pokemon Deck", game="pokemon"
        )
        resp = await client.get(f"{BASE}/meta-decks", headers=headers)
        assert resp.json() == []

    async def test_personal_deck_scope_isolates_same_game_decks(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_a = await create_active_personal_deck(client, owner_user, "Deck A")
        await _create_meta_deck(
            client, owner_user, deck_a["id"], name="Boros Energy", tier=1.0
        )
        deck_b = await create_active_personal_deck(client, owner_user, "Deck B")
        await _create_meta_deck(
            client, owner_user, deck_b["id"], name="Boros Energy", tier=2.0
        )
        await client.patch(
            f"{BASE}/me/settings",
            json={"metagame_roster_scope": "personal_deck"},
            headers=headers,
        )

        # Deck B is active — only its own row shows, unmerged.
        resp = await client.get(f"{BASE}/meta-decks", headers=headers)
        matching = [d for d in resp.json() if d["name"] == "Boros Energy"]
        assert len(matching) == 1
        assert matching[0]["tier"] == 2.0

        await client.patch(
            f"{BASE}/me/settings",
            json={"active_personal_deck_id": deck_a["id"]},
            headers=headers,
        )
        resp = await client.get(f"{BASE}/meta-decks", headers=headers)
        matching = [d for d in resp.json() if d["name"] == "Boros Energy"]
        assert len(matching) == 1
        assert matching[0]["tier"] == 1.0


class TestCreateMetaDeck:
    async def test_creates_deck_with_conversion(
        self, client: AsyncClient, owner_user: User, active_deck: dict
    ):
        deck = await _create_meta_deck(
            client, owner_user, active_deck["id"], top8=3, presence=12
        )
        assert deck["conversion"] == 25.0
        assert deck["personal_deck_id"] == active_deck["id"]
        assert deck["game"] == "magic"

    async def test_zero_presence_conversion_is_none(
        self, client: AsyncClient, owner_user: User, active_deck: dict
    ):
        deck = await _create_meta_deck(
            client, owner_user, active_deck["id"], top8=0, presence=0
        )
        assert deck["conversion"] is None

    async def test_invalid_tier_step_returns_422(
        self, client: AsyncClient, owner_user: User, active_deck: dict
    ):
        resp = await client.post(
            f"{BASE}/meta-decks",
            json={**_PAYLOAD, "tier": 1.3, "personal_deck_id": active_deck["id"]},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422

    async def test_invalid_category_returns_422(
        self, client: AsyncClient, owner_user: User, active_deck: dict
    ):
        resp = await client.post(
            f"{BASE}/meta-decks",
            json={
                **_PAYLOAD,
                "category": "not-a-category",
                "personal_deck_id": active_deck["id"],
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422

    async def test_missing_personal_deck_id_returns_422(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.post(
            f"{BASE}/meta-decks", json=_PAYLOAD, headers=auth_headers(owner_user)
        )
        assert resp.status_code == 422

    async def test_foreign_personal_deck_id_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        other_deck = await create_active_personal_deck(client, other_user, "Not Yours")
        resp = await client.post(
            f"{BASE}/meta-decks",
            json={**_PAYLOAD, "personal_deck_id": other_deck["id"]},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404


class TestUpdateMetaDeck:
    async def test_updates_fields(
        self, client: AsyncClient, owner_user: User, active_deck: dict
    ):
        deck = await _create_meta_deck(client, owner_user, active_deck["id"])
        headers = auth_headers(owner_user)
        resp = await client.put(
            f"{BASE}/meta-decks/{deck['id']}",
            json={
                **_PAYLOAD,
                "personal_deck_id": active_deck["id"],
                "name": "Burn Renamed",
                "tier": 2.0,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Burn Renamed"
        assert resp.json()["tier"] == 2.0

    async def test_foreign_deck_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User, active_deck: dict
    ):
        deck = await _create_meta_deck(client, owner_user, active_deck["id"])
        resp = await client.put(
            f"{BASE}/meta-decks/{deck['id']}",
            json={**_PAYLOAD, "personal_deck_id": active_deck["id"]},
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404

    async def test_edit_propagates_to_same_name_same_game_rows(
        self, client: AsyncClient, owner_user: User
    ):
        """F10 item 5: editing one roster row atomically updates every
        other same-name/same-`game` row the owner has, even though only
        one of them is currently visible in the (collapsed) list."""
        headers = auth_headers(owner_user)
        deck_a = await create_active_personal_deck(client, owner_user, "Deck A")
        row_a = await _create_meta_deck(
            client, owner_user, deck_a["id"], name="Boros Energy", tier=1.0
        )
        deck_b = await create_active_personal_deck(client, owner_user, "Deck B")
        row_b = await _create_meta_deck(
            client, owner_user, deck_b["id"], name="Boros Energy", tier=1.0
        )

        await client.put(
            f"{BASE}/meta-decks/{row_a['id']}",
            json={
                **_PAYLOAD,
                "personal_deck_id": deck_a["id"],
                "name": "Boros Energy",
                "tier": 2.5,
            },
            headers=headers,
        )

        # Switch active deck to B, "personal_deck" scope, to see B's row
        # directly (bypassing the "game" scope's own collapse/tie-break).
        await client.patch(
            f"{BASE}/me/settings",
            json={
                "active_personal_deck_id": deck_b["id"],
                "metagame_roster_scope": "personal_deck",
            },
            headers=headers,
        )
        resp = await client.get(f"{BASE}/meta-decks", headers=headers)
        [row] = [d for d in resp.json() if d["id"] == row_b["id"]]
        assert row["tier"] == 2.5

    async def test_edit_does_not_propagate_across_games(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        magic_deck = await create_active_personal_deck(
            client, owner_user, "Magic Deck", game="magic"
        )
        magic_row = await _create_meta_deck(
            client, owner_user, magic_deck["id"], name="Aggro", tier=1.0
        )
        pokemon_deck = await create_active_personal_deck(
            client, owner_user, "Pokemon Deck", game="pokemon"
        )
        pokemon_row = await _create_meta_deck(
            client, owner_user, pokemon_deck["id"], name="Aggro", tier=1.0
        )

        await client.put(
            f"{BASE}/meta-decks/{magic_row['id']}",
            json={
                **_PAYLOAD,
                "personal_deck_id": magic_deck["id"],
                "name": "Aggro",
                "tier": 2.5,
            },
            headers=headers,
        )

        await client.patch(
            f"{BASE}/me/settings",
            json={
                "active_personal_deck_id": pokemon_deck["id"],
                "metagame_roster_scope": "personal_deck",
            },
            headers=headers,
        )
        resp = await client.get(f"{BASE}/meta-decks", headers=headers)
        [row] = [d for d in resp.json() if d["id"] == pokemon_row["id"]]
        assert row["tier"] == 1.0


class TestArchiveMetaDeck:
    async def test_archives_own_deck(
        self, client: AsyncClient, owner_user: User, active_deck: dict
    ):
        deck = await _create_meta_deck(client, owner_user, active_deck["id"])
        resp = await client.delete(
            f"{BASE}/meta-decks/{deck['id']}", headers=auth_headers(owner_user)
        )
        assert resp.status_code == 204

    async def test_foreign_deck_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User, active_deck: dict
    ):
        deck = await _create_meta_deck(client, owner_user, active_deck["id"])
        resp = await client.delete(
            f"{BASE}/meta-decks/{deck['id']}", headers=auth_headers(other_user)
        )
        assert resp.status_code == 404


async def _share_a_match(
    client: AsyncClient,
    sharer: User,
    receiver: User,
    *,
    opponent_name: str,
    opponent_tier: float = 2.5,
) -> None:
    """`sharer` logs a match for "King T'Challa" against `opponent_name`, then
    shares; `receiver` (same-named personal deck) enables receiving."""
    sharer_headers = auth_headers(sharer)
    personal_deck = await create_active_personal_deck(client, sharer, "King T'Challa")
    meta_deck = await _create_meta_deck(
        client,
        sharer,
        personal_deck["id"],
        name=opponent_name,
        tier=opponent_tier,
        category="control",
    )
    await client.post(
        f"{BASE}/matches",
        json={
            "personal_deck_id": personal_deck["id"],
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
        owner_deck = await create_active_personal_deck(
            client, owner_user, "King T'Challa"
        )
        own_deck = await _create_meta_deck(
            client,
            owner_user,
            owner_deck["id"],
            name="Boros Energy",
            tier=1.0,
            category="aggro",
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
        # Bug (2026-07-30): an own deck that also received a merged match
        # had no signal distinguishing it from a purely-own deck.
        assert matching[0]["has_shared_data"] is True

    async def test_own_deck_without_merged_matches_has_shared_data_false(
        self, client: AsyncClient, owner_user: User, active_deck: dict
    ):
        owner_headers = auth_headers(owner_user)
        await _create_meta_deck(
            client,
            owner_user,
            active_deck["id"],
            name="Boros Energy",
            tier=1.0,
            category="aggro",
        )

        resp = await client.get(f"{BASE}/meta-decks", headers=owner_headers)
        matching = [d for d in resp.json() if d["name"] == "Boros Energy"]
        assert matching[0]["has_shared_data"] is False

    async def test_two_sharers_same_named_deck_consolidate_into_one_line(
        self, client: AsyncClient, owner_user: User, other_user: User, third_user: User
    ):
        """Bug (2026-07-30): two different sharers each having their own
        roster entry for "the same" deck (no owner equivalent) must not
        produce two read-only lines — one consolidated line, highest tier
        wins, labeled "multi share" instead of a single "from: {sharer}"."""
        owner_headers = auth_headers(owner_user)
        await create_active_personal_deck(client, owner_user, "King T'Challa")
        await _share_a_match(
            client,
            sharer=other_user,
            receiver=owner_user,
            opponent_name="Aragorn, King of Gondor",
            opponent_tier=1.0,
        )
        await _share_a_match(
            client,
            sharer=third_user,
            receiver=owner_user,
            opponent_name="Aragorn, King of Gondor",
            opponent_tier=3.0,
        )

        resp = await client.get(f"{BASE}/meta-decks", headers=owner_headers)
        assert resp.status_code == 200
        matching = [d for d in resp.json() if d["name"] == "Aragorn, King of Gondor"]
        assert len(matching) == 1
        assert matching[0]["tier"] == 3.0
        assert matching[0]["is_readonly"] is True
        assert matching[0]["is_multi_share"] is True
        assert matching[0]["shared_by"] is None

        matches_resp = await client.get(f"{BASE}/matches", headers=owner_headers)
        opponent_ids = {m["opponent_deck_id"] for m in matches_resp.json()}
        # Both sharers' matches resolve to the same consolidated opponent.
        assert opponent_ids == {matching[0]["id"]}

    async def test_archiving_own_matched_deck_falls_back_to_a_read_only_line(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        """Regression (2026-07-30): archiving the owner's own name-matched
        roster entry must not silently drop the foreign match's opponent —
        it should fall back to a fresh read-only line instead."""
        owner_headers = auth_headers(owner_user)
        owner_deck = await create_active_personal_deck(
            client, owner_user, "King T'Challa"
        )
        own_deck = await _create_meta_deck(
            client,
            owner_user,
            owner_deck["id"],
            name="Boros Energy",
            tier=1.0,
            category="aggro",
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
        await create_active_personal_deck(client, owner_user, "King T'Challa")
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
        await create_active_personal_deck(client, owner_user, "Not King T'Challa")
        await _share_a_match(
            client, sharer=other_user, receiver=owner_user, opponent_name="Boros Energy"
        )

        resp = await client.get(f"{BASE}/meta-decks", headers=owner_headers)
        assert resp.json() == []
