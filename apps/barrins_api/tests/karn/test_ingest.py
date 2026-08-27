"""Tests for `POST /internal/karn/ingest` (ADR-13): auth gate, persistence,
idempotency, and stable cross-run archetype matching.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.config import settings
from app.models.karn import KTArchetype, KTClusteringRun, KTRunArchetype
from tests.karn.conftest import INGEST_URL, archetype, headers, payload


class TestIngestAuth:
    async def test_missing_token_is_401(self, client: AsyncClient):
        resp = await client.post(INGEST_URL, json=payload())
        assert resp.status_code == 401

    async def test_wrong_token_is_401(self, client: AsyncClient):
        resp = await client.post(
            INGEST_URL, json=payload(), headers={"X-Karn-Token": "nope"}
        )
        assert resp.status_code == 401

    async def test_unconfigured_token_is_503(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(settings.base, "karn_ingest_token", None)
        resp = await client.post(INGEST_URL, json=payload(), headers=headers())
        assert resp.status_code == 503


class TestIngestPersistence:
    async def test_persists_run_and_archetypes(self, client: AsyncClient, db_session):
        body = payload(
            archetypes=[
                archetype(1, 40, 60),
                archetype(2, 20, 60, swap=60, prefix="Beta"),
            ]
        )
        resp = await client.post(INGEST_URL, json=body, headers=headers())
        assert resp.status_code == 200
        out = resp.json()
        assert out["archetypes_created"] == 2
        assert out["archetypes_matched"] == 0

        run = (await db_session.execute(select(KTClusteringRun))).scalar_one()
        assert run.format == "Duel Commander"
        assert run.total_decks == 60
        assert str(run.id) == out["run_id"]

        run_rows = (
            (
                await db_session.execute(
                    select(KTRunArchetype).where(KTRunArchetype.run_id == run.id)
                )
            )
            .scalars()
            .all()
        )
        assert {r.cluster_id for r in run_rows} == {1, 2}
        assert sum(r.deck_count for r in run_rows) == 60

        archetype_count = (
            await db_session.execute(select(func.count()).select_from(KTArchetype))
        ).scalar_one()
        assert archetype_count == 2

    async def test_explicit_format_is_stored(self, client: AsyncClient, db_session):
        resp = await client.post(
            INGEST_URL, json=payload(fmt="Legacy"), headers=headers()
        )
        assert resp.status_code == 200
        run = (await db_session.execute(select(KTClusteringRun))).scalar_one()
        assert run.format == "Legacy"

    async def test_exact_replay_is_idempotent(self, client: AsyncClient, db_session):
        body = payload(
            generated_at=datetime(2026, 8, 27, 4, 0, tzinfo=UTC),
            archetypes=[archetype(1, 30, 50), archetype(2, 20, 50, swap=60)],
        )
        first = await client.post(INGEST_URL, json=body, headers=headers())
        second = await client.post(INGEST_URL, json=body, headers=headers())
        assert first.status_code == second.status_code == 200
        assert first.json()["run_id"] == second.json()["run_id"]

        runs = (
            await db_session.execute(select(func.count()).select_from(KTClusteringRun))
        ).scalar_one()
        run_archetypes = (
            await db_session.execute(select(func.count()).select_from(KTRunArchetype))
        ).scalar_one()
        archetypes = (
            await db_session.execute(select(func.count()).select_from(KTArchetype))
        ).scalar_one()
        assert (runs, run_archetypes, archetypes) == (1, 2, 2)


class TestArchetypeMatching:
    async def test_mainboard_jaccard_reuses_archetype_when_no_commander(
        self, client: AsyncClient, db_session
    ):
        """Pass-2 fallback: with no commander in the data, a later run's
        cluster still matches on mainboard overlap above the threshold.
        """
        base = datetime(2026, 8, 20, 4, 0, tzinfo=UTC)
        first = await client.post(
            INGEST_URL,
            json=payload(
                generated_at=base,
                label="rolling_30d:2026-08-20",
                archetypes=[archetype(1, 30, 30, commander="")],
            ),
            headers=headers(),
        )
        # Next day: 4 of 60 mainboard cards different (Jaccard ~0.87).
        second = await client.post(
            INGEST_URL,
            json=payload(
                generated_at=base + timedelta(days=1),
                label="rolling_30d:2026-08-21",
                archetypes=[archetype(7, 33, 33, swap=4, commander="")],
            ),
            headers=headers(),
        )
        assert second.json()["archetypes_matched"] == 1
        assert second.json()["archetypes_created"] == 0

        archetype_ids = set(
            (await db_session.execute(select(KTRunArchetype.archetype_id)))
            .scalars()
            .all()
        )
        assert len(archetype_ids) == 1  # both runs point at the same archetype
        assert first.json()["run_id"] != second.json()["run_id"]

    async def test_different_commander_creates_new_archetype(
        self, client: AsyncClient, db_session
    ):
        base = datetime(2026, 8, 20, 4, 0, tzinfo=UTC)
        await client.post(
            INGEST_URL,
            json=payload(
                generated_at=base,
                archetypes=[archetype(1, 30, 30, commander="Atraxa, Grand Unifier")],
            ),
            headers=headers(),
        )
        resp = await client.post(
            INGEST_URL,
            json=payload(
                generated_at=base + timedelta(days=1),
                label="rolling_30d:2026-08-21",
                archetypes=[
                    archetype(
                        2,
                        30,
                        30,
                        swap=60,
                        prefix="Zeta",
                        commander="Emry, Lurker of the Loch",
                    )
                ],
            ),
            headers=headers(),
        )
        assert resp.json()["archetypes_matched"] == 0
        assert resp.json()["archetypes_created"] == 1
        total = (
            await db_session.execute(select(func.count()).select_from(KTArchetype))
        ).scalar_one()
        assert total == 2

    async def test_same_commander_matches_despite_full_mainboard_drift(
        self, client: AsyncClient, db_session
    ):
        """The commander is the identity: a later run whose representative
        mainboard shares nothing with the first still maps to the same
        archetype as long as the commander matches.
        """
        base = datetime(2026, 8, 20, 4, 0, tzinfo=UTC)
        first = await client.post(
            INGEST_URL,
            json=payload(
                generated_at=base,
                archetypes=[archetype(1, 30, 30, commander="Aragorn, King of Gondor")],
            ),
            headers=headers(),
        )
        second = await client.post(
            INGEST_URL,
            json=payload(
                generated_at=base + timedelta(days=1),
                label="rolling_30d:2026-08-21",
                archetypes=[
                    archetype(
                        9,
                        33,
                        33,
                        swap=60,
                        prefix="Totally Different",
                        commander="Aragorn, King of Gondor",
                    )
                ],
            ),
            headers=headers(),
        )
        assert second.json() == {
            "run_id": second.json()["run_id"],
            "archetypes_matched": 1,
            "archetypes_created": 0,
        }
        assert first.json()["run_id"] != second.json()["run_id"]
        ids = set(
            (await db_session.execute(select(KTRunArchetype.archetype_id)))
            .scalars()
            .all()
        )
        assert len(ids) == 1

    @pytest.mark.parametrize("reverse", [False, True])
    async def test_matching_is_order_independent_and_one_to_one(
        self, client: AsyncClient, db_session, reverse: bool
    ):
        """Two clusters in one run both resemble a known archetype; the
        larger claims it, the smaller gets a fresh identity -- regardless
        of the order they appear in the payload.
        """
        base = datetime(2026, 8, 20, 4, 0, tzinfo=UTC)
        await client.post(
            INGEST_URL,
            json=payload(generated_at=base, archetypes=[archetype(1, 30, 30)]),
            headers=headers(),
        )
        big = archetype(5, 40, 50, swap=2)  # ~0.93 overlap
        small = archetype(6, 10, 50, swap=5)  # ~0.85 overlap
        clusters = [small, big] if reverse else [big, small]
        resp = await client.post(
            INGEST_URL,
            json=payload(
                generated_at=base + timedelta(days=1),
                label="rolling_30d:2026-08-21",
                archetypes=clusters,
            ),
            headers=headers(),
        )
        assert resp.json() == {
            "run_id": resp.json()["run_id"],
            "archetypes_matched": 1,
            "archetypes_created": 1,
        }

        latest_run_id = resp.json()["run_id"]
        rows = (
            (
                await db_session.execute(
                    select(KTRunArchetype).where(KTRunArchetype.run_id == latest_run_id)
                )
            )
            .scalars()
            .all()
        )
        by_cluster = {r.cluster_id: r.archetype_id for r in rows}
        assert by_cluster[5] != by_cluster[6]  # never collapsed together

        original = (
            await db_session.execute(
                select(KTRunArchetype.archetype_id).where(
                    KTRunArchetype.cluster_id == 1
                )
            )
        ).scalar_one()
        assert by_cluster[5] == original  # the big cluster kept the identity


class TestArchetypeNaming:
    async def test_identical_new_clusters_get_deduped_names(
        self, client: AsyncClient, db_session
    ):
        """Two disjoint-but-identical clusters in one run generate the
        same auto-name and must be stored under distinct " #N" names.
        """
        twin = archetype(1, 20, 40, swap=60, prefix="Twin")
        other = {**archetype(2, 20, 40, swap=60, prefix="Twin"), "cluster_id": 2}
        resp = await client.post(
            INGEST_URL,
            json=payload(archetypes=[twin, other]),
            headers=headers(),
        )
        assert resp.json()["archetypes_created"] == 2
        names = sorted(
            (await db_session.execute(select(KTArchetype.name))).scalars().all()
        )
        assert names[0] != names[1]
        assert names[1].endswith(" #2")

    async def test_name_comes_from_the_commander_not_the_mainboard(
        self, client: AsyncClient, db_session
    ):
        """In Duel Commander the commander (representative sideboard) is
        the archetype identity -- a singleton mainboard would otherwise
        name every archetype after its alphabetically-first staples.
        """
        resp = await client.post(
            INGEST_URL,
            json=payload(
                archetypes=[
                    archetype(1, 40, 60, commander="Atraxa, Grand Unifier"),
                    archetype(
                        2,
                        20,
                        60,
                        swap=60,
                        prefix="X",
                        commander="Winota, Joiner of Forces",
                    ),
                ]
            ),
            headers=headers(),
        )
        assert resp.status_code == 200
        names = set(
            (await db_session.execute(select(KTArchetype.name))).scalars().all()
        )
        assert names == {"Atraxa, Grand Unifier", "Winota, Joiner of Forces"}

    async def test_empty_representative_mainboard_is_accepted(
        self, client: AsyncClient, db_session
    ):
        body = payload(
            archetypes=[
                {
                    "cluster_id": 1,
                    "deck_count": 5,
                    "share": 1.0,
                    "representative_mainboard": {},
                    "representative_sideboard": {},
                }
            ]
        )
        resp = await client.post(INGEST_URL, json=body, headers=headers())
        assert resp.status_code == 200
        name = (await db_session.execute(select(KTArchetype.name))).scalar_one()
        assert name == "Unclassified"
