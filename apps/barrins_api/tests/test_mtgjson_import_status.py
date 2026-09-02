"""Tests for live MTGJSON import progress: `mj_import_runs` /
`GET /mtgjson/import/status` (`app/services/mtgjson/importer.py`'s
`_ImportRunTracker`, `app/api/general/mtgjson.py`).

Separate from `test_mtgjson.py` (which already covers the importer's core
upsert/idempotency/chunking behavior) to keep this file focused on the
progress-tracking mechanism itself: the tracker writes independently of
the main import transaction so a status poll can see counts advance
mid-run instead of nothing until the whole import finishes -- see the
module docstring in `importer.py`.
"""

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.mtgjson import Card, MTGJSONImportRun, MTGSet
from app.services.mtgjson import import_all_printings
from app.services.mtgjson.importer import _ImportRunTracker
from tests.identity_auth import FakeUser as User
from tests.identity_auth import auth_headers as _auth_headers

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mtgjson_sample.json"
_BASE = "/api/v1"

# Every test here either calls `import_all_printings` or drives
# `_ImportRunTracker` directly, both of which write through it -- see
# `mtgjson_tracker_uses_test_db`'s docstring in conftest.py.
pytestmark = pytest.mark.usefixtures("mtgjson_tracker_uses_test_db")


def _load_fixture() -> dict[str, Any]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


class FakeMTGJSONClient:
    """Streams the real, trimmed fixture instead of calling MTGJSON."""

    async def stream_sets(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        for set_code, set_data in _load_fixture()["data"].items():
            yield set_code, set_data


class _RaisingAfterFirstSetClient:
    """Yields one real set, then fails -- simulates a mid-stream error."""

    async def stream_sets(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        for set_code, set_data in _load_fixture()["data"].items():
            yield set_code, set_data
            raise RuntimeError("simulated failure mid-stream")


@pytest.fixture()
def admin_user() -> User:
    return User(
        email="admin@mtgjson-status.example.com",
        role="admin",
        username="mtgjson-status-admin",
    )


@pytest.fixture()
def plain_user() -> User:
    return User(
        email="user@mtgjson-status.example.com",
        role="user",
        username="mtgjson-status-user",
    )


class TestImportStatusGate:
    async def test_unauthenticated_gets_401(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/mtgjson/import/status")
        assert resp.status_code == 401

    async def test_non_admin_gets_403(self, client: AsyncClient, plain_user: User):
        resp = await client.get(
            f"{_BASE}/mtgjson/import/status", headers=_auth_headers(plain_user)
        )
        assert resp.status_code == 403

    async def test_no_run_yet_returns_404(self, client: AsyncClient, admin_user: User):
        resp = await client.get(
            f"{_BASE}/mtgjson/import/status", headers=_auth_headers(admin_user)
        )
        assert resp.status_code == 404


class TestSuccessfulImportStatus:
    async def test_status_reflects_a_finished_run(
        self, client: AsyncClient, db_session, admin_user: User
    ):
        await import_all_printings(db_session, FakeMTGJSONClient())

        resp = await client.get(
            f"{_BASE}/mtgjson/import/status", headers=_auth_headers(admin_user)
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "succeeded"
        assert body["sets_upserted"] == 2
        assert body["cards_upserted"] == 3
        assert body["finished_at"] is not None
        assert body["error_message"] is None


class TestFailedImportStatus:
    async def test_mid_stream_failure_marks_the_run_failed(self, db_session):
        with pytest.raises(RuntimeError, match="simulated failure mid-stream"):
            await import_all_printings(db_session, _RaisingAfterFirstSetClient())

        run = (
            await db_session.execute(
                select(MTGJSONImportRun).order_by(MTGJSONImportRun.started_at.desc())
            )
        ).scalar_one()
        assert run.status == "failed"
        assert run.error_message is not None
        assert "simulated failure mid-stream" in run.error_message

        sets_count = (
            await db_session.execute(select(MTGSet).limit(1))
        ).scalar_one_or_none()
        cards_count = (
            await db_session.execute(select(Card).limit(1))
        ).scalar_one_or_none()
        assert sets_count is None
        assert cards_count is None


class TestTrackerProgress:
    async def test_progress_updates_the_same_row_across_calls(self, db_session):
        tracker = _ImportRunTracker()
        await tracker.start()

        await tracker.progress(sets_upserted=2, cards_upserted=50)
        first_run = (await db_session.execute(select(MTGJSONImportRun))).scalar_one()
        assert first_run.status == "running"
        assert (first_run.sets_upserted, first_run.cards_upserted) == (2, 50)

        await tracker.progress(sets_upserted=5, cards_upserted=120)
        await db_session.refresh(first_run)
        assert (first_run.sets_upserted, first_run.cards_upserted) == (5, 120)

        await tracker.finish(sets_upserted=5, cards_upserted=120)
        await db_session.refresh(first_run)
        assert first_run.status == "succeeded"
        assert first_run.finished_at is not None


class TestStaleRunningRowSelfHeals:
    async def test_new_run_marks_a_leftover_running_row_failed(self, db_session):
        stale = MTGJSONImportRun(status="running")
        db_session.add(stale)
        await db_session.commit()

        tracker = _ImportRunTracker()
        await tracker.start()

        await db_session.refresh(stale)
        assert stale.status == "failed"
        assert stale.error_message == "Interrupted by a new import run."
        assert stale.finished_at is not None
