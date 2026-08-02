"""Tests for /teams (S2, "Team Decks") — creation, membership, name-based
deck flagging, threads.

Follows `test_ownership.py`/`test_personal_decks.py`'s conventions:
`owner_user`/`other_user`/`third_user` fixtures, `auth_headers()`, and a
uniform 404 for both "doesn't exist" and "not yours" (never 403).
"""

import uuid
from datetime import timedelta

from httpx import AsyncClient, Response
from sqlalchemy import update

from app.models.tamiyo_scroll import TSInviteAttempt
from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


async def _create_team(
    client: AsyncClient, user: User, name: str = "Dream Team"
) -> dict:
    resp = await client.post(
        f"{BASE}/teams", json={"name": name}, headers=auth_headers(user)
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _join_team(client: AsyncClient, user: User, invite_code: str) -> Response:
    return await client.post(
        f"{BASE}/teams/join",
        json={"invite_code": invite_code},
        headers=auth_headers(user),
    )


async def _clear_invite_cooldown(db_session, user: User) -> None:
    """Backdates `last_attempt_at` past the 5s cooldown — for tests that
    make two genuine join attempts in a row, faster than a real user
    could type a second code."""
    await db_session.execute(
        update(TSInviteAttempt)
        .where(TSInviteAttempt.user_id == user.id)
        .values(last_attempt_at=TSInviteAttempt.last_attempt_at - timedelta(seconds=10))
    )
    await db_session.commit()


async def _create_personal_deck(client: AsyncClient, user: User, name: str) -> str:
    resp = await client.post(
        f"{BASE}/personal-decks",
        json={"name": name, "game": "magic", "category": "midrange"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _flag_deck(
    client: AsyncClient, owner: User, team_id: str, deck_id: str
) -> Response:
    return await client.post(
        f"{BASE}/teams/{team_id}/decks/flags",
        json={"deck_id": deck_id},
        headers=auth_headers(owner),
    )


class TestCreateTeam:
    async def test_creates_team_with_8_char_invite_code(
        self, client: AsyncClient, owner_user: User
    ):
        team = await _create_team(client, owner_user)
        assert team["name"] == "Dream Team"
        assert len(team["invite_code"]) == 8
        assert team["owner_id"] == str(owner_user.id)
        assert len(team["members"]) == 1
        assert team["members"][0]["user_id"] == str(owner_user.id)
        assert team["members"][0]["is_owner"] is True


class TestJoinTeam:
    async def test_second_user_joins_via_invite_code(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)

        resp = await _join_team(client, other_user, team["invite_code"])

        assert resp.status_code == 200
        member_ids = {m["user_id"] for m in resp.json()["members"]}
        assert member_ids == {str(owner_user.id), str(other_user.id)}

    async def test_dash_and_lowercase_are_normalized(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        code = team["invite_code"]
        spaced = f"{code[:4]}-{code[4:]}".lower()

        resp = await _join_team(client, other_user, spaced)

        assert resp.status_code == 200

    async def test_invalid_code_returns_400(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await _join_team(client, owner_user, "NOTREAL1")
        assert resp.status_code == 400

    async def test_joining_twice_is_idempotent(
        self, client: AsyncClient, owner_user: User, other_user: User, db_session
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])
        await _clear_invite_cooldown(db_session, other_user)

        resp = await _join_team(client, other_user, team["invite_code"])

        assert resp.status_code == 200
        member_ids = [m["user_id"] for m in resp.json()["members"]]
        assert member_ids.count(str(other_user.id)) == 1

    async def test_multi_team_membership_allowed(
        self,
        client: AsyncClient,
        owner_user: User,
        other_user: User,
        third_user: User,
        db_session,
    ):
        team_a = await _create_team(client, owner_user, "Team A")
        team_b = await _create_team(client, third_user, "Team B")

        resp_a = await _join_team(client, other_user, team_a["invite_code"])
        await _clear_invite_cooldown(db_session, other_user)
        resp_b = await _join_team(client, other_user, team_b["invite_code"])

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

        mine = await client.get(f"{BASE}/teams/mine", headers=auth_headers(other_user))
        assert {t["name"] for t in mine.json()} == {"Team A", "Team B"}

    async def test_rate_limit_blocks_second_attempt_within_5_seconds(
        self, client: AsyncClient, owner_user: User
    ):
        await _join_team(client, owner_user, "WRONG001")
        resp = await _join_team(client, owner_user, "WRONG002")
        assert resp.status_code == 429

    async def test_rate_limit_blocks_6th_attempt_within_a_minute(
        self, client: AsyncClient, owner_user: User, db_session
    ):
        """Attempts are spaced past the 5s cooldown (by backdating
        `last_attempt_at`) so only the per-minute cap is exercised."""
        for _ in range(5):
            resp = await _join_team(client, owner_user, "WRONG001")
            assert resp.status_code == 400
            await db_session.execute(
                update(TSInviteAttempt)
                .where(TSInviteAttempt.user_id == owner_user.id)
                .values(
                    last_attempt_at=TSInviteAttempt.last_attempt_at
                    - timedelta(seconds=10)
                )
            )
            await db_session.commit()

        resp = await _join_team(client, owner_user, "WRONG001")
        assert resp.status_code == 429


class TestGetTeam:
    async def test_member_can_read_team(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])

        resp = await client.get(
            f"{BASE}/teams/{team['id']}", headers=auth_headers(other_user)
        )
        assert resp.status_code == 200

    async def test_non_member_gets_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)

        resp = await client.get(
            f"{BASE}/teams/{team['id']}", headers=auth_headers(other_user)
        )
        assert resp.status_code == 404

    async def test_unknown_team_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.get(
            f"{BASE}/teams/{uuid.uuid4()}", headers=auth_headers(owner_user)
        )
        assert resp.status_code == 404


class TestUpdateTeam:
    async def test_owner_can_set_description(
        self, client: AsyncClient, owner_user: User
    ):
        team = await _create_team(client, owner_user)

        resp = await client.patch(
            f"{BASE}/teams/{team['id']}",
            json={"description": "We test cards together."},
            headers=auth_headers(owner_user),
        )

        assert resp.status_code == 200
        assert resp.json()["description"] == "We test cards together."

    async def test_non_owner_member_cannot_update(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])

        resp = await client.patch(
            f"{BASE}/teams/{team['id']}",
            json={"description": "hijacked"},
            headers=auth_headers(other_user),
        )

        assert resp.status_code == 404


class TestLeaveAndRemoveMember:
    async def test_member_can_leave(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])

        resp = await client.post(
            f"{BASE}/teams/{team['id']}/leave", headers=auth_headers(other_user)
        )
        assert resp.status_code == 204

        get_resp = await client.get(
            f"{BASE}/teams/{team['id']}", headers=auth_headers(other_user)
        )
        assert get_resp.status_code == 404

    async def test_owner_cannot_leave(self, client: AsyncClient, owner_user: User):
        team = await _create_team(client, owner_user)

        resp = await client.post(
            f"{BASE}/teams/{team['id']}/leave", headers=auth_headers(owner_user)
        )
        assert resp.status_code == 409

    async def test_owner_removes_a_member(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])

        resp = await client.delete(
            f"{BASE}/teams/{team['id']}/members/{other_user.id}",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 204

        get_resp = await client.get(
            f"{BASE}/teams/{team['id']}", headers=auth_headers(other_user)
        )
        assert get_resp.status_code == 404

    async def test_non_owner_cannot_remove_a_member(
        self, client: AsyncClient, owner_user: User, other_user: User, third_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])
        await _join_team(client, third_user, team["invite_code"])

        resp = await client.delete(
            f"{BASE}/teams/{team['id']}/members/{third_user.id}",
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestDeleteTeam:
    async def test_wrong_code_blocks_deletion(
        self, client: AsyncClient, owner_user: User
    ):
        team = await _create_team(client, owner_user)

        resp = await client.request(
            "DELETE",
            f"{BASE}/teams/{team['id']}",
            json={"invite_code": "WRONGCOD"},
            headers=auth_headers(owner_user),
        )

        assert resp.status_code == 400
        get_resp = await client.get(
            f"{BASE}/teams/{team['id']}", headers=auth_headers(owner_user)
        )
        assert get_resp.status_code == 200

    async def test_correct_code_deletes_and_leaves_decks_untouched(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])
        deck_id = await _create_personal_deck(client, other_user, "Boros Aggro")
        await _flag_deck(client, owner_user, team["id"], deck_id)

        resp = await client.request(
            "DELETE",
            f"{BASE}/teams/{team['id']}",
            json={"invite_code": team["invite_code"]},
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 204

        get_resp = await client.get(
            f"{BASE}/teams/{team['id']}", headers=auth_headers(owner_user)
        )
        assert get_resp.status_code == 404

        # Deletion isolation: the deck itself (owned by other_user) is
        # untouched — it was never linked by anything but the now-gone flag.
        decks_resp = await client.get(
            f"{BASE}/personal-decks", headers=auth_headers(other_user)
        )
        assert any(d["id"] == deck_id for d in decks_resp.json())

    async def test_non_owner_cannot_delete(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])

        resp = await client.request(
            "DELETE",
            f"{BASE}/teams/{team['id']}",
            json={"invite_code": team["invite_code"]},
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestDeckReportViaTeamMembership:
    async def test_team_member_can_fetch_owner_deck_report(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        deck_id = await _create_personal_deck(client, owner_user, "Mono Red")
        await _flag_deck(client, owner_user, team["id"], deck_id)
        await _join_team(client, other_user, team["invite_code"])

        resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/report.pdf",
            headers=auth_headers(other_user),
        )

        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF-")

    async def test_non_member_still_gets_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        deck_id = await _create_personal_deck(client, owner_user, "Mono Red")
        await _flag_deck(client, owner_user, team["id"], deck_id)

        resp = await client.get(
            f"{BASE}/personal-decks/{deck_id}/report.pdf",
            headers=auth_headers(other_user),
        )

        assert resp.status_code == 404


class TestTeamDeckThreads:
    async def test_owner_enables_thread_and_member_can_post(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        deck_id = await _create_personal_deck(client, owner_user, "Mono Red")
        await _flag_deck(client, owner_user, team["id"], deck_id)
        await _join_team(client, other_user, team["invite_code"])

        enable_resp = await client.post(
            f"{BASE}/teams/{team['id']}/decks/mono red/thread",
            headers=auth_headers(owner_user),
        )
        assert enable_resp.status_code == 201

        post_resp = await client.post(
            f"{BASE}/teams/{team['id']}/decks/mono red/thread/messages",
            json={"body": "This deck is spicy."},
            headers=auth_headers(other_user),
        )
        assert post_resp.status_code == 201

        list_resp = await client.get(
            f"{BASE}/teams/{team['id']}/decks/mono red/thread/messages",
            headers=auth_headers(owner_user),
        )
        assert list_resp.status_code == 200
        bodies = [m["body"] for m in list_resp.json()]
        assert bodies == ["This deck is spicy."]

    async def test_non_member_cannot_post(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        deck_id = await _create_personal_deck(client, owner_user, "Mono Red")
        await _flag_deck(client, owner_user, team["id"], deck_id)
        await client.post(
            f"{BASE}/teams/{team['id']}/decks/mono red/thread",
            headers=auth_headers(owner_user),
        )

        resp = await client.post(
            f"{BASE}/teams/{team['id']}/decks/mono red/thread/messages",
            json={"body": "sneaking in"},
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404

    async def test_non_owner_cannot_enable_thread(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        deck_id = await _create_personal_deck(client, owner_user, "Mono Red")
        await _flag_deck(client, owner_user, team["id"], deck_id)
        await _join_team(client, other_user, team["invite_code"])

        resp = await client.post(
            f"{BASE}/teams/{team['id']}/decks/mono red/thread",
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404

    async def test_cannot_enable_thread_for_an_unflagged_name(
        self, client: AsyncClient, owner_user: User
    ):
        team = await _create_team(client, owner_user)

        resp = await client.post(
            f"{BASE}/teams/{team['id']}/decks/nonexistent/thread",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404


class TestFlagDeckName:
    async def test_owner_flags_a_members_deck(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])
        deck_id = await _create_personal_deck(client, other_user, "Boros Aggro")

        resp = await _flag_deck(client, owner_user, team["id"], deck_id)

        assert resp.status_code == 201
        body = resp.json()
        assert body["deck_name"] == "Boros Aggro"
        assert body["owners"] == [
            {"deck_id": deck_id, "display": other_user.display_name or other_user.email}
        ]

    async def test_non_owner_cannot_flag(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])
        deck_id = await _create_personal_deck(client, other_user, "Boros Aggro")

        resp = await client.post(
            f"{BASE}/teams/{team['id']}/decks/flags",
            json={"deck_id": deck_id},
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404

    async def test_cannot_flag_a_non_members_deck(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        deck_id = await _create_personal_deck(client, other_user, "Boros Aggro")

        resp = await _flag_deck(client, owner_user, team["id"], deck_id)
        assert resp.status_code == 404

    async def test_flagging_twice_is_idempotent(
        self, client: AsyncClient, owner_user: User
    ):
        team = await _create_team(client, owner_user)
        deck_id = await _create_personal_deck(client, owner_user, "Mono Red")

        first = await _flag_deck(client, owner_user, team["id"], deck_id)
        second = await _flag_deck(client, owner_user, team["id"], deck_id)

        assert first.status_code == 201
        assert second.status_code == 201

        decks_resp = await client.get(
            f"{BASE}/teams/{team['id']}/decks", headers=auth_headers(owner_user)
        )
        assert len(decks_resp.json()) == 1

    async def test_owner_unflags_a_name(self, client: AsyncClient, owner_user: User):
        team = await _create_team(client, owner_user)
        deck_id = await _create_personal_deck(client, owner_user, "Mono Red")
        await _flag_deck(client, owner_user, team["id"], deck_id)

        resp = await client.delete(
            f"{BASE}/teams/{team['id']}/decks/flags/mono red",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 204

        decks_resp = await client.get(
            f"{BASE}/teams/{team['id']}/decks", headers=auth_headers(owner_user)
        )
        assert decks_resp.json() == []

    async def test_non_owner_cannot_unflag(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        deck_id = await _create_personal_deck(client, owner_user, "Mono Red")
        await _flag_deck(client, owner_user, team["id"], deck_id)
        await _join_team(client, other_user, team["invite_code"])

        resp = await client.delete(
            f"{BASE}/teams/{team['id']}/decks/flags/mono red",
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404


class TestListMemberDecks:
    async def test_owner_sees_every_members_decks(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])
        await _create_personal_deck(client, owner_user, "Mono Red")
        await _create_personal_deck(client, other_user, "Boros Aggro")

        resp = await client.get(
            f"{BASE}/teams/{team['id']}/members/decks", headers=auth_headers(owner_user)
        )

        assert resp.status_code == 200
        names = {d["name"] for d in resp.json()}
        assert names == {"Mono Red", "Boros Aggro"}
        assert all(d["is_flagged"] is False for d in resp.json())

    async def test_non_owner_cannot_list_member_decks(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])

        resp = await client.get(
            f"{BASE}/teams/{team['id']}/members/decks", headers=auth_headers(other_user)
        )
        assert resp.status_code == 404


class TestNameBasedAutoSharing:
    async def test_flagging_one_deck_auto_includes_every_same_named_deck(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        """Once a name is flagged, every member's same-named deck is
        shared automatically — no per-deck action from the other members."""
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])
        owner_deck_id = await _create_personal_deck(client, owner_user, "King T'Challa")
        await _create_personal_deck(client, other_user, "King T'Challa")

        await _flag_deck(client, owner_user, team["id"], owner_deck_id)

        resp = await client.get(
            f"{BASE}/teams/{team['id']}/decks", headers=auth_headers(other_user)
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        owner_displays = {o["display"] for o in resp.json()[0]["owners"]}
        assert owner_displays == {
            owner_user.display_name or owner_user.email,
            other_user.display_name or other_user.email,
        }

    async def test_renaming_into_a_flagged_name_joins_the_team_deck(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])
        owner_deck_id = await _create_personal_deck(client, owner_user, "King T'Challa")
        await _flag_deck(client, owner_user, team["id"], owner_deck_id)
        other_deck_id = await _create_personal_deck(
            client, other_user, "Something Else"
        )

        rename_resp = await client.patch(
            f"{BASE}/personal-decks/{other_deck_id}",
            json={"name": "King T'Challa"},
            headers=auth_headers(other_user),
        )
        assert rename_resp.status_code == 200

        resp = await client.get(
            f"{BASE}/teams/{team['id']}/decks", headers=auth_headers(owner_user)
        )
        owner_displays = {o["display"] for o in resp.json()[0]["owners"]}
        assert (other_user.display_name or other_user.email) in owner_displays


class TestTeamDeckReport:
    async def test_returns_one_cumulative_pdf_for_the_flagged_name(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        await _join_team(client, other_user, team["invite_code"])
        owner_deck_id = await _create_personal_deck(client, owner_user, "King T'Challa")
        await _create_personal_deck(client, other_user, "King T'Challa")
        await _flag_deck(client, owner_user, team["id"], owner_deck_id)

        resp = await client.get(
            f"{BASE}/teams/{team['id']}/decks/king t'challa/report.pdf",
            headers=auth_headers(other_user),
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF-")

    async def test_non_member_gets_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        team = await _create_team(client, owner_user)
        deck_id = await _create_personal_deck(client, owner_user, "King T'Challa")
        await _flag_deck(client, owner_user, team["id"], deck_id)

        resp = await client.get(
            f"{BASE}/teams/{team['id']}/decks/king t'challa/report.pdf",
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404

    async def test_unflagged_name_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        team = await _create_team(client, owner_user)

        resp = await client.get(
            f"{BASE}/teams/{team['id']}/decks/nonexistent/report.pdf",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404
