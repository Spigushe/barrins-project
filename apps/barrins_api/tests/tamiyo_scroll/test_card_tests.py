"""Tests for /bff/tamiyo-scroll/card-tests."""

import uuid
from datetime import date

from httpx import AsyncClient

from app.models.mtgjson import Card, MTGSet
from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


async def _create_personal_deck(
    client: AsyncClient, user: User, *, name: str = "Mono Red"
) -> str:
    resp = await client.post(
        f"{BASE}/personal-decks",
        json={"name": name, "game": "magic", "category": "midrange"},
        headers=auth_headers(user),
    )
    return resp.json()["id"]


async def _create_meta_deck(
    client: AsyncClient, user: User, personal_deck_id: str
) -> str:
    resp = await client.post(
        f"{BASE}/meta-decks",
        json={
            "name": "Burn",
            "tier": 1.0,
            "category": "aggro",
            "top8": 1,
            "presence": 5,
            "expected": "as_expected",
            "personal_deck_id": personal_deck_id,
        },
        headers=auth_headers(user),
    )
    return resp.json()["id"]


async def _disable_removed_card_validation(client: AsyncClient, user: User) -> None:
    """`validate_removed_card_in_decklist` defaults on (S16) -- tests not
    exercising that specific feature disable it so a card-test payload
    doesn't need a matching decklist version just to satisfy setup."""
    await client.patch(
        f"{BASE}/me/settings",
        json={"validate_removed_card_in_decklist": False},
        headers=auth_headers(user),
    )


async def _seed_card(db_session, name: str) -> Card:
    mtg_set = MTGSet(
        code="S16",
        name="Card Test Matching Set",
        release_date=date(2026, 1, 1),
        type="expansion",
        base_set_size=1,
        total_set_size=1,
        keyrune_code="s16",
    )
    db_session.add(mtg_set)
    await db_session.flush()
    card = Card(
        id=uuid.uuid4(),
        set_code="S16",
        name=name,
        type_line="Instant",
        mana_cost=None,
        mana_value=1,
        color_identity=[],
        rarity="common",
        number=name,
        scryfall_id=f"{name}-scryfall-id",
    )
    db_session.add(card)
    return card


class TestCreateCardTest:
    async def test_creates_test_without_matchup(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Lightning Bolt",
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
        await _disable_removed_card_validation(client, owner_user)
        meta_id = await _create_meta_deck(client, owner_user, personal_id)
        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Lightning Bolt",
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
                "removed_card_name": "Duress",
                "added_card_name": "Lightning Bolt",
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
                "removed_card_name": "Duress",
                "added_card_name": "Lightning Bolt",
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
                "removed_card_name": "Duress",
                "added_card_name": "Lightning Bolt",
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
                "removed_card_name": "Duress",
                "added_card_name": "Bolt",
                "rating": 6,
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422


class TestUpdateCardTest:
    async def test_updates_rating(self, client: AsyncClient, owner_user: User):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        create_resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Bolt",
                "rating": 4,
            },
            headers=headers,
        )
        test_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/card-tests/{test_id}",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Bolt",
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
        await _disable_removed_card_validation(client, owner_user)
        create_resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Bolt",
                "rating": 4,
            },
            headers=headers,
        )
        test_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/card-tests/{test_id}",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Bolt",
                "rating": 2,
            },
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestDeleteCardTest:
    async def test_deletes_own_test(self, client: AsyncClient, owner_user: User):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        create_resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Bolt",
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
        await _disable_removed_card_validation(client, owner_user)
        await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Bolt",
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
        await _disable_removed_card_validation(client, owner_user)
        await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": deck_a,
                "removed_card_name": "Duress",
                "added_card_name": "Bolt",
                "rating": 4,
            },
            headers=headers,
        )
        await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": deck_b,
                "removed_card_name": "Duress",
                "added_card_name": "Counterspell",
                "rating": 3,
            },
            headers=headers,
        )

        resp = await client.get(
            f"{BASE}/card-tests?personal_deck_id={deck_a}", headers=headers
        )
        names = [t["added_card_name"] for t in resp.json()]
        assert names == ["Bolt"]

        resp = await client.get(
            f"{BASE}/card-tests?personal_deck_id={deck_b}", headers=headers
        )
        names = [t["added_card_name"] for t in resp.json()]
        assert names == ["Counterspell"]


class TestValidateRemovedCardInDecklist:
    async def test_on_by_default_rejects_card_not_in_current_decklist(
        self, client: AsyncClient, owner_user: User
    ):
        """Defaults on (2026-08-24 decision) -- no explicit PATCH needed."""
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Lightning Bolt\n1 Sol Ring"},
            headers=headers,
        )

        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Counterspell",
                "added_card_name": "Bolt",
                "rating": 4,
            },
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_on_by_default_accepts_card_present_in_current_decklist(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Lightning Bolt\n1 Sol Ring"},
            headers=headers,
        )

        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Sol Ring",
                "added_card_name": "Bolt",
                "rating": 4,
            },
            headers=headers,
        )
        assert resp.status_code == 201

    async def test_off_accepts_anything_when_disabled(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)

        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Not In Deck At All",
                "added_card_name": "Bolt",
                "rating": 4,
            },
            headers=headers,
        )
        assert resp.status_code == 201


class TestValidateAddedCardExists:
    async def test_off_by_default_accepts_anything(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Not A Real Card XYZ",
                "rating": 4,
            },
            headers=headers,
        )
        assert resp.status_code == 201

    async def test_on_rejects_unresolvable_name(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        headers = auth_headers(owner_user)
        await _seed_card(db_session, "Ambush Viper")
        await db_session.commit()
        personal_id = await _create_personal_deck(client, owner_user)
        await client.patch(
            f"{BASE}/me/settings",
            json={
                "validate_removed_card_in_decklist": False,
                "validate_added_card_exists": True,
            },
            headers=headers,
        )

        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Not A Real Card XYZ",
                "rating": 4,
            },
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_on_accepts_resolvable_name(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        headers = auth_headers(owner_user)
        await _seed_card(db_session, "Ambush Viper")
        await db_session.commit()
        personal_id = await _create_personal_deck(client, owner_user)
        await client.patch(
            f"{BASE}/me/settings",
            json={
                "validate_removed_card_in_decklist": False,
                "validate_added_card_exists": True,
            },
            headers=headers,
        )

        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Ambush Viper",
                "rating": 4,
            },
            headers=headers,
        )
        assert resp.status_code == 201


class TestCardTestChangeLog:
    async def test_returns_only_entries_that_match_no_diff(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Lightning Bolt\n2 Duress"},
            headers=headers,
        )
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Lightning Bolt\n1 Sol Ring"},
            headers=headers,
        )

        matched = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Sol Ring",
                "rating": 4,
            },
            headers=headers,
        )
        unmatched = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Counterspell",
                "added_card_name": "Mana Crypt",
                "rating": 4,
            },
            headers=headers,
        )

        resp = await client.get(
            f"{BASE}/card-tests/change-log?personal_deck_id={personal_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        ids = {t["id"] for t in resp.json()}
        assert ids == {unmatched.json()["id"]}
        assert matched.json()["id"] not in ids

    async def test_matches_on_either_half_alone(
        self, client: AsyncClient, owner_user: User
    ):
        """A card test only needs one half (removed or added) to line up
        with a real diff line to count as matched."""
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Lightning Bolt\n2 Duress"},
            headers=headers,
        )
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Lightning Bolt\n1 Sol Ring"},
            headers=headers,
        )

        partially_matched = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Something Never Actually Added",
                "rating": 4,
            },
            headers=headers,
        )

        resp = await client.get(
            f"{BASE}/card-tests/change-log?personal_deck_id={personal_id}",
            headers=headers,
        )
        ids = {t["id"] for t in resp.json()}
        assert partially_matched.json()["id"] not in ids

    async def test_unknown_personal_deck_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.get(
            f"{BASE}/card-tests/change-log"
            "?personal_deck_id=00000000-0000-0000-0000-000000000000",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404
