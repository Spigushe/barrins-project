"""Tests for GET /bff/tamiyo-scroll/sessions/{id}/report.pdf (S5)."""

from typing import Any

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.tamiyo_scroll.conftest import BASE, auth_headers


async def _setup_decks(client: AsyncClient, user: User) -> tuple[str, str]:
    headers = auth_headers(user)
    personal_resp = await client.post(
        f"{BASE}/personal-decks",
        json={"name": "Mono Red", "game": "magic", "category": "aggro"},
        headers=headers,
    )
    meta_resp = await client.post(
        f"{BASE}/meta-decks",
        json={
            "name": "Burn",
            "tier": 1.0,
            "category": "aggro",
            "top8": 1,
            "presence": 5,
            "expected": "as_expected",
        },
        headers=headers,
    )
    return personal_resp.json()["id"], meta_resp.json()["id"]


def _match_payload(
    personal_deck_id: str, opponent_deck_id: str, **overrides: Any
) -> dict:
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


async def _create_session(client: AsyncClient, headers: dict, personal_id: str) -> str:
    resp = await client.post(
        f"{BASE}/sessions",
        json={
            "name": "RC Toronto",
            "type": "tournament",
            "personal_deck_id": personal_id,
        },
        headers=headers,
    )
    return resp.json()["id"]


class TestGetSessionReport:
    async def test_returns_a_pdf_for_the_owned_session(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id, meta_id = await _setup_decks(client, owner_user)
        session_id = await _create_session(client, headers, personal_id)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, session_id=session_id),
            headers=headers,
        )

        resp = await client.get(
            f"{BASE}/sessions/{session_id}/report.pdf", headers=headers
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert "attachment" in resp.headers["content-disposition"]
        assert resp.content.startswith(b"%PDF-")

    async def test_foreign_session_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)
        session_id = await _create_session(
            client, auth_headers(owner_user), personal_id
        )

        resp = await client.get(
            f"{BASE}/sessions/{session_id}/report.pdf", headers=auth_headers(other_user)
        )
        assert resp.status_code == 404

    async def test_unknown_session_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.get(
            f"{BASE}/sessions/00000000-0000-0000-0000-000000000000/report.pdf",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_reuses_the_comparison_endpoints_numbers(
        self,
        client: AsyncClient,
        owner_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """The PDF is fed the exact same computed numbers /comparison returns.

        Non-regression per S5's Done statement: no parallel calculation path.
        Monkeypatches the WeasyPrint call itself (out of scope here — that's
        report.py's own concern) and captures what it was called with.
        """
        headers = auth_headers(owner_user)
        personal_id, meta_id = await _setup_decks(client, owner_user)
        session_id = await _create_session(client, headers, personal_id)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, session_id=session_id),
            headers=headers,
        )
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(
                personal_id, meta_id, session_id=session_id, game1="loss", game2="loss"
            ),
            headers=headers,
        )

        captured: dict[str, Any] = {}

        def _fake_render(**kwargs: Any) -> bytes:
            captured.update(kwargs)
            return b"%PDF-stub"

        monkeypatch.setattr(
            "app.api.tamiyo_scroll.sessions.render_session_report_pdf", _fake_render
        )

        comparison_resp = await client.get(
            f"{BASE}/sessions/{session_id}/comparison", headers=headers
        )
        comparison = comparison_resp.json()

        report_resp = await client.get(
            f"{BASE}/sessions/{session_id}/report.pdf", headers=headers
        )

        assert report_resp.status_code == 200
        assert report_resp.content == b"%PDF-stub"
        assert captured["period_match_count"] == comparison["session_match_count"]
        assert captured["period_wins"] == comparison["session_wins"]
        assert captured["period_losses"] == comparison["session_losses"]
        assert captured["baseline_wins"] == comparison["baseline_wins"]
        assert captured["baseline_losses"] == comparison["baseline_losses"]
        captured_rows = [
            {**row, "opponent_deck_id": str(row["opponent_deck_id"])}
            for row in captured["period_matchup_rows"]
        ]
        assert captured_rows == comparison["session_matchup_summary"]["rows"]

    async def test_uses_the_version_referenced_by_a_session_match_over_the_decks_latest(
        self, client: AsyncClient, owner_user: User, monkeypatch: pytest.MonkeyPatch
    ):
        """A session sticks to the version its matches were logged against.

        `MatchWrite` auto-stamps the deck's *current* latest version at
        POST time (S3) — it isn't retroactively repointed when a newer
        version is created afterwards. The report must follow the same
        rule: prefer what the session's matches actually reference over
        whatever happens to be the deck's latest version by the time the
        report is generated.
        """
        headers = auth_headers(owner_user)
        personal_id, meta_id = await _setup_decks(client, owner_user)

        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Goblin Guide"},
            headers=headers,
        )
        session_id = await _create_session(client, headers, personal_id)
        # Auto-stamped to v1 (the only version that exists yet).
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, session_id=session_id),
            headers=headers,
        )
        # A newer version now becomes the deck's overall latest — but the
        # match above still points at v1.
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Monastery Swiftspear"},
            headers=headers,
        )

        captured: dict[str, Any] = {}

        def _fake_render(**kwargs: Any) -> bytes:
            captured.update(kwargs)
            return b"%PDF-stub"

        monkeypatch.setattr(
            "app.api.tamiyo_scroll.sessions.render_session_report_pdf", _fake_render
        )
        resp = await client.get(
            f"{BASE}/sessions/{session_id}/report.pdf", headers=headers
        )

        assert resp.status_code == 200
        assert captured["colored_lines"] == [
            {"line": "4 Goblin Guide", "status": "neutral"}
        ]

    async def test_falls_back_to_latest_version_when_none_referenced(
        self, client: AsyncClient, owner_user: User, monkeypatch: pytest.MonkeyPatch
    ):
        headers = auth_headers(owner_user)
        personal_id, _ = await _setup_decks(client, owner_user)
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Goblin Guide"},
            headers=headers,
        )
        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Monastery Swiftspear"},
            headers=headers,
        )
        session_id = await _create_session(client, headers, personal_id)

        captured: dict[str, Any] = {}

        def _fake_render(**kwargs: Any) -> bytes:
            captured.update(kwargs)
            return b"%PDF-stub"

        monkeypatch.setattr(
            "app.api.tamiyo_scroll.sessions.render_session_report_pdf", _fake_render
        )
        resp = await client.get(
            f"{BASE}/sessions/{session_id}/report.pdf", headers=headers
        )

        assert resp.status_code == 200
        assert captured["colored_lines"] == [
            {"line": "4 Monastery Swiftspear", "status": "neutral"}
        ]

    async def test_handles_a_deck_with_no_decklist_version_yet(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id, _ = await _setup_decks(client, owner_user)
        session_id = await _create_session(client, headers, personal_id)

        resp = await client.get(
            f"{BASE}/sessions/{session_id}/report.pdf", headers=headers
        )

        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF-")
