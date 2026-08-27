"""Persists one pushed Karn Tablets clustering run into `kt_*` (ADR-13).

A run's raw `cluster_id` is a run-local integer with no identity across
runs. This module gives each cluster a **stable** identity by matching it
against the `kt_archetypes` registry for the same `(format, window_kind)`,
in two passes over the as-yet-unclaimed archetypes:

1. **Commander identity.** In Duel Commander the representative sideboard
   is the commander zone; a cluster whose commander(s) exactly match an
   existing archetype's `commanders` is that archetype, regardless of
   99-card list drift.
2. **Mainboard similarity.** Otherwise (no commander, or a second
   distinct build of one commander), highest Jaccard overlap of the
   mainboard signature, accepted at `ARCHETYPE_MATCH_THRESHOLD` or above.

No match on either pass → a new archetype, auto-named from its commander
(`_archetype_name`).

Clusters are processed largest-first so the dominant deck of a window
claims its archetype before smaller, partially-overlapping ones — the
result is independent of the payload's archetype order. One transaction,
committed once at the end (mirrors
`app/services/scripture/ingester.py`). A re-push of the same
`(format, window_kind, window_label, generated_at)` is idempotent: the
run's `kt_run_archetypes` rows are deleted and rebuilt, exactly like the
Scripture ingester replaces a deck's card rows.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.karn import KTArchetype, KTClusteringRun, KTRunArchetype
from app.schemas.karn_ingest import KarnIngestRequest

#: Stamped on every run/archetype until the pipeline itself starts sending
#: a `format` (the frozen CLI contract has no such field today).
INGEST_DEFAULT_FORMAT = "Duel Commander"

#: Upper bound on how many card names go into an archetype signature —
#: a representative Duel Commander decklist is ~100 singletons, well under
#: this; the cap only guards pathological input.
ARCHETYPE_SIGNATURE_SIZE = 60

#: Minimum Jaccard overlap between two signatures to treat them as the
#: same archetype. Tuned against `tests/karn/test_ingest.py`.
ARCHETYPE_MATCH_THRESHOLD = 0.6

#: `kt_archetypes.name` is `String(120)`; leave headroom for a
#: `_dedupe_name` " #NN" suffix.
_NAME_MAX_LENGTH = 110

_BASIC_LANDS = frozenset(
    {
        "Plains",
        "Island",
        "Swamp",
        "Mountain",
        "Forest",
        "Wastes",
        "Snow-Covered Plains",
        "Snow-Covered Island",
        "Snow-Covered Swamp",
        "Snow-Covered Mountain",
        "Snow-Covered Forest",
        "Snow-Covered Wastes",
    }
)


@dataclass(frozen=True)
class KarnIngestResult:
    """Outcome of a single `ingest_run` call."""

    run_id: uuid.UUID
    archetypes_matched: int
    archetypes_created: int


def _signature(mainboard: dict[str, int]) -> list[str]:
    """The card-name fingerprint for matching: highest-quantity cards
    first (so a frequency-weighted representative list keeps its defining
    cards when capped), then stored sorted for a stable comparison set.
    """
    ranked = sorted(mainboard.items(), key=lambda kv: (-kv[1], kv[0]))
    return sorted(name for name, _ in ranked[:ARCHETYPE_SIGNATURE_SIZE])


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _commanders(representative_sideboard: dict[str, int]) -> list[str]:
    """The archetype's commander card name(s), sorted. In Duel Commander
    the representative sideboard *is* the commander zone; an empty result
    means the data carries no commander (a non-DC format, or a gap).
    """
    return sorted(representative_sideboard)


def _archetype_name(
    representative_mainboard: dict[str, int],
    representative_sideboard: dict[str, int],
) -> str:
    """A deterministic archetype label.

    In Duel Commander the commander(s) — carried in the representative
    *sideboard* — are the archetype identity, so name from there when it
    has anything. Fall back to the mainboard's top non-basic-land cards
    (a singleton-format decklist has almost everything at quantity 1, so
    this is effectively "first cards alphabetically" — a weak label, but
    only reached for formats/data without a commander). `"Unclassified"`
    if both are empty.
    """
    source = representative_sideboard or representative_mainboard
    ranked = sorted(
        ((n, q) for n, q in source.items() if n not in _BASIC_LANDS),
        key=lambda kv: (-kv[1], kv[0]),
    )
    picks = [name for name, _ in ranked[:3]]
    label = " / ".join(picks) if picks else "Unclassified"
    return label[:_NAME_MAX_LENGTH]


def _dedupe_name(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    suffix = 2
    while f"{base} #{suffix}" in taken:
        suffix += 1
    return f"{base} #{suffix}"


async def _upsert_run(
    session: AsyncSession, fmt: str, payload: KarnIngestRequest
) -> uuid.UUID:
    values: dict[str, object] = {
        "format": fmt,
        "window_kind": payload.window.kind,
        "window_label": payload.window.label,
        "generated_at": payload.generated_at,
        "window_date_from": payload.window.date_from,
        "window_date_to": payload.window.date_to,
        "algorithm": payload.algorithm,
        "total_decks": payload.total_decks,
        "pipeline_version": payload.pipeline_version,
    }
    stmt = pg_insert(KTClusteringRun).values(**values)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_kt_runs_window_generated",
        set_={
            "window_date_from": stmt.excluded.window_date_from,
            "window_date_to": stmt.excluded.window_date_to,
            "algorithm": stmt.excluded.algorithm,
            "total_decks": stmt.excluded.total_decks,
            "pipeline_version": stmt.excluded.pipeline_version,
        },
    ).returning(KTClusteringRun.id)
    return (await session.execute(stmt)).scalar_one()


async def ingest_run(
    session: AsyncSession, payload: KarnIngestRequest
) -> KarnIngestResult:
    """Persist one clustering run and match its clusters to stable archetypes.

    Idempotent on an exact re-push (`(format, window_kind, window_label,
    generated_at)`): the run row is updated in place and its
    `kt_run_archetypes` rows are rebuilt. A re-run of the same window with
    a later `generated_at` is a new run row — reads always return the
    latest per `(format, window_kind)`.
    """
    fmt = payload.format or INGEST_DEFAULT_FORMAT
    run_id = await _upsert_run(session, fmt, payload)
    await session.execute(delete(KTRunArchetype).where(KTRunArchetype.run_id == run_id))

    rows = (
        await session.execute(
            select(
                KTArchetype.id,
                KTArchetype.name,
                KTArchetype.commanders,
                KTArchetype.signature,
            ).where(
                KTArchetype.format == fmt,
                KTArchetype.window_kind == payload.window.kind,
            )
        )
    ).all()
    existing: list[tuple[uuid.UUID, tuple[str, ...], set[str]]] = [
        (row.id, tuple(row.commanders or []), set(row.signature or [])) for row in rows
    ]
    taken_names: set[str] = {row.name for row in rows}

    claimed: set[uuid.UUID] = set()
    matched = 0
    created = 0

    ordered = sorted(payload.archetypes, key=lambda a: (-a.deck_count, a.cluster_id))
    for arch in ordered:
        commanders = _commanders(arch.representative_sideboard)
        commander_key = tuple(commanders)
        signature = _signature(arch.representative_mainboard)
        sig_set = set(signature)

        target_id: uuid.UUID | None = None

        # 1. Commander identity — the decisive match for Duel Commander.
        if commander_key:
            target_id = next(
                (
                    archetype_id
                    for archetype_id, arch_commanders, _ in existing
                    if archetype_id not in claimed and arch_commanders == commander_key
                ),
                None,
            )

        # 2. Fall back to mainboard similarity (no commander, or no
        #    commander match — e.g. a second distinct build of one commander).
        if target_id is None:
            best_score = 0.0
            for archetype_id, _, archetype_sig in existing:
                if archetype_id in claimed:
                    continue
                score = _jaccard(sig_set, archetype_sig)
                if score > best_score:
                    best_score, target_id = score, archetype_id
            if best_score < ARCHETYPE_MATCH_THRESHOLD:
                target_id = None

        if target_id is not None:
            matched += 1
            claimed.add(target_id)
            await session.execute(
                update(KTArchetype)
                .where(KTArchetype.id == target_id)
                .values(signature=signature, last_seen_run_id=run_id)
            )
        else:
            created += 1
            target_id = uuid.uuid4()
            name = _dedupe_name(
                _archetype_name(
                    arch.representative_mainboard, arch.representative_sideboard
                ),
                taken_names,
            )
            taken_names.add(name)
            await session.execute(
                pg_insert(KTArchetype).values(
                    id=target_id,
                    format=fmt,
                    window_kind=payload.window.kind,
                    name=name,
                    commanders=commanders,
                    signature=signature,
                    first_seen_run_id=run_id,
                    last_seen_run_id=run_id,
                )
            )
            existing.append((target_id, commander_key, sig_set))
            claimed.add(target_id)

        await session.execute(
            pg_insert(KTRunArchetype).values(
                run_id=run_id,
                archetype_id=target_id,
                cluster_id=arch.cluster_id,
                deck_count=arch.deck_count,
                share=arch.share,
                representative_mainboard=arch.representative_mainboard,
                representative_sideboard=arch.representative_sideboard,
            )
        )

    await session.commit()
    return KarnIngestResult(
        run_id=run_id, archetypes_matched=matched, archetypes_created=created
    )
