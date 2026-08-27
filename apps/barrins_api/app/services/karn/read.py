"""Read layer over `kt_*` — shared by the public Tolaria News BFF routes
and the S6 admin dashboard route (Constitution §4.2: one implementation,
two callers, so the two surfaces can never disagree — an ADR-13
consequence).

Every entry point is scoped by `(format, window_kind)` and returns the
**latest** run for that pair (greatest `generated_at`). An unknown
`format` (anything but `"Duel Commander"` today) or a pair with no runs
yet returns an empty snapshot with the current calendar window, never an
error — matching how the pipeline treats an empty window as a valid
outcome.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Literal

from dc_calendar.windowing import banlist_period_window, rolling_30d_window
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.karn import KTArchetype, KTClusteringRun, KTRunArchetype, KTWindowKind
from app.models.mtgjson import Card
from app.services.decklist_sort import categorize

ArchetypeMomentum = Literal["rising", "falling", "stable", "new"]

#: "rising"/"falling" require `deck_share` to move by more than this
#: fraction of its *previous* value; inside the band an archetype counts
#: as "stable". Relative (not an absolute percentage-point band) so small
#: and large archetypes are judged proportionally. Backend-owned domain
#: rule (Constitution 4.1/4.2) -- the frontend renders the label, it does
#: not compute it.
_MOMENTUM_RELATIVE_BAND = 0.10

#: A land is dropped from an archetype's "signature cards" once it shows
#: up in at least this fraction of the latest run's archetypes -- at that
#: point it is a field-wide staple, not archetype-defining. A land unique
#: to a single archetype is always kept regardless of this. Provisional
#: (T6 follow-up) and backend-owned (Constitution 4.1/4.2).
_FIELD_LAND_PREVALENCE = 0.33


@dataclass(frozen=True)
class WindowRef:
    kind: KTWindowKind
    label: str
    date_from: date
    date_to: date


@dataclass(frozen=True)
class CardRefRow:
    name: str
    scryfall_id: str | None


@dataclass(frozen=True)
class RepresentativeCardRow:
    name: str
    qty: int
    scryfall_id: str | None
    is_land: bool
    #: `False` only for a land at or above `_FIELD_LAND_PREVALENCE` across
    #: the run's archetypes; always `True` for non-lands and for a land
    #: unique to one archetype.
    is_signature: bool


@dataclass(frozen=True)
class ArchetypeShareRow:
    id: uuid.UUID
    name: str
    deck_count: int
    share: float
    representative_mainboard: dict[str, int]
    #: The archetype's commander card name(s) with resolved Scryfall ids
    #: (for image hovers). Always populated.
    commanders: list[CardRefRow] = field(default_factory=list)
    #: The representative mainboard as ordered rows (largest qty first)
    #: with per-card Scryfall id / land / signature flags. Only populated
    #: when `metagame_snapshot` is called with `with_card_details=True`
    #: (the `/archetypes` route); empty otherwise.
    representative_cards: list[RepresentativeCardRow] = field(default_factory=list)
    #: `share` (this run) minus `share` (previous run) for the same
    #: archetype identity; `None` when there is no previous run or the
    #: archetype is absent from it.
    share_delta: float | None = None
    momentum: ArchetypeMomentum = "stable"


@dataclass(frozen=True)
class MetagameSnapshotData:
    fmt: str
    window: WindowRef
    total_decks: int
    #: `generated_at` of the run these numbers come from; `None` when
    #: there is no run yet.
    synced_at: datetime | None
    archetypes: list[ArchetypeShareRow]
    #: The adjacent windows of the same kind (by period start), for
    #: prev/next navigation. `None` at either end / when there is no run.
    previous_window: WindowRef | None = None
    next_window: WindowRef | None = None


@dataclass(frozen=True)
class TrendPointRow:
    window: WindowRef
    deck_share: float | None


@dataclass(frozen=True)
class ArchetypeTrendRow:
    archetype_id: uuid.UUID
    archetype_name: str
    commanders: list[CardRefRow]
    points: list[TrendPointRow]


def _current_window(window_kind: KTWindowKind) -> WindowRef:
    today = datetime.now(UTC).date()
    resolved = (
        rolling_30d_window(today)
        if window_kind is KTWindowKind.rolling_30d
        else banlist_period_window(today)
    )
    return WindowRef(
        kind=window_kind,
        label=resolved.label,
        date_from=resolved.date_from,
        date_to=resolved.date_to,
    )


def _window_of(run: KTClusteringRun) -> WindowRef:
    return WindowRef(
        kind=run.window_kind,
        label=run.window_label,
        date_from=run.window_date_from,
        date_to=run.window_date_to,
    )


async def latest_run(
    session: AsyncSession, fmt: str, window_kind: KTWindowKind
) -> KTClusteringRun | None:
    """The most recent clustering run for `(fmt, window_kind)`, or `None`."""
    return (
        await session.execute(
            select(KTClusteringRun)
            .where(
                KTClusteringRun.format == fmt,
                KTClusteringRun.window_kind == window_kind,
            )
            .order_by(KTClusteringRun.generated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


def _classify_momentum(
    current: float, previous: float | None, *, has_previous_run: bool
) -> tuple[float | None, ArchetypeMomentum]:
    """`(share_delta, momentum)` for one archetype -- see
    `ArchetypeMomentum` for the bucketing rule."""
    if not has_previous_run:
        return None, "stable"
    if previous is None:
        return None, "new"
    delta = current - previous
    if abs(delta) <= _MOMENTUM_RELATIVE_BAND * previous:
        return delta, "stable"
    return delta, "rising" if delta > 0 else "falling"


async def _run_windows(
    session: AsyncSession, fmt: str, window_kind: KTWindowKind
) -> list[tuple[WindowRef, uuid.UUID]]:
    """Every distinct window for `(fmt, window_kind)`, oldest first (by
    period start), each paired with the id of its most recent run. This is
    the sequence the `/metagame` + `/archetypes` prev/next navigation
    steps through."""
    runs = (
        (
            await session.execute(
                select(KTClusteringRun)
                .where(
                    KTClusteringRun.format == fmt,
                    KTClusteringRun.window_kind == window_kind,
                )
                .order_by(
                    KTClusteringRun.window_date_from, KTClusteringRun.generated_at
                )
            )
        )
        .scalars()
        .all()
    )
    # Ordered by (window_date_from, generated_at) asc, so for each label the
    # last row seen is its most recent run.
    latest_by_label: dict[str, tuple[WindowRef, uuid.UUID]] = {}
    for run in runs:
        latest_by_label[run.window_label] = (_window_of(run), run.id)
    return sorted(latest_by_label.values(), key=lambda pair: pair[0].date_from)


@dataclass(frozen=True)
class _CardFact:
    scryfall_id: str | None = None
    is_land: bool = False
    #: A `Basic` supertype land ("Plains", "Snow-Covered Island", ...).
    #: Never archetype-defining, so never a "signature card" whatever its
    #: prevalence.
    is_basic_land: bool = False


_NO_FACT = _CardFact()


async def _card_facts(session: AsyncSession, names: set[str]) -> dict[str, _CardFact]:
    """`{name: _CardFact}` for the `names` that resolve in `mj_cards`.
    Matches on either `name` or `face_name` (representative lists store
    whichever form the scraped list used, already canonicalized at
    Scripture ingest). Names with no match are absent (the caller falls
    back to `_NO_FACT`)."""
    if not names:
        return {}
    rows = (
        await session.execute(
            select(
                Card.name,
                Card.face_name,
                Card.scryfall_id,
                Card.type_line,
                Card.supertypes,
            ).where(or_(Card.name.in_(names), Card.face_name.in_(names)))
        )
    ).all()
    facts: dict[str, _CardFact] = {}
    for name, face_name, scryfall_id, type_line, supertypes in rows:
        is_land = categorize(type_line) == "land"
        fact = _CardFact(
            scryfall_id=scryfall_id,
            is_land=is_land,
            is_basic_land=is_land and "Basic" in (supertypes or []),
        )
        if name in names:
            facts.setdefault(name, fact)
        if face_name is not None and face_name in names:
            facts.setdefault(face_name, fact)
    return facts


def _commander_names(value: object) -> list[str]:
    """`KTArchetype.commanders` is stored as a JSON list of card names."""
    if isinstance(value, list):
        return [str(name) for name in value]
    return []


def _signature_check(
    total_archetypes: int, land_prevalence: dict[str, int]
) -> Callable[[str, _CardFact], bool]:
    """Build the `(name, fact) -> is_signature` predicate for one run.

    Non-lands are always signature. A basic land never is. Any other land
    is kept only while it is unique to one archetype or stays below
    `_FIELD_LAND_PREVALENCE` of the run's archetypes.
    """

    def is_signature(name: str, fact: _CardFact) -> bool:
        if not fact.is_land:
            return True
        if fact.is_basic_land:
            return False
        count = land_prevalence.get(name, 0)
        if count <= 1:
            return True
        return count / total_archetypes < _FIELD_LAND_PREVALENCE

    return is_signature


class WindowNotFoundError(LookupError):
    """`at_label` was passed to `metagame_snapshot` but no run of that
    `(fmt, window_kind)` has that `window_label`."""


async def metagame_snapshot(
    session: AsyncSession,
    fmt: str,
    window_kind: KTWindowKind,
    *,
    at_label: str | None = None,
    with_card_details: bool = False,
) -> MetagameSnapshotData:
    """The archetype-share distribution of one run for `(fmt,
    window_kind)`, largest archetype first, each row carrying its
    commanders (with Scryfall ids) and its `momentum` versus the
    *preceding* window of the same kind.

    `at_label` selects that window's latest run; `None` (default) is the
    most recent window. An `at_label` with no run raises
    `WindowNotFoundError`.

    `with_card_details=True` additionally resolves the whole
    representative mainboard into ordered rows with Scryfall id / land /
    signature flags (one extra `mj_cards` query) -- only the `/archetypes`
    route needs it.
    """
    windows = await _run_windows(session, fmt, window_kind)
    if not windows:
        return MetagameSnapshotData(
            fmt=fmt,
            window=_current_window(window_kind),
            total_decks=0,
            synced_at=None,
            archetypes=[],
        )

    if at_label is None:
        index = len(windows) - 1
    else:
        index = next(
            (i for i, (win, _) in enumerate(windows) if win.label == at_label), None
        )
        if index is None:
            raise WindowNotFoundError(at_label)

    target_window, run_id = windows[index]
    previous = windows[index - 1] if index > 0 else None
    following = windows[index + 1] if index + 1 < len(windows) else None
    run = await session.get(KTClusteringRun, run_id)
    if run is None:  # pragma: no cover - windows just told us it exists
        raise WindowNotFoundError(at_label or target_window.label)

    rows = (
        await session.execute(
            select(KTRunArchetype, KTArchetype.name, KTArchetype.commanders)
            .join(KTArchetype, KTRunArchetype.archetype_id == KTArchetype.id)
            .where(KTRunArchetype.run_id == run.id)
            .order_by(KTRunArchetype.deck_count.desc(), KTArchetype.name)
        )
    ).all()

    previous_shares: dict[uuid.UUID, float] = {}
    if previous is not None:
        previous_rows = await session.execute(
            select(KTRunArchetype.archetype_id, KTRunArchetype.share).where(
                KTRunArchetype.run_id == previous[1]
            )
        )
        for archetype_id, share in previous_rows.all():
            previous_shares[archetype_id] = share

    names_to_resolve: set[str] = set()
    for run_archetype, _, commanders in rows:
        names_to_resolve.update(_commander_names(commanders))
        if with_card_details:
            names_to_resolve.update(run_archetype.representative_mainboard or {})
    facts = await _card_facts(session, names_to_resolve)

    land_prevalence: dict[str, int] = {}
    if with_card_details:
        for run_archetype, _, _ in rows:
            for card_name in run_archetype.representative_mainboard or {}:
                if facts.get(card_name, _NO_FACT).is_land:
                    land_prevalence[card_name] = land_prevalence.get(card_name, 0) + 1
    is_signature = _signature_check(len(rows), land_prevalence)

    archetypes = []
    for run_archetype, name, commanders in rows:
        mainboard = dict(run_archetype.representative_mainboard or {})
        commander_refs = [
            CardRefRow(name=cmd, scryfall_id=facts.get(cmd, _NO_FACT).scryfall_id)
            for cmd in _commander_names(commanders)
        ]
        rep_cards: list[RepresentativeCardRow] = []
        if with_card_details:
            for card_name, qty in sorted(
                mainboard.items(), key=lambda kv: (-kv[1], kv[0])
            ):
                fact = facts.get(card_name, _NO_FACT)
                rep_cards.append(
                    RepresentativeCardRow(
                        name=card_name,
                        qty=qty,
                        scryfall_id=fact.scryfall_id,
                        is_land=fact.is_land,
                        is_signature=is_signature(card_name, fact),
                    )
                )
        share_delta, momentum = _classify_momentum(
            run_archetype.share,
            previous_shares.get(run_archetype.archetype_id),
            has_previous_run=previous is not None,
        )  # `previous` here is the preceding window, not "an earlier run"
        archetypes.append(
            ArchetypeShareRow(
                id=run_archetype.archetype_id,
                name=name,
                deck_count=run_archetype.deck_count,
                share=run_archetype.share,
                representative_mainboard=mainboard,
                commanders=commander_refs,
                representative_cards=rep_cards,
                share_delta=share_delta,
                momentum=momentum,
            )
        )
    return MetagameSnapshotData(
        fmt=fmt,
        window=target_window,
        total_decks=run.total_decks,
        synced_at=run.generated_at,
        archetypes=archetypes,
        previous_window=previous[0] if previous is not None else None,
        next_window=following[0] if following is not None else None,
    )


async def archetype_trends(
    session: AsyncSession,
    fmt: str,
    window_kind: KTWindowKind,
    limit: int = 10,
    runs: int = 12,
) -> list[ArchetypeTrendRow]:
    """For the top-`limit` archetypes of the latest run, their share
    across the last `runs` runs of `(fmt, window_kind)` (chronological;
    `deck_share` is `None` for a run in which the archetype had no
    cluster).
    """
    recent = list(
        reversed(
            (
                await session.execute(
                    select(KTClusteringRun)
                    .where(
                        KTClusteringRun.format == fmt,
                        KTClusteringRun.window_kind == window_kind,
                    )
                    .order_by(KTClusteringRun.generated_at.desc())
                    .limit(runs)
                )
            )
            .scalars()
            .all()
        )
    )
    if not recent:
        return []

    latest = recent[-1]
    top = (
        await session.execute(
            select(
                KTRunArchetype.archetype_id, KTArchetype.name, KTArchetype.commanders
            )
            .join(KTArchetype, KTRunArchetype.archetype_id == KTArchetype.id)
            .where(KTRunArchetype.run_id == latest.id)
            .order_by(KTRunArchetype.deck_count.desc(), KTArchetype.name)
            .limit(limit)
        )
    ).all()
    if not top:
        return []

    commander_facts = await _card_facts(
        session,
        {name for _, _, commanders in top for name in _commander_names(commanders)},
    )

    run_ids = [run.id for run in recent]
    archetype_ids = [archetype_id for archetype_id, _, _ in top]
    shares = {
        (row.run_id, row.archetype_id): row.share
        for row in (
            await session.execute(
                select(
                    KTRunArchetype.run_id,
                    KTRunArchetype.archetype_id,
                    KTRunArchetype.share,
                ).where(
                    KTRunArchetype.run_id.in_(run_ids),
                    KTRunArchetype.archetype_id.in_(archetype_ids),
                )
            )
        ).all()
    }

    windows = [_window_of(run) for run in recent]
    return [
        ArchetypeTrendRow(
            archetype_id=archetype_id,
            archetype_name=name,
            commanders=[
                CardRefRow(
                    name=cmd, scryfall_id=commander_facts.get(cmd, _NO_FACT).scryfall_id
                )
                for cmd in _commander_names(commanders)
            ],
            points=[
                TrendPointRow(
                    window=window,
                    deck_share=shares.get((run.id, archetype_id)),
                )
                for run, window in zip(recent, windows, strict=True)
            ],
        )
        for archetype_id, name, commanders in top
    ]
