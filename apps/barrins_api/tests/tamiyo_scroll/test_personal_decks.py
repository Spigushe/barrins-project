"""Tests for /bff/tamiyo-scroll/personal-decks and its sub-resources."""

import uuid
from datetime import date

from httpx import AsyncClient
from sqlalchemy import select, update

from app.main import app
from app.models.mtgjson import Card, MTGSet
from app.models.tamiyo_scroll import TSPersonalDeck, TSPersonalDecklistVersion
from app.models.user import User
from app.services.moxfield import get_moxfield_client
from app.services.moxfield.base import MoxfieldDeckFetch
from tests.tamiyo_scroll.conftest import BASE, auth_headers


async def _create_deck(client: AsyncClient, user: User, name: str = "Mono Red") -> str:
    resp = await client.post(
        f"{BASE}/personal-decks",
        json={"name": name, "game": "magic", "category": "aggro"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _flatten_library(body: dict) -> list[dict]:
    """`library_cards`'s cards, in group order -- for tests that only care
    about resolved card data, not the grouping itself."""
    return [card for group in body["library_cards"] for card in group["cards"]]


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
            json={"name": "Boros Aggro", "game": "magic", "category": "aggro"},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Boros Aggro"
        assert body["game"] == "magic"
        assert body["category"] == "aggro"
        assert body["archived_at"] is None

    async def test_blank_name_returns_422(self, client: AsyncClient, owner_user: User):
        resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "", "game": "magic", "category": "aggro"},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422

    async def test_missing_game_returns_422(
        self, client: AsyncClient, owner_user: User
    ):
        """S10: `game` is required, no default — a payload without it is
        rejected server-side, not silently defaulted."""
        resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Boros Aggro", "category": "aggro"},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422

    async def test_missing_category_returns_422(
        self, client: AsyncClient, owner_user: User
    ):
        """S11: `category` is required, no default — same rule as `game`."""
        resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Boros Aggro", "game": "magic"},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422


class TestPatchPersonalDeck:
    async def test_renames_without_touching_game_or_category(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_id = await _create_deck(client, owner_user, "Mono Red")

        resp = await client.patch(
            f"{BASE}/personal-decks/{deck_id}",
            json={"name": "Mono Red V2"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Mono Red V2"
        assert body["game"] == "magic"
        assert body["category"] == "aggro"

    async def test_sets_game_without_touching_name_or_category(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_id = await _create_deck(client, owner_user, "Mono Red")

        resp = await client.patch(
            f"{BASE}/personal-decks/{deck_id}",
            json={"game": "pokemon"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Mono Red"
        assert body["game"] == "pokemon"
        assert body["category"] == "aggro"

    async def test_sets_category_without_touching_name_or_game(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_id = await _create_deck(client, owner_user, "Mono Red")

        resp = await client.patch(
            f"{BASE}/personal-decks/{deck_id}",
            json={"category": "control"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Mono Red"
        assert body["game"] == "magic"
        assert body["category"] == "control"

    async def test_empty_payload_changes_nothing(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_id = await _create_deck(client, owner_user, "Mono Red")

        resp = await client.patch(
            f"{BASE}/personal-decks/{deck_id}", json={}, headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Mono Red"
        assert body["game"] == "magic"
        assert body["category"] == "aggro"

    async def test_unblocks_a_historical_null_game_deck(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        """A pre-migration deck (`game`/`category` NULL) is unblocked by
        PATCH — the whole point of the route existing (S10/S11)."""
        headers = auth_headers(owner_user)
        deck_id = await _create_deck(client, owner_user, "Historical Deck")
        await db_session.execute(
            update(TSPersonalDeck)
            .where(TSPersonalDeck.id == uuid.UUID(deck_id))
            .values(game=None, category=None)
        )
        await db_session.commit()

        resp = await client.patch(
            f"{BASE}/personal-decks/{deck_id}",
            json={"game": "magic", "category": "aggro"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["game"] == "magic"
        assert body["category"] == "aggro"

    async def test_foreign_deck_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        deck_id = await _create_deck(client, owner_user)
        resp = await client.patch(
            f"{BASE}/personal-decks/{deck_id}",
            json={"name": "Hijacked"},
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404

    async def test_unknown_deck_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.patch(
            f"{BASE}/personal-decks/00000000-0000-0000-0000-000000000000",
            json={"name": "Doesn't matter"},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_extra_field_returns_422(self, client: AsyncClient, owner_user: User):
        deck_id = await _create_deck(client, owner_user)
        resp = await client.patch(
            f"{BASE}/personal-decks/{deck_id}",
            json={"owner_id": str(owner_user.id)},
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
    async def test_no_version_returns_empty_view(
        self, client: AsyncClient, owner_user: User
    ):
        deck_id = await _create_deck(client, owner_user)
        resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/decklist-view",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "commander_cards": [],
            "library_cards": [],
            "unparsed_lines": [],
        }

    async def test_colors_cards_from_card_tests(
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
        body = resp.json()
        assert body["commander_cards"] == []
        cards = {(c["qty"], c["name"]): c["status"] for c in _flatten_library(body)}
        assert cards == {
            (4, "Lightning Bolt"): "validated",
            (2, "Duress"): "rejected",
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
        cards = {
            (c["qty"], c["name"]): c["status"] for c in _flatten_library(resp.json())
        }
        assert cards == {(4, "Lightning Bolt"): "neutral"}

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
        # "new content" doesn't match the "<qty> <name>" card-line pattern,
        # so it falls back to unparsed_lines rather than disappearing.
        assert [line["line"] for line in resp.json()["unparsed_lines"]] == [
            "new content"
        ]

    async def test_recognizes_commander_header_from_import(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_id = await _create_deck(client, owner_user)
        await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": "Commander\n1 Atraxa, Praetors' Voice\n\n1 Sol Ring"},
            headers=headers,
        )
        resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/decklist-view", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert [(c["qty"], c["name"]) for c in body["commander_cards"]] == [
            (1, "Atraxa, Praetors' Voice")
        ]
        assert [(c["qty"], c["name"]) for c in _flatten_library(body)] == [
            (1, "Sol Ring")
        ]

    async def test_sorts_library_cards_by_type_then_mana_value_then_name(
        self, client: AsyncClient, owner_user: User, db_session
    ) -> None:
        """Duel Commander display order: type, then
        mana value, then name. Covers every category in the type order plus
        both tiebreaks: creatures with contradicting name/mv order (proves
        mv beats name), and two same-type same-mv instants (proves name is
        the final tiebreak)."""
        mtg_set = MTGSet(
            code="SRT",
            name="Sort Test Set",
            release_date=date(2026, 1, 1),
            type="expansion",
            base_set_size=10,
            total_set_size=10,
            keyrune_code="srt",
        )
        db_session.add(mtg_set)
        await db_session.flush()

        def _card(name: str, type_line: str, mana_value: float | None) -> Card:
            return Card(
                id=uuid.uuid4(),
                set_code="SRT",
                name=name,
                type_line=type_line,
                mana_cost=None,
                mana_value=mana_value,
                color_identity=[],
                rarity="common",
                number=name,
                scryfall_id=f"{name}-scryfall-id",
            )

        db_session.add_all(
            [
                _card("Land Test", "Land", None),
                _card("Enchant Test", "Enchantment", 3),
                _card("Sol Ring Test", "Artifact", 1),
                _card("Sorcery Test", "Sorcery", 2),
                _card("Bravo Instant", "Instant", 2),
                _card("Alpha Instant", "Instant", 2),
                _card("Alpha High", "Creature — Beast", 5),
                _card("Zeta Low", "Creature — Beast", 1),
                _card("Battle Test", "Battle — Siege", 3),
                _card("Nissa Test", "Legendary Planeswalker — Nissa", 5),
            ]
        )
        await db_session.commit()

        headers = auth_headers(owner_user)
        deck_id = await _create_deck(client, owner_user)
        content = "\n".join(
            [
                "1 Land Test",
                "1 Enchant Test",
                "1 Sol Ring Test",
                "1 Sorcery Test",
                "1 Bravo Instant",
                "1 Alpha Instant",
                "1 Alpha High",
                "1 Zeta Low",
                "1 Battle Test",
                "1 Nissa Test",
            ]
        )
        await client.post(
            f"{BASE}/personal-decks/{deck_id}/versions",
            json={"content": content},
            headers=headers,
        )

        resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/decklist-view", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert [(g["category"], g["count"]) for g in body["library_cards"]] == [
            ("planeswalker", 1),
            ("battle", 1),
            ("creature", 2),
            ("instant", 2),
            ("sorcery", 1),
            ("artifact", 1),
            ("enchantment", 1),
            ("land", 1),
        ]
        assert [c["name"] for c in _flatten_library(body)] == [
            "Nissa Test",  # planeswalker
            "Battle Test",  # battle
            "Zeta Low",  # creature, mv1
            "Alpha High",  # creature, mv5
            "Alpha Instant",  # instant, mv2, name tiebreak
            "Bravo Instant",  # instant, mv2, name tiebreak
            "Sorcery Test",  # sorcery
            "Sol Ring Test",  # artifact
            "Enchant Test",  # enchantment
            "Land Test",  # land
        ]
