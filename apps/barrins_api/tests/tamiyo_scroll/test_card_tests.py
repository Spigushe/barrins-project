"""Tests for /bff/tamiyo-scroll/card-tests and their evaluations (S17)."""

import uuid
from datetime import date

from httpx import AsyncClient
from sqlalchemy import select

from app.models.mtgjson import Card, MTGSet
from app.models.tamiyo_scroll import TSCardTest, TSCardTestEvaluation
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


async def _create_card_log(
    client: AsyncClient,
    user: User,
    personal_id: str,
    *,
    removed_card_name: str = "Duress",
    added_card_name: str = "Bolt",
    notes: str | None = None,
):
    return await client.post(
        f"{BASE}/card-tests",
        json={
            "personal_deck_id": personal_id,
            "removed_card_name": removed_card_name,
            "added_card_name": added_card_name,
            "notes": notes,
        },
        headers=auth_headers(user),
    )


class TestCreateCardTest:
    async def test_creates_card_log(self, client: AsyncClient, owner_user: User):
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        resp = await _create_card_log(
            client,
            owner_user,
            personal_id,
            removed_card_name="Duress",
            added_card_name="Lightning Bolt",
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["personal_deck_id"] == personal_id
        assert body["removed_card_name"] == "Duress"
        assert body["added_card_name"] == "Lightning Bolt"
        # S17: matchup/rating no longer live on the card log itself.
        assert "opponent_deck_id" not in body
        assert "rating" not in body

    async def test_resolves_scryfall_ids_for_hover_preview(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        """S17 item 3 follow-up: the "Tested cards" block hovers the
        removed/added names the same way a pending decklist line does --
        both must resolve against `mj_cards`, and an unresolvable name
        (e.g. a homebrew/typo'd added card) must not break the response,
        just leave that side's id `None`."""
        await _seed_card(db_session, "Duress")
        await db_session.commit()

        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        resp = await _create_card_log(
            client,
            owner_user,
            personal_id,
            removed_card_name="Duress",
            added_card_name="Not A Real Card XYZ",
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["removed_card_scryfall_id"] == "Duress-scryfall-id"
        assert body["added_card_scryfall_id"] is None

    async def test_unknown_personal_deck_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.post(
            f"{BASE}/card-tests",
            json={
                "personal_deck_id": "00000000-0000-0000-0000-000000000000",
                "removed_card_name": "Duress",
                "added_card_name": "Lightning Bolt",
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_foreign_personal_deck_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        other_personal_id = await _create_personal_deck(client, other_user)
        resp = await _create_card_log(client, owner_user, other_personal_id)
        assert resp.status_code == 404


class TestUpdateCardTest:
    async def test_updates_notes(self, client: AsyncClient, owner_user: User):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        create_resp = await _create_card_log(client, owner_user, personal_id)
        test_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/card-tests/{test_id}",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Bolt",
                "notes": "Swap looks promising",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Swap looks promising"

    async def test_foreign_card_test_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        create_resp = await _create_card_log(client, owner_user, personal_id)
        test_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/card-tests/{test_id}",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Duress",
                "added_card_name": "Bolt",
                "notes": None,
            },
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestDeleteCardTest:
    async def test_deletes_own_test(self, client: AsyncClient, owner_user: User):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        create_resp = await _create_card_log(client, owner_user, personal_id)
        test_id = create_resp.json()["id"]

        resp = await client.delete(f"{BASE}/card-tests/{test_id}", headers=headers)
        assert resp.status_code == 204

        list_resp = await client.get(f"{BASE}/card-tests", headers=headers)
        assert list_resp.json() == []

    async def test_archives_rather_than_hard_deletes(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        """Constitution §11.8: deletion defaults to archive, never a SQL
        DELETE -- the row and its data must still exist in the database
        after a "delete", just hidden from active reads."""
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        create_resp = await _create_card_log(client, owner_user, personal_id)
        test_id = create_resp.json()["id"]

        resp = await client.delete(f"{BASE}/card-tests/{test_id}", headers=headers)
        assert resp.status_code == 204

        result = await db_session.execute(
            select(TSCardTest).where(TSCardTest.id == uuid.UUID(test_id))
        )
        test = result.scalar_one()
        assert test.archived_at is not None
        assert test.removed_card_name == "Duress"

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
        await _create_card_log(client, owner_user, personal_id)
        resp = await client.get(f"{BASE}/card-tests", headers=headers)
        assert len(resp.json()) == 1

    async def test_filters_by_personal_deck_id(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_a = await _create_personal_deck(client, owner_user, name="Deck A")
        deck_b = await _create_personal_deck(client, owner_user, name="Deck B")
        await _disable_removed_card_validation(client, owner_user)
        await _create_card_log(client, owner_user, deck_a, added_card_name="Bolt")
        await _create_card_log(
            client, owner_user, deck_b, added_card_name="Counterspell"
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

    async def test_resolves_scryfall_ids_across_multiple_logs(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        duress = await _seed_card(db_session, "Duress")
        db_session.add(
            Card(
                id=uuid.uuid4(),
                set_code=duress.set_code,
                name="Lightning Bolt",
                type_line="Instant",
                mana_cost=None,
                mana_value=1,
                color_identity=[],
                rarity="common",
                number="Lightning Bolt",
                scryfall_id="Lightning Bolt-scryfall-id",
            )
        )
        await db_session.commit()

        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        await _create_card_log(
            client,
            owner_user,
            personal_id,
            removed_card_name="Duress",
            added_card_name="Lightning Bolt",
        )

        resp = await client.get(f"{BASE}/card-tests", headers=headers)
        assert resp.status_code == 200
        [test] = resp.json()
        assert test["removed_card_scryfall_id"] == "Duress-scryfall-id"
        assert test["added_card_scryfall_id"] == "Lightning Bolt-scryfall-id"


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

        resp = await _create_card_log(
            client,
            owner_user,
            personal_id,
            removed_card_name="Counterspell",
            added_card_name="Bolt",
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

        resp = await _create_card_log(
            client,
            owner_user,
            personal_id,
            removed_card_name="Sol Ring",
            added_card_name="Bolt",
        )
        assert resp.status_code == 201

    async def test_off_accepts_anything_when_disabled(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)

        resp = await _create_card_log(
            client,
            owner_user,
            personal_id,
            removed_card_name="Not In Deck At All",
            added_card_name="Bolt",
        )
        assert resp.status_code == 201

    async def test_editing_an_existing_log_is_not_re_checked_against_the_decklist(
        self, client: AsyncClient, owner_user: User
    ):
        """The check is create-time only (2026-08-25 decision): once a log
        is saved, later decklist versions can legitimately move past its
        removed card, and that must not block editing the log (e.g. just
        its notes)."""
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Lightning Bolt\n1 Sol Ring"},
            headers=headers,
        )
        create_resp = await _create_card_log(
            client,
            owner_user,
            personal_id,
            removed_card_name="Sol Ring",
            added_card_name="Bolt",
        )
        assert create_resp.status_code == 201
        test_id = create_resp.json()["id"]

        # A newer version drops "Sol Ring" -- it's no longer in the
        # *current* decklist, so re-validating the existing log's
        # removed_card_name against it would now fail.
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Lightning Bolt"},
            headers=headers,
        )

        resp = await client.put(
            f"{BASE}/card-tests/{test_id}",
            json={
                "personal_deck_id": personal_id,
                "removed_card_name": "Sol Ring",
                "added_card_name": "Bolt",
                "notes": "Still tracking this swap",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Still tracking this swap"


class TestValidateAddedCardExists:
    async def test_off_by_default_accepts_anything(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        resp = await _create_card_log(
            client,
            owner_user,
            personal_id,
            added_card_name="Not A Real Card XYZ",
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

        resp = await _create_card_log(
            client,
            owner_user,
            personal_id,
            added_card_name="Not A Real Card XYZ",
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

        resp = await _create_card_log(
            client, owner_user, personal_id, added_card_name="Ambush Viper"
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

        matched = await _create_card_log(
            client,
            owner_user,
            personal_id,
            removed_card_name="Duress",
            added_card_name="Sol Ring",
        )
        unmatched = await _create_card_log(
            client,
            owner_user,
            personal_id,
            removed_card_name="Counterspell",
            added_card_name="Mana Crypt",
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

        partially_matched = await _create_card_log(
            client,
            owner_user,
            personal_id,
            removed_card_name="Duress",
            added_card_name="Something Never Actually Added",
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


class TestCreateCardTestEvaluation:
    async def test_creates_evaluation(self, client: AsyncClient, owner_user: User):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        meta_id = await _create_meta_deck(client, owner_user, personal_id)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]

        resp = await client.post(
            f"{BASE}/card-tests/{test_id}/evaluations",
            json={"opponent_deck_id": meta_id, "rating": 4, "notes": "Good matchup"},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["test_id"] == test_id
        assert body["opponent_deck_id"] == meta_id
        assert body["rating"] == 4
        assert body["notes"] == "Good matchup"

    async def test_missing_opponent_deck_returns_422(
        self, client: AsyncClient, owner_user: User
    ):
        """Unlike the pre-S17 flat field, `opponent_deck_id` is required
        on an evaluation — an evaluation is specifically a match-up."""
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]

        resp = await client.post(
            f"{BASE}/card-tests/{test_id}/evaluations",
            json={"rating": 4},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_unknown_opponent_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]

        resp = await client.post(
            f"{BASE}/card-tests/{test_id}/evaluations",
            json={
                "opponent_deck_id": "00000000-0000-0000-0000-000000000000",
                "rating": 4,
            },
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_unknown_card_test_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id = await _create_personal_deck(client, owner_user)
        meta_id = await _create_meta_deck(client, owner_user, personal_id)
        resp = await client.post(
            f"{BASE}/card-tests/00000000-0000-0000-0000-000000000000/evaluations",
            json={"opponent_deck_id": meta_id, "rating": 4},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_foreign_card_test_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        meta_id = await _create_meta_deck(client, owner_user, personal_id)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]

        resp = await client.post(
            f"{BASE}/card-tests/{test_id}/evaluations",
            json={"opponent_deck_id": meta_id, "rating": 4},
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404

    async def test_rating_out_of_range_returns_422(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        meta_id = await _create_meta_deck(client, owner_user, personal_id)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]

        resp = await client.post(
            f"{BASE}/card-tests/{test_id}/evaluations",
            json={"opponent_deck_id": meta_id, "rating": 6},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422

    async def test_two_evaluations_attach_to_same_log(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        meta_a = await _create_meta_deck(client, owner_user, personal_id)
        meta_b = await _create_meta_deck(client, owner_user, personal_id)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]

        await client.post(
            f"{BASE}/card-tests/{test_id}/evaluations",
            json={"opponent_deck_id": meta_a, "rating": 4},
            headers=headers,
        )
        await client.post(
            f"{BASE}/card-tests/{test_id}/evaluations",
            json={"opponent_deck_id": meta_b, "rating": 2},
            headers=headers,
        )
        list_resp = await client.get(f"{BASE}/card-tests", headers=headers)
        assert len(list_resp.json()) == 1


class TestUpdateCardTestEvaluation:
    async def test_updates_rating_and_notes(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        meta_id = await _create_meta_deck(client, owner_user, personal_id)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]
        create_resp = await client.post(
            f"{BASE}/card-tests/{test_id}/evaluations",
            json={"opponent_deck_id": meta_id, "rating": 4},
            headers=headers,
        )
        evaluation_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/card-tests/{test_id}/evaluations/{evaluation_id}",
            json={"opponent_deck_id": meta_id, "rating": 2, "notes": "Reconsidered"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["rating"] == 2
        assert body["notes"] == "Reconsidered"

    async def test_unknown_evaluation_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        meta_id = await _create_meta_deck(client, owner_user, personal_id)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]

        resp = await client.put(
            f"{BASE}/card-tests/{test_id}/evaluations/"
            "00000000-0000-0000-0000-000000000000",
            json={"opponent_deck_id": meta_id, "rating": 2},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_foreign_card_test_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        meta_id = await _create_meta_deck(client, owner_user, personal_id)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]
        create_resp = await client.post(
            f"{BASE}/card-tests/{test_id}/evaluations",
            json={"opponent_deck_id": meta_id, "rating": 4},
            headers=headers,
        )
        evaluation_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/card-tests/{test_id}/evaluations/{evaluation_id}",
            json={"opponent_deck_id": meta_id, "rating": 2},
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestDeleteCardTestEvaluation:
    async def test_deletes_own_evaluation(self, client: AsyncClient, owner_user: User):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        meta_id = await _create_meta_deck(client, owner_user, personal_id)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]
        create_resp = await client.post(
            f"{BASE}/card-tests/{test_id}/evaluations",
            json={"opponent_deck_id": meta_id, "rating": 4},
            headers=headers,
        )
        evaluation_id = create_resp.json()["id"]

        resp = await client.delete(
            f"{BASE}/card-tests/{test_id}/evaluations/{evaluation_id}",
            headers=headers,
        )
        assert resp.status_code == 204

    async def test_archives_rather_than_hard_deletes(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        meta_id = await _create_meta_deck(client, owner_user, personal_id)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]
        create_resp = await client.post(
            f"{BASE}/card-tests/{test_id}/evaluations",
            json={"opponent_deck_id": meta_id, "rating": 4},
            headers=headers,
        )
        evaluation_id = create_resp.json()["id"]

        resp = await client.delete(
            f"{BASE}/card-tests/{test_id}/evaluations/{evaluation_id}",
            headers=headers,
        )
        assert resp.status_code == 204

        result = await db_session.execute(
            select(TSCardTestEvaluation).where(
                TSCardTestEvaluation.id == uuid.UUID(evaluation_id)
            )
        )
        evaluation = result.scalar_one()
        assert evaluation.archived_at is not None
        assert evaluation.rating == 4

    async def test_unknown_evaluation_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id = await _create_personal_deck(client, owner_user)
        await _disable_removed_card_validation(client, owner_user)
        test_id = (await _create_card_log(client, owner_user, personal_id)).json()["id"]

        resp = await client.delete(
            f"{BASE}/card-tests/{test_id}/evaluations/"
            "00000000-0000-0000-0000-000000000000",
            headers=headers,
        )
        assert resp.status_code == 404
