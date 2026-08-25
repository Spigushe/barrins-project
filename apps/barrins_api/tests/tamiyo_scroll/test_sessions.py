"""Tests for /bff/tamiyo-scroll/sessions (S9)."""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update

from app.models.tamiyo_scroll import TSMatch, TSSession
from tests.identity_auth import FakeUser as User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


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


class TestCreateSession:
    async def test_creates_session(self, client: AsyncClient, owner_user: User):
        personal_id, _ = await _setup_decks(client, owner_user)
        resp = await client.post(
            f"{BASE}/sessions",
            json={
                "name": "RC Toronto 2026",
                "type": "tournament",
                "personal_deck_id": personal_id,
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "RC Toronto 2026"
        assert body["type"] == "tournament"
        assert body["personal_deck_id"] == personal_id
        assert body["ended_at"] is None
        assert body["closed_at"] is None
        assert body["archived_at"] is None
        assert body["hue"] is None
        assert body["location"] is None

    async def test_creates_session_with_dates_and_hue(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        resp = await client.post(
            f"{BASE}/sessions",
            json={
                "name": "RC Toronto 2026",
                "type": "tournament",
                "personal_deck_id": personal_id,
                "location": "Toronto, ON",
                "notes": "Day 1",
                "started_at": "2026-08-01T10:00:00Z",
                "ended_at": "2026-08-01T18:00:00Z",
                "hue": 210,
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["location"] == "Toronto, ON"
        assert body["notes"] == "Day 1"
        assert body["started_at"] == "2026-08-01T10:00:00Z"
        assert body["ended_at"] == "2026-08-01T18:00:00Z"
        assert body["hue"] == 210
        # started_at/ended_at are independent of the Close/Reopen workflow.
        assert body["closed_at"] is None

    async def test_hue_out_of_range_is_rejected_on_create(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        resp = await client.post(
            f"{BASE}/sessions",
            json={
                "name": "S1",
                "type": "training",
                "personal_deck_id": personal_id,
                "hue": 360,
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 422

    async def test_unknown_personal_deck_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.post(
            f"{BASE}/sessions",
            json={
                "name": "Weekly Training",
                "type": "training",
                "personal_deck_id": "00000000-0000-0000-0000-000000000000",
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_foreign_personal_deck_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        personal_id, _ = await _setup_decks(client, other_user)
        resp = await client.post(
            f"{BASE}/sessions",
            json={
                "name": "Weekly Training",
                "type": "training",
                "personal_deck_id": personal_id,
            },
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404


class TestListSessions:
    async def test_lists_own_sessions(self, client: AsyncClient, owner_user: User):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        resp = await client.get(f"{BASE}/sessions", headers=headers)
        assert len(resp.json()) == 1

    async def test_does_not_leak_other_users_sessions(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        personal_id, _ = await _setup_decks(client, other_user)
        await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=auth_headers(other_user),
        )
        resp = await client.get(f"{BASE}/sessions", headers=auth_headers(owner_user))
        assert resp.json() == []

    async def test_filters_by_personal_deck_id(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        deck_a, _ = await _setup_decks(client, owner_user)
        deck_b_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Azorius Control", "game": "magic", "category": "control"},
            headers=headers,
        )
        deck_b = deck_b_resp.json()["id"]
        await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": deck_a},
            headers=headers,
        )
        await client.post(
            f"{BASE}/sessions",
            json={"name": "S2", "type": "training", "personal_deck_id": deck_b},
            headers=headers,
        )

        resp = await client.get(
            f"{BASE}/sessions?personal_deck_id={deck_a}", headers=headers
        )
        assert [s["name"] for s in resp.json()] == ["S1"]

    async def test_archived_excluded_by_default_included_with_flag(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = create_resp.json()["id"]
        await client.delete(f"{BASE}/sessions/{session_id}", headers=headers)

        resp = await client.get(f"{BASE}/sessions", headers=headers)
        assert resp.json() == []

        resp = await client.get(
            f"{BASE}/sessions?include_archived=true", headers=headers
        )
        assert len(resp.json()) == 1

    async def test_sorts_by_name(self, client: AsyncClient, owner_user: User):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        for name in ["Charlie", "Alpha", "Bravo"]:
            await client.post(
                f"{BASE}/sessions",
                json={
                    "name": name,
                    "type": "training",
                    "personal_deck_id": personal_id,
                },
                headers=headers,
            )

        resp = await client.get(
            f"{BASE}/sessions?sort_by=name&sort_dir=asc", headers=headers
        )
        assert [s["name"] for s in resp.json()] == ["Alpha", "Bravo", "Charlie"]

    async def test_limit_and_offset_paginate(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        for i in range(3):
            await client.post(
                f"{BASE}/sessions",
                json={
                    "name": f"S{i}",
                    "type": "training",
                    "personal_deck_id": personal_id,
                },
                headers=headers,
            )

        resp = await client.get(
            f"{BASE}/sessions?sort_by=name&sort_dir=asc&limit=2&offset=0",
            headers=headers,
        )
        assert [s["name"] for s in resp.json()] == ["S0", "S1"]

        resp = await client.get(
            f"{BASE}/sessions?sort_by=name&sort_dir=asc&limit=2&offset=2",
            headers=headers,
        )
        assert [s["name"] for s in resp.json()] == ["S2"]

    async def test_search_filters_by_name_case_insensitive(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        for name in ["RC Toronto", "Weekly Training"]:
            await client.post(
                f"{BASE}/sessions",
                json={
                    "name": name,
                    "type": "training",
                    "personal_deck_id": personal_id,
                },
                headers=headers,
            )

        resp = await client.get(f"{BASE}/sessions?search=toronto", headers=headers)
        assert [s["name"] for s in resp.json()] == ["RC Toronto"]


class TestUpdateSession:
    async def test_renames_and_updates_notes(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = create_resp.json()["id"]

        resp = await client.patch(
            f"{BASE}/sessions/{session_id}",
            json={"name": "Renamed", "notes": "Some notes"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"
        assert resp.json()["notes"] == "Some notes"

    async def test_close_stamps_closed_at(self, client: AsyncClient, owner_user: User):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = create_resp.json()["id"]
        assert create_resp.json()["closed_at"] is None

        resp = await client.patch(
            f"{BASE}/sessions/{session_id}", json={"close": True}, headers=headers
        )
        assert resp.json()["closed_at"] is not None

    async def test_reopen_clears_closed_at(self, client: AsyncClient, owner_user: User):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = create_resp.json()["id"]
        await client.patch(
            f"{BASE}/sessions/{session_id}", json={"close": True}, headers=headers
        )

        resp = await client.patch(
            f"{BASE}/sessions/{session_id}", json={"reopen": True}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["closed_at"] is None

    async def test_started_at_and_ended_at_are_independent_of_close_reopen(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = create_resp.json()["id"]

        resp = await client.patch(
            f"{BASE}/sessions/{session_id}",
            json={
                "started_at": "2026-08-01T10:00:00Z",
                "ended_at": "2026-08-01T18:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["started_at"] == "2026-08-01T10:00:00Z"
        assert body["ended_at"] == "2026-08-01T18:00:00Z"
        # Setting ended_at directly must not touch the Close/Reopen state.
        assert body["closed_at"] is None

        # Closing afterwards must not clear the manually-set dates.
        resp = await client.patch(
            f"{BASE}/sessions/{session_id}", json={"close": True}, headers=headers
        )
        body = resp.json()
        assert body["closed_at"] is not None
        assert body["started_at"] == "2026-08-01T10:00:00Z"
        assert body["ended_at"] == "2026-08-01T18:00:00Z"

    async def test_updates_location_and_hue(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = create_resp.json()["id"]

        resp = await client.patch(
            f"{BASE}/sessions/{session_id}",
            json={"location": "Toronto, ON", "hue": 210},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["location"] == "Toronto, ON"
        assert resp.json()["hue"] == 210

    async def test_hue_out_of_range_is_rejected(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = create_resp.json()["id"]

        resp = await client.patch(
            f"{BASE}/sessions/{session_id}", json={"hue": 360}, headers=headers
        )
        assert resp.status_code == 422

    async def test_restore_clears_archived_at(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = create_resp.json()["id"]
        await client.delete(f"{BASE}/sessions/{session_id}", headers=headers)

        resp = await client.patch(
            f"{BASE}/sessions/{session_id}", json={"restore": True}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["archived_at"] is None

        list_resp = await client.get(f"{BASE}/sessions", headers=headers)
        assert [s["id"] for s in list_resp.json()] == [session_id]

    async def test_foreign_session_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        create_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = create_resp.json()["id"]

        resp = await client.patch(
            f"{BASE}/sessions/{session_id}",
            json={"name": "Hijacked"},
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestArchiveSession:
    async def test_archives_without_touching_matches_session_id(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        session_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = session_resp.json()["id"]
        match_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, session_id=session_id),
            headers=headers,
        )
        match_id = match_resp.json()["id"]

        resp = await client.delete(f"{BASE}/sessions/{session_id}", headers=headers)
        assert resp.status_code == 204

        matches_resp = await client.get(f"{BASE}/matches", headers=headers)
        match = next(m for m in matches_resp.json() if m["id"] == match_id)
        assert match["session_id"] == session_id


async def _set_created_at(db_session, table, row_id: str, when: datetime) -> None:
    """Backdate `created_at` directly in the DB.

    All requests in a test share one outer Postgres transaction, so
    `server_default=func.now()` (transaction-start time) yields identical
    timestamps for every row created in that test — a test-harness
    artifact, never true across separate requests in production. Ordering
    assertions that depend on `created_at` need explicit backdating.
    """
    await db_session.execute(
        update(table).where(table.id == uuid.UUID(row_id)).values(created_at=when)
    )
    await db_session.commit()


class TestSessionComparison:
    async def test_baseline_excludes_session_own_matches_includes_prior_history(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        base_time = datetime(2026, 1, 1, tzinfo=UTC)

        # Ungrouped match logged before any session exists.
        old_match_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, game1="loss", game2="loss"),
            headers=headers,
        )
        await _set_created_at(
            db_session, TSMatch, old_match_resp.json()["id"], base_time
        )

        # An earlier session, whose matches must still count in the baseline.
        earlier_session_resp = await client.post(
            f"{BASE}/sessions",
            json={
                "name": "Earlier",
                "type": "training",
                "personal_deck_id": personal_id,
            },
            headers=headers,
        )
        earlier_session_id = earlier_session_resp.json()["id"]
        await _set_created_at(
            db_session, TSSession, earlier_session_id, base_time + timedelta(days=1)
        )
        earlier_match_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, session_id=earlier_session_id),
            headers=headers,
        )
        await _set_created_at(
            db_session,
            TSMatch,
            earlier_match_resp.json()["id"],
            base_time + timedelta(days=2),
        )

        # The session under test.
        session_resp = await client.post(
            f"{BASE}/sessions",
            json={
                "name": "Under test",
                "type": "tournament",
                "personal_deck_id": personal_id,
            },
            headers=headers,
        )
        session_id = session_resp.json()["id"]
        await _set_created_at(
            db_session, TSSession, session_id, base_time + timedelta(days=3)
        )
        own_match_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, session_id=session_id),
            headers=headers,
        )
        await _set_created_at(
            db_session,
            TSMatch,
            own_match_resp.json()["id"],
            base_time + timedelta(days=4),
        )

        resp = await client.get(
            f"{BASE}/sessions/{session_id}/comparison", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_match_count"] == 1
        assert body["baseline_match_count"] == 2
        # Own match: win/loss/win = 2W/1L. Baseline: old match (loss/loss/win
        # = 1W/2L) + earlier session's match (win/loss/win = 2W/1L) = 3W/3L.
        assert body["session_wins"] == 2
        assert body["session_losses"] == 1
        assert body["baseline_wins"] == 3
        assert body["baseline_losses"] == 3

    async def test_foreign_session_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        session_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = session_resp.json()["id"]

        resp = await client.get(
            f"{BASE}/sessions/{session_id}/comparison",
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestMatchSessionLink:
    async def test_creates_match_with_session(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        headers = auth_headers(owner_user)
        session_resp = await client.post(
            f"{BASE}/sessions",
            json={"name": "S1", "type": "training", "personal_deck_id": personal_id},
            headers=headers,
        )
        session_id = session_resp.json()["id"]

        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, session_id=session_id),
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["session_id"] == session_id

    async def test_unknown_session_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(
                personal_id,
                meta_id,
                session_id="00000000-0000-0000-0000-000000000000",
            ),
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_session_for_a_different_deck_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id, meta_id = await _setup_decks(client, owner_user)
        other_deck_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Azorius Control", "game": "magic", "category": "control"},
            headers=headers,
        )
        other_deck_id = other_deck_resp.json()["id"]
        session_resp = await client.post(
            f"{BASE}/sessions",
            json={
                "name": "S1",
                "type": "training",
                "personal_deck_id": other_deck_id,
            },
            headers=headers,
        )
        session_id = session_resp.json()["id"]

        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, session_id=session_id),
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_foreign_session_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        personal_id, meta_id = await _setup_decks(client, owner_user)
        other_personal_id, _ = await _setup_decks(client, other_user)
        other_session_resp = await client.post(
            f"{BASE}/sessions",
            json={
                "name": "S1",
                "type": "training",
                "personal_deck_id": other_personal_id,
            },
            headers=auth_headers(other_user),
        )
        other_session_id = other_session_resp.json()["id"]

        resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, session_id=other_session_id),
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404
