"""Tests for /bff/tamiyo-scroll/matches."""

import uuid
from typing import ClassVar

from httpx import AsyncClient
from sqlalchemy import update

from app.models.tamiyo_scroll import TSMatchGame, TSPersonalDeck
from tests.identity_auth import FakeUser as User
from tests.tamiyo_scroll.conftest import BASE, auth_headers, create_active_personal_deck


async def _null_out(
    db_session, personal_id: str, *, game: bool, category: bool
) -> None:
    """Directly nulls `game`/`category` on a deck to simulate a historical,
    pre-migration deck (nullable, no backfill) — the only way to reach that
    state now that `PersonalDeckCreate` requires both fields."""
    values: dict[str, None] = {}
    if game:
        values["game"] = None
    if category:
        values["category"] = None
    stmt = update(TSPersonalDeck).where(TSPersonalDeck.id == uuid.UUID(personal_id))
    await db_session.execute(stmt.values(**values))
    await db_session.commit()


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


def _match_payload(
    personal_deck_id: str,
    opponent_deck_id: str,
    *,
    on_play: bool = True,
    game1: str | None = "win",
    game2: str | None = "loss",
    game3: str | None = "win",
    games: list[dict] | None = None,
    **overrides,
) -> dict:
    """Builds a `MatchWrite` payload.

    `on_play`/`game1`/`game2`/`game3` are convenience kwargs (matching the
    pre-#123/#124 flat shape most call sites already use) translated into
    the new nested `games[]` array — `game1`'s result also carries
    `on_play` (only game 1 has ever had a starting player). Pass `games`
    directly to bypass this convenience shape entirely (gated-field tests,
    multi-game mulligan/misplay payloads).
    """
    if games is None:
        games = []
        for number, result in ((1, game1), (2, game2), (3, game3)):
            if result is None:
                continue
            entry: dict = {"game_number": number, "result": result}
            if number == 1:
                entry["on_play"] = on_play
            games.append(entry)
    payload = {
        "personal_deck_id": personal_deck_id,
        "opponent_deck_id": opponent_deck_id,
        "games": games,
    }
    payload.update(overrides)
    return payload


async def _create_version(client: AsyncClient, headers: dict, personal_id: str) -> str:
    resp = await client.post(
        f"{BASE}/personal-decks/{personal_id}/versions",
        json={"content": "1x Lightning Bolt"},
        headers=headers,
    )
    return resp.json()["id"]


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

    async def test_no_decklist_version_stamps_null(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=auth_headers(owner_user),
        )
        assert resp.json()["decklist_version_id"] is None

    async def test_stamps_the_latest_decklist_version_at_creation(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        await _create_version(client, headers, personal_id)
        version_2 = await _create_version(client, headers, personal_id)

        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        assert resp.json()["decklist_version_id"] == version_2

    async def test_client_supplied_decklist_version_is_ignored_on_create(
        self, client: AsyncClient, owner_user: User
    ):
        """Never the frontend guessing which version is "current" (S3)."""
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        version_1 = await _create_version(client, headers, personal_id)
        await _create_version(client, headers, personal_id)

        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, decklist_version_id=version_1),
            headers=headers,
        )
        assert resp.json()["decklist_version_id"] != version_1

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


class TestCreateMatchGameCategoryGate:
    """S10/S11: a personal deck's `game` and `category` must both be set
    before a match can be logged on it — a historical (pre-migration or
    still-incomplete) deck is rejected with a stable 422 detail code."""

    async def test_null_game_returns_422(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        await _null_out(db_session, personal_id, game=True, category=False)

        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["message"] == "personal_deck_game_required"

    async def test_null_category_returns_422(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        await _null_out(db_session, personal_id, game=False, category=True)

        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["message"] == "personal_deck_macrotype_required"

    async def test_succeeds_once_both_are_set(
        self, client: AsyncClient, owner_user: User
    ):
        """Non-regression: a deck created through the normal flow (both
        fields required at creation) is never gated."""
        personal_id, meta_id = await _setup_decks(client, owner_user)
        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 201


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

    async def test_filters_by_personal_deck_id(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_a, meta_id = await _setup_decks(client, owner_user)
        deck_b_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Azorius Control", "game": "magic", "category": "control"},
            headers=headers,
        )
        deck_b = deck_b_resp.json()["id"]
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(deck_a, meta_id),
            headers=headers,
        )
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(deck_b, meta_id),
            headers=headers,
        )

        resp = await client.get(
            f"{BASE}/matches?personal_deck_id={deck_a}", headers=headers
        )
        deck_ids = [m["personal_deck_id"] for m in resp.json()]
        assert deck_ids == [deck_a]

        resp = await client.get(
            f"{BASE}/matches?personal_deck_id={deck_b}", headers=headers
        )
        deck_ids = [m["personal_deck_id"] for m in resp.json()]
        assert deck_ids == [deck_b]


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
        games = resp.json()["games"]
        assert next(g["on_play"] for g in games if g["game_number"] == 1) is False
        assert all(g["game_number"] != 3 for g in games)

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

    async def test_re_points_the_match_to_a_different_decklist_version(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        version_1 = await _create_version(client, headers, personal_id)
        await _create_version(client, headers, personal_id)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        match_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/matches/{match_id}",
            json=_match_payload(personal_id, meta_id, decklist_version_id=version_1),
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["decklist_version_id"] == version_1

    async def test_clears_the_decklist_version_with_explicit_null(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        await _create_version(client, headers, personal_id)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        match_id = create_resp.json()["id"]
        assert create_resp.json()["decklist_version_id"] is not None

        resp = await client.put(
            f"{BASE}/matches/{match_id}",
            json=_match_payload(personal_id, meta_id, decklist_version_id=None),
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["decklist_version_id"] is None

    async def test_unknown_decklist_version_returns_404(
        self, client: AsyncClient, owner_user: User
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
            json=_match_payload(
                personal_id,
                meta_id,
                decklist_version_id="00000000-0000-0000-0000-000000000000",
            ),
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_other_deck_decklist_version_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        """A version must belong to the match's own personal deck, not any deck."""
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        other_deck_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Azorius Control", "game": "magic", "category": "control"},
            headers=headers,
        )
        other_deck_id = other_deck_resp.json()["id"]
        foreign_version = await _create_version(client, headers, other_deck_id)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        match_id = create_resp.json()["id"]

        resp = await client.put(
            f"{BASE}/matches/{match_id}",
            json=_match_payload(
                personal_id, meta_id, decklist_version_id=foreign_version
            ),
            headers=headers,
        )
        assert resp.status_code == 404


class TestUpdateMatchGameCategoryGate:
    """S10/S11: the gate blocks re-saving an existing match, not just
    creating a new one — "block create and modify" (matches.py's
    `_validate_match_refs`, called from both `create_match` and
    `update_match`)."""

    async def test_null_game_returns_422(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        match_id = create_resp.json()["id"]
        await _null_out(db_session, personal_id, game=True, category=False)

        resp = await client.put(
            f"{BASE}/matches/{match_id}",
            json=_match_payload(personal_id, meta_id, on_play=False),
            headers=headers,
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["message"] == "personal_deck_game_required"

    async def test_null_category_returns_422(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        match_id = create_resp.json()["id"]
        await _null_out(db_session, personal_id, game=False, category=True)

        resp = await client.put(
            f"{BASE}/matches/{match_id}",
            json=_match_payload(personal_id, meta_id, on_play=False),
            headers=headers,
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["message"] == "personal_deck_macrotype_required"


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


async def _enable_sharing(client: AsyncClient, sharer: User, receiver: User) -> None:
    await client.patch(
        f"{BASE}/me/settings",
        json={"data_shared": True},
        headers=auth_headers(sharer),
    )
    await client.patch(
        f"{BASE}/me/settings",
        json={"receive_shared_data": True},
        headers=auth_headers(receiver),
    )


class TestSharedDataMerge:
    """No "view as" selector (overhauled 2026-07-30): a sharer's matches for a
    same-named personal deck are merged read-only into the viewer's own
    Journal, automatically, once both toggles are on."""

    async def test_merges_read_only_match_for_a_same_named_deck(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        other_headers = auth_headers(other_user)
        other_personal, other_meta = await _setup_decks(client, other_user)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(other_personal, other_meta),
            headers=other_headers,
        )

        owner_headers = auth_headers(owner_user)
        # Same name as other_user's deck ("Mono Red", from _setup_decks).
        owner_personal_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Mono Red", "game": "magic", "category": "aggro"},
            headers=owner_headers,
        )
        owner_personal = owner_personal_resp.json()["id"]

        await _enable_sharing(client, sharer=other_user, receiver=owner_user)

        resp = await client.get(
            f"{BASE}/matches?personal_deck_id={owner_personal}", headers=owner_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["is_readonly"] is True
        # Never the sharer's email (GDPR/privacy) — a generic label when
        # they have no display_name set.
        assert body[0]["shared_by"] == "a kind user"
        assert "other@tamiyo-scroll.example.com" not in resp.text
        # Remapped onto the viewer's own deck, not the sharer's raw id.
        assert body[0]["personal_deck_id"] == owner_personal
        # #123/#124: the sharer's per-game log carries through read-only.
        assert [g["game_number"] for g in body[0]["games"]] == [1, 2, 3]

    async def test_merged_match_carries_gated_counts_but_strips_comments(
        self, client: AsyncClient, owner_user: User
    ):
        """sharing_merge.py::_from_match_game carries the sharer's
        mulligan/misplay *counts* through (as the event list's length) but
        strips each event's `comment` — an Agent 1 privacy judgment call
        (2026-09-15): per-event commentary reads as a personal note-to-
        self, not something obviously meant for teammates."""
        sharer = User(role="moderator")
        sharer_headers = auth_headers(sharer)
        sharer_personal, sharer_meta = await _setup_decks(client, sharer)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(
                sharer_personal,
                sharer_meta,
                games=[
                    {
                        "game_number": 1,
                        "on_play": True,
                        "result": "win",
                        "player_mulligans": [
                            {"comment": "kept a risky 6"},
                            {"comment": None},
                        ],
                        "player_misplays": [{"comment": "attacked into open mana"}],
                    }
                ],
            ),
            headers=sharer_headers,
        )

        owner_headers = auth_headers(owner_user)
        owner_personal_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Mono Red", "game": "magic", "category": "aggro"},
            headers=owner_headers,
        )
        owner_personal = owner_personal_resp.json()["id"]
        await _enable_sharing(client, sharer=sharer, receiver=owner_user)

        resp = await client.get(
            f"{BASE}/matches?personal_deck_id={owner_personal}", headers=owner_headers
        )
        assert resp.status_code == 200
        games = resp.json()[0]["games"]
        # Count (list length) carries through...
        assert len(games[0]["player_mulligans"]) == 2
        assert len(games[0]["player_misplays"]) == 1
        # ...but every comment is stripped.
        assert all(e["comment"] is None for e in games[0]["player_mulligans"])
        assert all(e["comment"] is None for e in games[0]["player_misplays"])
        assert "kept a risky 6" not in resp.text
        assert "attacked into open mana" not in resp.text

    async def test_shared_by_uses_display_name_when_set(
        self,
        client: AsyncClient,
        owner_user: User,
        other_user: User,
        identity_directory,
    ):
        from app.services.identity_directory import UserRef

        # Post-ADR-20 the sharer's display name comes from identity, not a
        # barrins_api profile row — model it on the directory.
        identity_directory._extra[other_user.id] = UserRef(
            username="other", display_name="Bob"
        )
        other_headers = auth_headers(other_user)
        other_personal, other_meta = await _setup_decks(client, other_user)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(other_personal, other_meta),
            headers=other_headers,
        )

        owner_headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Mono Red", "game": "magic", "category": "aggro"},
            headers=owner_headers,
        )
        await _enable_sharing(client, sharer=other_user, receiver=owner_user)

        resp = await client.get(f"{BASE}/matches", headers=owner_headers)
        assert resp.json()[0]["shared_by"] == "Bob"

    async def test_no_merge_without_receive_toggle(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        other_headers = auth_headers(other_user)
        other_personal, other_meta = await _setup_decks(client, other_user)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(other_personal, other_meta),
            headers=other_headers,
        )
        await client.patch(
            f"{BASE}/me/settings", json={"data_shared": True}, headers=other_headers
        )

        owner_headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Mono Red", "game": "magic", "category": "aggro"},
            headers=owner_headers,
        )

        resp = await client.get(f"{BASE}/matches", headers=owner_headers)
        assert resp.json() == []

    async def test_no_merge_without_a_matching_deck_name(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        other_headers = auth_headers(other_user)
        other_personal, other_meta = await _setup_decks(client, other_user)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(other_personal, other_meta),
            headers=other_headers,
        )

        owner_headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks",
            json={
                "name": "Totally Different Deck",
                "game": "magic",
                "category": "midrange",
            },
            headers=owner_headers,
        )
        await _enable_sharing(client, sharer=other_user, receiver=owner_user)

        resp = await client.get(f"{BASE}/matches", headers=owner_headers)
        assert resp.json() == []

    async def test_deck_name_match_is_case_insensitive_and_trimmed(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        other_headers = auth_headers(other_user)
        other_personal, other_meta = await _setup_decks(client, other_user)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(other_personal, other_meta),
            headers=other_headers,
        )

        owner_headers = auth_headers(owner_user)
        owner_personal_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "  mono red  ", "game": "magic", "category": "aggro"},
            headers=owner_headers,
        )
        await _enable_sharing(client, sharer=other_user, receiver=owner_user)

        resp = await client.get(
            f"{BASE}/matches?personal_deck_id={owner_personal_resp.json()['id']}",
            headers=owner_headers,
        )
        assert len(resp.json()) == 1

    async def test_merged_match_is_not_editable(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        """Merged matches don't belong to the viewer — PUT/DELETE still 404."""
        other_headers = auth_headers(other_user)
        other_personal, other_meta = await _setup_decks(client, other_user)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(other_personal, other_meta),
            headers=other_headers,
        )
        shared_match_id = create_resp.json()["id"]

        owner_headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Mono Red", "game": "magic", "category": "aggro"},
            headers=owner_headers,
        )
        await _enable_sharing(client, sharer=other_user, receiver=owner_user)

        resp = await client.put(
            f"{BASE}/matches/{shared_match_id}",
            json=_match_payload(other_personal, other_meta),
            headers=owner_headers,
        )
        assert resp.status_code == 404

        resp = await client.delete(
            f"{BASE}/matches/{shared_match_id}", headers=owner_headers
        )
        assert resp.status_code == 404

    async def test_new_match_against_a_foreign_readonly_opponent_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        """Bug (2026-07-30): a roster entry that only exists via sharing
        (`is_readonly=True`, owned by the sharer) can't be used directly as
        a *new* match's opponent — it isn't the viewer's own row. The
        frontend must first create the viewer's own same-named roster
        entry (the "claim" flow in MatchForm's OpponentDeckField) and use
        that id instead. This test locks in the 404 the claim flow exists
        to route around."""
        other_personal, other_meta = await _setup_decks(client, other_user)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(other_personal, other_meta),
            headers=auth_headers(other_user),
        )

        owner_headers = auth_headers(owner_user)
        owner_personal_deck = await create_active_personal_deck(
            client, owner_user, "Mono Red"
        )
        owner_personal = owner_personal_deck["id"]
        await _enable_sharing(client, sharer=other_user, receiver=owner_user)

        # "Burn" now appears read-only in the owner's roster (see
        # test_meta_decks.py) — but its id is still the sharer's own row.
        meta_decks_resp = await client.get(f"{BASE}/meta-decks", headers=owner_headers)
        foreign_meta_id = next(
            d["id"] for d in meta_decks_resp.json() if d["name"] == "Burn"
        )
        assert foreign_meta_id == other_meta

        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(owner_personal, foreign_meta_id),
            headers=owner_headers,
        )
        assert resp.status_code == 404


class TestMatchGames:
    """#123/#124: the nested `games[]` array (mulligans, misplays — one
    event per individual occurrence, each with its own comment, D2's
    second amendment), round-tripped through POST/PUT."""

    async def test_creates_and_returns_nested_games(self, client: AsyncClient):
        moderator = User(role="moderator")
        personal_id, meta_id = await _setup_decks(client, moderator)
        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(
                personal_id,
                meta_id,
                games=[
                    {
                        "game_number": 1,
                        "on_play": True,
                        "result": "win",
                        "player_mulligans": [
                            {"comment": "Kept a 6"},
                        ],
                        "opponent_mulligans": [],
                        "player_misplays": [
                            {"comment": "Missed a land drop"},
                            {"comment": None},
                        ],
                        "opponent_misplays": [],
                    },
                    {"game_number": 2, "result": "loss"},
                ],
            ),
            headers=auth_headers(moderator),
        )
        assert resp.status_code == 201
        games = sorted(resp.json()["games"], key=lambda g: g["game_number"])
        assert [g["game_number"] for g in games] == [1, 2]
        assert games[0]["on_play"] is True
        assert games[0]["result"] == "win"
        assert [e["comment"] for e in games[0]["player_mulligans"]] == ["Kept a 6"]
        assert [e["comment"] for e in games[0]["player_misplays"]] == [
            "Missed a land drop",
            None,
        ]
        # Every event has a stable id (frontend React-key requirement, D2).
        assert all(e["id"] for e in games[0]["player_misplays"])
        assert games[0]["opponent_mulligans"] == []
        assert games[1]["result"] == "loss"
        assert games[1]["on_play"] is None
        assert games[1]["player_mulligans"] == []

    async def test_put_removes_a_game_no_longer_present(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        match_id = create_resp.json()["id"]
        assert len(create_resp.json()["games"]) == 3

        resp = await client.put(
            f"{BASE}/matches/{match_id}",
            json=_match_payload(personal_id, meta_id, game2=None, game3=None),
            headers=headers,
        )
        assert resp.status_code == 200
        assert [g["game_number"] for g in resp.json()["games"]] == [1]

    async def test_put_upserts_an_added_game(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, game2=None, game3=None),
            headers=headers,
        )
        match_id = create_resp.json()["id"]
        assert len(create_resp.json()["games"]) == 1

        resp = await client.put(
            f"{BASE}/matches/{match_id}",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["games"]) == 3


class TestMatchGamesRoleGate:
    """D7: mulligans/misplays require a `moderator`+ caller, enforced
    field-level inside `_apply_payload` — never a route-level dependency,
    so a sub-moderator can still submit ordinary game results."""

    _GATED_PAYLOADS: ClassVar[list[dict]] = [
        {"player_mulligans": [{"comment": None}]},
        {"opponent_mulligans": [{"comment": None}]},
        {"player_misplays": [{"comment": None}]},
        {"opponent_misplays": [{"comment": None}]},
    ]

    async def test_sub_moderator_create_with_gated_field_is_403(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        for extra in self._GATED_PAYLOADS:
            resp = await client.post(
                f"{BASE}/matches",
                json=_match_payload(
                    personal_id,
                    meta_id,
                    games=[{"game_number": 1, "result": "win", **extra}],
                ),
                headers=auth_headers(owner_user),
            )
            assert resp.status_code == 403, extra

    async def test_sub_moderator_create_without_gated_fields_succeeds(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 201

    async def test_sub_moderator_update_with_gated_field_is_403(
        self, client: AsyncClient, owner_user: User
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
            json=_match_payload(
                personal_id,
                meta_id,
                games=[
                    {
                        "game_number": 1,
                        "result": "win",
                        "player_mulligans": [{"comment": None}],
                    }
                ],
            ),
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_moderator_can_submit_gated_fields(self, client: AsyncClient):
        moderator = User(role="moderator")
        personal_id, meta_id = await _setup_decks(client, moderator)
        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(
                personal_id,
                meta_id,
                games=[
                    {
                        "game_number": 1,
                        "on_play": True,
                        "result": "win",
                        "player_mulligans": [
                            {"comment": "a"},
                            {"comment": "b"},
                            {"comment": None},
                        ],
                        "player_misplays": [{"comment": "note"}],
                    }
                ],
            ),
            headers=auth_headers(moderator),
        )
        assert resp.status_code == 201
        assert len(resp.json()["games"][0]["player_mulligans"]) == 3

    async def test_admin_can_submit_gated_fields(
        self, client: AsyncClient, admin_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, admin_user)
        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(
                personal_id,
                meta_id,
                games=[
                    {
                        "game_number": 1,
                        "result": "win",
                        "player_mulligans": [{"comment": None}],
                    }
                ],
            ),
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 201


class TestMatchGameEventCounterNullVsZero:
    """D2's second amendment (2026-09-15): `TSMatchGame`'s four counter
    columns are a backend-only derived cache — NULL ("not tracked", a
    sub-moderator save) must stay distinguishable from a real `0`
    ("tracked, confirmed empty", a moderator save) for `stats.py`'s
    averaging. Verified here at the model level since the API response
    deliberately never surfaces the counter itself (only the event list,
    whose length already gives it) — see `ResponseMatchGame`'s docstring.
    """

    async def test_moderator_genuinely_empty_list_yields_zero_not_null(
        self, client: AsyncClient, db_session
    ):
        moderator = User(role="moderator")
        personal_id, meta_id = await _setup_decks(client, moderator)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(
                personal_id,
                meta_id,
                games=[
                    {
                        "game_number": 1,
                        "result": "win",
                        "player_mulligans": [],
                        "player_misplays": [],
                    }
                ],
            ),
            headers=auth_headers(moderator),
        )
        assert create_resp.status_code == 201
        game_id = uuid.UUID(create_resp.json()["games"][0]["id"])

        game = await db_session.get(TSMatchGame, game_id)
        assert game.player_mulligans == 0
        assert game.player_misplays == 0

    async def test_sub_moderator_save_forces_null_not_zero(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        game_id = uuid.UUID(create_resp.json()["games"][0]["id"])

        game = await db_session.get(TSMatchGame, game_id)
        assert game.player_mulligans is None
        assert game.player_misplays is None
        assert game.opponent_mulligans is None
        assert game.opponent_misplays is None

    async def test_sub_moderator_edit_never_deletes_a_moderators_events(
        self, client: AsyncClient, db_session
    ):
        """A sub-moderator's edit forces the derived counter cache back to
        NULL (D2), but must never delete the actual event rows a moderator
        previously entered — those stay visible (and unchanged) in the
        response's event list regardless of who saves the match next."""
        moderator = User(role="moderator")
        personal_id, meta_id = await _setup_decks(client, moderator)
        create_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(
                personal_id,
                meta_id,
                games=[
                    {
                        "game_number": 1,
                        "result": "win",
                        "player_mulligans": [{"comment": "kept a 6"}],
                    }
                ],
            ),
            headers=auth_headers(moderator),
        )
        match_id = create_resp.json()["id"]
        game_id = uuid.UUID(create_resp.json()["games"][0]["id"])

        # Same account/owner_id, but this token claims the base `user`
        # role — any sub-moderator caller's payload must omit the gated
        # field (defaults to `[]`), same as `owner_user` elsewhere in this
        # file.
        downgraded_headers = auth_headers(sub=str(moderator.id), role="user")
        resp = await client.put(
            f"{BASE}/matches/{match_id}",
            json=_match_payload(personal_id, meta_id, game2=None, game3=None),
            headers=downgraded_headers,
        )
        assert resp.status_code == 200
        assert [e["comment"] for e in resp.json()["games"][0]["player_mulligans"]] == [
            "kept a 6"
        ]

        game = await db_session.get(TSMatchGame, game_id)
        assert game.player_mulligans is None
