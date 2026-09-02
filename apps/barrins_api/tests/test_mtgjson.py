"""Tests for the S8 MTGJSON reference-data pipeline.

Covers both layers: the HTTP routes (`app/api/general/mtgjson.py`) and
the underlying importer (`app/services/mtgjson/importer.py`). Import
tests run against `tests/fixtures/mtgjson_sample.json` (real, trimmed
MTGJSON data — see `tests/fixtures/README.md`), via a fake client
substituted for the real HTTP download.
"""

import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import func, select, update

from app.config import settings
from app.main import app
from app.models.mtgjson import Card, MTGSet
from app.services.mtgjson import get_mtgjson_client, import_all_printings
from tests.identity_auth import FakeUser as User
from tests.identity_auth import auth_headers as _auth_headers

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_FIXTURE_PATH = _FIXTURES_DIR / "mtgjson_sample.json"
_BASE = "/api/v1"

# Every test here calls `import_all_printings`, which now also writes
# import-progress rows through `_ImportRunTracker` -- see
# `mtgjson_tracker_uses_test_db`'s docstring in conftest.py.
pytestmark = pytest.mark.usefixtures("mtgjson_tracker_uses_test_db")


def _load_fixture() -> dict[str, Any]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


class FakeMTGJSONClient:
    """Streams the real, trimmed fixture instead of calling MTGJSON."""

    async def stream_sets(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        for set_code, set_data in _load_fixture()["data"].items():
            yield set_code, set_data


@pytest.fixture()
def admin_user() -> User:
    return User(
        email="admin@mtgjson.example.com", role="admin", username="mtgjson-admin"
    )


@pytest.fixture()
def plain_user() -> User:
    return User(email="user@mtgjson.example.com", role="user", username="mtgjson-user")


class TestImportGate:
    async def test_unauthenticated_gets_401(self, client: AsyncClient):
        resp = await client.post(f"{_BASE}/mtgjson/import")
        assert resp.status_code == 401

    async def test_non_admin_gets_403(self, client: AsyncClient, plain_user: User):
        resp = await client.post(
            f"{_BASE}/mtgjson/import", headers=_auth_headers(plain_user)
        )
        assert resp.status_code == 403


_MTGJSON_TOKEN = "test-mtgjson-import-token"  # noqa: S105


class TestImportServiceToken:
    """The daily-refresh systemd timer authenticates via
    X-MTGJSON-Import-Token instead of an admin JWT -- see
    app/dependencies/service_auth.py::verify_mtgjson_or_admin. A human
    admin's JWT must keep working unchanged regardless of whether this
    token is configured (covered by TestImportGate/TestImportRoute above,
    which never set mtgjson_import_token).
    """

    @pytest.fixture(autouse=True)
    def _configured_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            settings.base, "mtgjson_import_token", SecretStr(_MTGJSON_TOKEN)
        )

    async def test_valid_service_token_allows_import(self, client: AsyncClient):
        app.dependency_overrides[get_mtgjson_client] = lambda: FakeMTGJSONClient()
        resp = await client.post(
            f"{_BASE}/mtgjson/import",
            headers={"X-MTGJSON-Import-Token": _MTGJSON_TOKEN},
        )
        assert resp.status_code == 200

    async def test_wrong_service_token_and_no_bearer_gets_401(
        self, client: AsyncClient
    ):
        resp = await client.post(
            f"{_BASE}/mtgjson/import",
            headers={"X-MTGJSON-Import-Token": "wrong-token"},
        )
        assert resp.status_code == 401

    async def test_admin_jwt_still_works_when_token_is_configured(
        self, client: AsyncClient, admin_user: User
    ):
        app.dependency_overrides[get_mtgjson_client] = lambda: FakeMTGJSONClient()
        resp = await client.post(
            f"{_BASE}/mtgjson/import", headers=_auth_headers(admin_user)
        )
        assert resp.status_code == 200


class TestImportRoute:
    async def test_import_upserts_sets_and_cards(
        self, client: AsyncClient, admin_user: User
    ):
        app.dependency_overrides[get_mtgjson_client] = lambda: FakeMTGJSONClient()
        resp = await client.post(
            f"{_BASE}/mtgjson/import", headers=_auth_headers(admin_user)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["sets_upserted"] == 2
        assert body["cards_upserted"] == 3


class TestImportChunking:
    async def test_import_spans_multiple_upsert_chunks(
        self, db_session, monkeypatch: pytest.MonkeyPatch
    ):
        """Forces the 3-card fixture across 2 chunks (chunk size 2) to
        prove no rows are dropped or duplicated at a chunk boundary, and
        that idempotency (see `TestImportIdempotency`) still holds when
        a re-import's chunk boundaries land on the same rows.
        """
        monkeypatch.setattr("app.services.mtgjson.importer._UPSERT_CHUNK_SIZE", 2)
        client_ = FakeMTGJSONClient()

        first = await import_all_printings(db_session, client_)
        second = await import_all_printings(db_session, client_)

        assert first.sets_upserted == second.sets_upserted == 2
        assert first.cards_upserted == second.cards_upserted == 3
        cards_after = (
            await db_session.execute(select(func.count()).select_from(Card))
        ).scalar_one()
        assert cards_after == 3


class TestImportIdempotency:
    async def test_reimport_does_not_duplicate_rows(self, db_session):
        client_ = FakeMTGJSONClient()

        first = await import_all_printings(db_session, client_)
        sets_after_first = (
            await db_session.execute(select(func.count()).select_from(MTGSet))
        ).scalar_one()
        cards_after_first = (
            await db_session.execute(select(func.count()).select_from(Card))
        ).scalar_one()

        second = await import_all_printings(db_session, client_)
        sets_after_second = (
            await db_session.execute(select(func.count()).select_from(MTGSet))
        ).scalar_one()
        cards_after_second = (
            await db_session.execute(select(func.count()).select_from(Card))
        ).scalar_one()

        assert first.sets_upserted == second.sets_upserted == 2
        assert first.cards_upserted == second.cards_upserted == 3
        assert sets_after_first == sets_after_second == 2
        assert cards_after_first == cards_after_second == 3


class TestImportBumpsUpdatedAt:
    """Regression test: the chunked upsert (`_upsert_sets`/`_upsert_cards`)
    uses a raw Core `INSERT ... ON CONFLICT DO UPDATE`, which bypasses the
    ORM unit-of-work path entirely -- so the model's `onupdate=func.now()`
    (`app/models/mtgjson.py`) never fired on a re-import's conflict branch,
    leaving `updated_at` (and `GET /mtgjson/status`'s `last_imported_at`)
    frozen at each row's original insert time forever. Both upsert helpers
    now set `updated_at` explicitly.
    """

    async def test_reimport_bumps_set_and_card_updated_at(self, db_session):
        """Doesn't compare timestamps across the two imports directly --
        Postgres's `now()` is transaction-start time, and the test fixture
        keeps the whole test inside one outer transaction, so two calls a
        few milliseconds apart can (and did, before this was rewritten)
        resolve to the exact same instant, making a naive `>` assertion
        pass or fail independent of whether the fix actually works.
        Instead: force a stale sentinel onto already-imported rows, then
        confirm a re-import moves them off of it -- proving the DO UPDATE
        branch actually touches `updated_at` at all.
        """
        client_ = FakeMTGJSONClient()
        await import_all_printings(db_session, client_)

        stale = datetime(2000, 1, 1, tzinfo=UTC)
        await db_session.execute(
            update(MTGSet).where(MTGSet.code == "P30A").values(updated_at=stale)
        )
        await db_session.execute(
            update(Card).where(Card.set_code == "P30A").values(updated_at=stale)
        )
        await db_session.commit()

        await import_all_printings(db_session, client_)

        mtg_set = (
            await db_session.execute(select(MTGSet).where(MTGSet.code == "P30A"))
        ).scalar_one()
        card = (
            await db_session.execute(select(Card).where(Card.set_code == "P30A"))
        ).scalar_one()

        assert mtg_set.updated_at != stale
        assert card.updated_at != stale


class TestMultiFaceRoundTrip:
    """Emeria's Call // Emeria, Shattered Skyclave (ZNR) -- a real MDFC."""

    async def test_front_and_back_face_types_stored_independently(self, db_session):
        await import_all_printings(db_session, FakeMTGJSONClient())

        result = await db_session.execute(
            select(Card).where(Card.set_code == "ZNR").order_by(Card.side)
        )
        front, back = result.scalars().all()

        assert front.face_name == "Emeria's Call"
        assert front.side == "a"
        assert front.type_line == "Sorcery"
        assert front.other_face_ids == [str(back.id)]

        assert back.face_name == "Emeria, Shattered Skyclave"
        assert back.side == "b"
        assert back.type_line == "Land"
        assert back.other_face_ids == [str(front.id)]


class TestPublicRoutesReachability:
    async def test_status_reachable_without_auth(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/mtgjson/status")
        assert resp.status_code == 200

    async def test_list_sets_reachable_without_auth(
        self, client: AsyncClient, db_session
    ):
        await import_all_printings(db_session, FakeMTGJSONClient())
        resp = await client.get(f"{_BASE}/sets/")
        assert resp.status_code == 200
        codes = {s["code"] for s in resp.json()}
        assert {"P30A", "ZNR"} <= codes

    async def test_get_set_reachable_without_auth(
        self, client: AsyncClient, db_session
    ):
        await import_all_printings(db_session, FakeMTGJSONClient())
        resp = await client.get(f"{_BASE}/sets/P30A")
        assert resp.status_code == 200
        assert resp.json()["name"] == "30th Anniversary Play Promos"

    async def test_get_set_unknown_code_404s(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/sets/ZZZZ")
        assert resp.status_code == 404

    async def test_set_cards_reachable_without_auth(
        self, client: AsyncClient, db_session
    ):
        await import_all_printings(db_session, FakeMTGJSONClient())
        resp = await client.get(f"{_BASE}/sets/P30A/cards")
        assert resp.status_code == 200
        assert [c["name"] for c in resp.json()] == ["Serra Angel"]

    async def test_get_card_by_id_reachable_without_auth(
        self, client: AsyncClient, db_session
    ):
        await import_all_printings(db_session, FakeMTGJSONClient())
        result = await db_session.execute(select(Card).where(Card.set_code == "P30A"))
        serra = result.scalar_one()
        resp = await client.get(f"{_BASE}/cards/{serra.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Serra Angel"

    async def test_get_card_by_name_reachable_without_auth(
        self, client: AsyncClient, db_session
    ):
        await import_all_printings(db_session, FakeMTGJSONClient())
        resp = await client.get(f"{_BASE}/cards/by-name/Serra Angel")
        assert resp.status_code == 200
        assert resp.json()["rarity"] == "rare"

    async def test_get_card_unknown_id_404s(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/cards/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Scryfall multi-face layout fixtures -> found via GET /cards/by-name/{name}
# ---------------------------------------------------------------------------
#
# Real Scryfall card payloads, one per multi-face layout (adventure,
# transform, modal_dfc, split, prepare -- see tests/fixtures/README.md).
# MTGJSON uses the exact same combined "Front // Back" string as its own
# per-face `name` (verified against the real ZNR fixture above), so these
# double as realistic MTGJSON card names without needing a live MTGJSON
# fetch for each layout.
#
# Manually checking these by name against a real import failed: every
# multi-face name contains a literal " // ", and FastAPI's default `str`
# path converter on `/cards/by-name/{name}` stops matching at the first
# "/", 404ing on all five. Fixed in `app/api/general/mtgjson.py` by
# switching to the `:path` converter. These tests import a minimal
# MTGJSON-shaped set+card pair derived from each fixture and confirm the
# route now finds it -- kept as a permanent regression guard.
_SCRYFALL_LAYOUT_FIXTURES: tuple[str, ...] = (
    "scryfall_aventure_example.json",
    "scryfall_transform_example.json",
    "scryfall_mdfc_example.json",
    "scryfall_room_example.json",
    "scryfall_prepared_example.json",
)


def _load_scryfall_fixture(filename: str) -> dict[str, Any]:
    return json.loads((_FIXTURES_DIR / filename).read_text(encoding="utf-8"))


def _mtgjson_payload_from_scryfall_card(
    scryfall_card: dict[str, Any],
) -> dict[str, Any]:
    """Builds a minimal MTGJSON `AllPrintings.json`-shaped payload for one
    multi-face Scryfall card, one row per face, linked via `otherFaceIds`
    -- same shape as the real ZNR fixture above.
    """
    set_code = scryfall_card["set"].upper()
    faces = scryfall_card["card_faces"]
    face_uuids = [
        str(uuid.uuid5(uuid.NAMESPACE_URL, f"{scryfall_card['id']}/{side}"))
        for side in range(len(faces))
    ]
    cards = [
        {
            "uuid": face_uuids[side],
            "name": scryfall_card["name"],
            "faceName": face["name"],
            "side": "ab"[side],
            "otherFaceIds": [face_uuids[(side + 1) % len(face_uuids)]],
            "type": face.get("type_line", scryfall_card["type_line"]),
            "manaCost": face.get("mana_cost") or None,
            "colors": face.get("colors", scryfall_card.get("colors", [])),
            "colorIdentity": scryfall_card.get("color_identity", []),
            "rarity": scryfall_card["rarity"],
            "number": scryfall_card["collector_number"],
            "layout": scryfall_card["layout"],
        }
        for side, face in enumerate(faces)
    ]
    return {
        "meta": {"date": "2026-08-07", "version": "test"},
        "data": {
            set_code: {
                "name": scryfall_card["set_name"],
                "releaseDate": scryfall_card["released_at"],
                "type": scryfall_card["set_type"],
                "baseSetSize": 1,
                "totalSetSize": 1,
                "keyruneCode": set_code,
                "cards": cards,
            }
        },
    }


class _FakeScryfallDerivedClient:
    """Streams a payload built from a single Scryfall fixture card."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    async def stream_sets(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        for set_code, set_data in self._payload["data"].items():
            yield set_code, set_data


class TestScryfallMultiFaceNamesFoundByName:
    @pytest.mark.parametrize("fixture_name", _SCRYFALL_LAYOUT_FIXTURES)
    async def test_layout_card_found_by_full_name(
        self, client: AsyncClient, db_session, fixture_name: str
    ):
        scryfall_card = _load_scryfall_fixture(fixture_name)
        payload = _mtgjson_payload_from_scryfall_card(scryfall_card)
        await import_all_printings(db_session, _FakeScryfallDerivedClient(payload))

        resp = await client.get(f"{_BASE}/cards/by-name/{scryfall_card['name']}")

        assert resp.status_code == 200
        assert resp.json()["name"] == scryfall_card["name"]


# ---------------------------------------------------------------------------
# GET /cards/search-by-name/{name} -- lookup by full name, face A, or face B
# ---------------------------------------------------------------------------
#
# A card must be findable by its full combined name or by an individual
# face's name, but only when that face is independently castable (see
# `CASTABLE_BOTH_FACES_LAYOUTS` in app/models/mtgjson.py): both faces for
# Adventure/modal DFC/split, front face only for Transform/Prepare/normal.
# A non-castable back face is never a search key at all -- searching
# "Ancestral Recall" must return only the real classic card, never
# "Emeritus of Ideation // Ancestral Recall" (whose back face happens to
# share that name but can't be cast on its own).
_BACK_FACE_SEARCHABLE_LAYOUTS: frozenset[str] = frozenset(
    {
        "adventure",
        "modal_dfc",
        "split",
    }
)


def _mtgjson_payload_for_normal_card(
    name: str, set_code: str, set_name: str, released_at: str
) -> dict[str, Any]:
    """Minimal MTGJSON payload for one single-faced ("normal" layout) card."""
    return {
        "meta": {"date": "2026-08-07", "version": "test"},
        "data": {
            set_code: {
                "name": set_name,
                "releaseDate": released_at,
                "type": "expansion",
                "baseSetSize": 1,
                "totalSetSize": 1,
                "keyruneCode": set_code,
                "cards": [
                    {
                        "uuid": str(
                            uuid.uuid5(uuid.NAMESPACE_URL, f"{set_code}/{name}")
                        ),
                        "name": name,
                        "type": "Instant",
                        "rarity": "special",
                        "number": "1",
                        "layout": "normal",
                    }
                ],
            }
        },
    }


class TestSearchCardsByName:
    @pytest.mark.parametrize("fixture_name", _SCRYFALL_LAYOUT_FIXTURES)
    async def test_found_by_full_name_and_front_face(
        self, client: AsyncClient, db_session, fixture_name: str
    ):
        scryfall_card = _load_scryfall_fixture(fixture_name)
        payload = _mtgjson_payload_from_scryfall_card(scryfall_card)
        await import_all_printings(db_session, _FakeScryfallDerivedClient(payload))

        face_a_name = scryfall_card["card_faces"][0]["name"]

        for query in (scryfall_card["name"], face_a_name):
            resp = await client.get(f"{_BASE}/cards/search-by-name/{query}")
            assert resp.status_code == 200, query
            names = [c["name"] for c in resp.json()]
            assert names == [scryfall_card["name"]], query

    @pytest.mark.parametrize("fixture_name", _SCRYFALL_LAYOUT_FIXTURES)
    async def test_back_face_searchable_only_when_independently_castable(
        self, client: AsyncClient, db_session, fixture_name: str
    ):
        scryfall_card = _load_scryfall_fixture(fixture_name)
        payload = _mtgjson_payload_from_scryfall_card(scryfall_card)
        await import_all_printings(db_session, _FakeScryfallDerivedClient(payload))

        face_b_name = scryfall_card["card_faces"][1]["name"]
        resp = await client.get(f"{_BASE}/cards/search-by-name/{face_b_name}")

        assert resp.status_code == 200
        if scryfall_card["layout"] in _BACK_FACE_SEARCHABLE_LAYOUTS:
            assert [c["name"] for c in resp.json()] == [scryfall_card["name"]]
        else:
            assert resp.json() == []

    async def test_name_collision_only_the_castable_card_matches(
        self, client: AsyncClient, db_session
    ):
        """ "Ancestral Recall" is both a real classic card and the back face
        of "Emeritus of Ideation // Ancestral Recall" -- but Prepare only
        lets you cast the front face, so that back face is never a search
        key. Searching "Ancestral Recall" must return only the real card.
        """
        emeritus = _load_scryfall_fixture("scryfall_prepared_example.json")
        await import_all_printings(
            db_session,
            _FakeScryfallDerivedClient(_mtgjson_payload_from_scryfall_card(emeritus)),
        )
        await import_all_printings(
            db_session,
            _FakeScryfallDerivedClient(
                _mtgjson_payload_for_normal_card(
                    "Ancestral Recall", "LEA", "Limited Edition Alpha", "1993-08-05"
                )
            ),
        )

        resp = await client.get(f"{_BASE}/cards/search-by-name/Ancestral Recall")

        assert resp.status_code == 200
        assert [c["name"] for c in resp.json()] == ["Ancestral Recall"]

    async def test_unknown_name_returns_empty_list(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/cards/search-by-name/Not A Real Card")
        assert resp.status_code == 200
        assert resp.json() == []
