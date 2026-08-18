"""Tests for GET /bff/tamiyo-scroll/personal-decks/{id}/report.pdf (S5).

Deck-level counterpart to `test_session_report.py`: no session required,
a rolling last-30-days window instead of explicit match membership, and
S1's shared/merged data folded in when the viewer opted in.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.models.tamiyo_scroll import TSMatch
from app.models.user import User
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


async def _set_created_at(db_session, table, row_id: str, when: datetime) -> None:
    """Backdate `created_at` directly in the DB — see `test_sessions.py`'s
    identical helper: matches created within one test's outer transaction
    all share the same `server_default=func.now()` timestamp otherwise."""
    await db_session.execute(
        update(table).where(table.id == uuid.UUID(row_id)).values(created_at=when)
    )
    await db_session.commit()


class TestGetDeckReport:
    async def test_returns_a_pdf_for_the_owned_deck(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id, meta_id = await _setup_decks(client, owner_user)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )

        resp = await client.get(
            f"{BASE}/personal-decks/{personal_id}/report.pdf", headers=headers
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert "attachment" in resp.headers["content-disposition"]
        assert resp.content.startswith(b"%PDF-")

    async def test_foreign_deck_returns_404(
        self, client: AsyncClient, owner_user: User, other_user: User
    ):
        personal_id, _ = await _setup_decks(client, owner_user)

        resp = await client.get(
            f"{BASE}/personal-decks/{personal_id}/report.pdf",
            headers=auth_headers(other_user),
        )
        assert resp.status_code == 404

    async def test_unknown_deck_returns_404(
        self, client: AsyncClient, owner_user: User
    ):
        resp = await client.get(
            f"{BASE}/personal-decks/00000000-0000-0000-0000-000000000000/report.pdf",
            headers=auth_headers(owner_user),
        )
        assert resp.status_code == 404

    async def test_handles_a_deck_with_no_decklist_version_yet(
        self, client: AsyncClient, owner_user: User
    ):
        headers = auth_headers(owner_user)
        personal_id, _ = await _setup_decks(client, owner_user)

        resp = await client.get(
            f"{BASE}/personal-decks/{personal_id}/report.pdf", headers=headers
        )

        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF-")

    async def test_splits_matches_into_last_30_days_vs_baseline(
        self,
        client: AsyncClient,
        owner_user: User,
        db_session,
        monkeypatch: pytest.MonkeyPatch,
    ):
        headers = auth_headers(owner_user)
        personal_id, meta_id = await _setup_decks(client, owner_user)

        old_match_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id, game1="loss", game2="loss"),
            headers=headers,
        )
        await _set_created_at(
            db_session,
            TSMatch,
            old_match_resp.json()["id"],
            datetime.now(UTC) - timedelta(days=45),
        )

        recent_match_resp = await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        await _set_created_at(
            db_session,
            TSMatch,
            recent_match_resp.json()["id"],
            datetime.now(UTC) - timedelta(days=1),
        )

        captured: dict[str, Any] = {}

        def _fake_render(**kwargs: Any) -> bytes:
            captured.update(kwargs)
            return b"%PDF-stub"

        monkeypatch.setattr(
            "app.api.tamiyo_scroll.personal_decks.render_session_report_pdf",
            _fake_render,
        )

        resp = await client.get(
            f"{BASE}/personal-decks/{personal_id}/report.pdf", headers=headers
        )

        assert resp.status_code == 200
        assert captured["period_match_count"] == 1
        assert captured["period_wins"] == 2
        assert captured["period_losses"] == 1
        assert captured["baseline_wins"] == 1
        assert captured["baseline_losses"] == 2

    async def test_excludes_matches_against_archived_opponent_decks(
        self,
        client: AsyncClient,
        owner_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ):
        headers = auth_headers(owner_user)
        personal_id, meta_id = await _setup_decks(client, owner_user)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
            headers=headers,
        )
        await client.delete(f"{BASE}/meta-decks/{meta_id}", headers=headers)

        captured: dict[str, Any] = {}

        def _fake_render(**kwargs: Any) -> bytes:
            captured.update(kwargs)
            return b"%PDF-stub"

        monkeypatch.setattr(
            "app.api.tamiyo_scroll.personal_decks.render_session_report_pdf",
            _fake_render,
        )
        resp = await client.get(
            f"{BASE}/personal-decks/{personal_id}/report.pdf", headers=headers
        )

        assert resp.status_code == 200
        assert captured["period_match_count"] == 0
        assert captured["period_matchup_rows"] == []

    async def test_includes_shared_data_when_receiving_is_enabled(
        self,
        client: AsyncClient,
        owner_user: User,
        other_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ):
        other_headers = auth_headers(other_user)
        other_personal_id, other_meta_id = await _setup_decks(client, other_user)
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(other_personal_id, other_meta_id),
            headers=other_headers,
        )
        await client.patch(
            f"{BASE}/me/settings", json={"data_shared": True}, headers=other_headers
        )

        owner_headers = auth_headers(owner_user)
        personal_resp = await client.post(
            f"{BASE}/personal-decks",
            json={"name": "Mono Red", "game": "magic", "category": "aggro"},
            headers=owner_headers,
        )
        personal_id = personal_resp.json()["id"]
        await client.patch(
            f"{BASE}/me/settings",
            json={"receive_shared_data": True},
            headers=owner_headers,
        )

        captured: dict[str, Any] = {}

        def _fake_render(**kwargs: Any) -> bytes:
            captured.update(kwargs)
            return b"%PDF-stub"

        monkeypatch.setattr(
            "app.api.tamiyo_scroll.personal_decks.render_session_report_pdf",
            _fake_render,
        )
        resp = await client.get(
            f"{BASE}/personal-decks/{personal_id}/report.pdf",
            headers=owner_headers,
        )

        assert resp.status_code == 200
        assert captured["period_match_count"] == 1
        assert captured["period_matchup_rows"][0]["opponent_deck_name"] == "Burn"
        assert captured["period_matchup_rows"][0]["is_readonly"] is True

    async def test_uses_the_version_referenced_by_a_recent_match_over_the_decks_latest(
        self, client: AsyncClient, owner_user: User, monkeypatch: pytest.MonkeyPatch
    ):
        headers = auth_headers(owner_user)
        personal_id, meta_id = await _setup_decks(client, owner_user)

        await client.post(
            f"{BASE}/personal-decks/{personal_id}/versions",
            json={"content": "4 Goblin Guide"},
            headers=headers,
        )
        # Auto-stamped to v1 (the only version that exists yet).
        await client.post(
            f"{BASE}/matches",
            json=_match_payload(personal_id, meta_id),
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
            "app.api.tamiyo_scroll.personal_decks.render_session_report_pdf",
            _fake_render,
        )
        resp = await client.get(
            f"{BASE}/personal-decks/{personal_id}/report.pdf", headers=headers
        )

        assert resp.status_code == 200
        assert captured["colored_lines"] == [
            {"line": "4 Goblin Guide", "status": "neutral"}
        ]
