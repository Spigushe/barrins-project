"""Routes /metagame, /archetypes, /trends -- public archetype-clustering
views over the `kt_*` data `apps/karn_tablets` pushes in (ADR-13, T4
iteration 2). Public, no auth (ADR-10), same `Envelope`/`Meta` wrapper as
the rest of this BFF.

Query params: `window` (`rolling_30d` | `banlist_period`, required) and
`format` (optional, defaults to `"Duel Commander"` -- the only populated
value in v1). `/metagame` and `/archetypes` take `at` (a `window.label`)
to step to a past window; `/archetypes` also takes `limit` + opaque
`cursor`.
"""

import base64
import binascii
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app.database.session import DatabaseSession
from app.models.karn import KTWindowKind
from app.schemas.responses_tolaria_news import (
    ArchetypeDetailPage,
    ArchetypeTrend,
    ArchetypeTrendPoint,
    CardRef,
    Envelope,
    Meta,
    MetagameArchetype,
    MetagameArchetypeDetail,
    MetagameSnapshot,
    Page,
    RepresentativeCard,
    WindowOut,
)
from app.services.karn import read
from app.services.karn.read import (
    ArchetypeShareRow,
    CardRefRow,
    RepresentativeCardRow,
    WindowRef,
)

router = APIRouter()

_DEFAULT_FORMAT = "Duel Commander"
#: `/archetypes` default page size. A run holds ~10 archetypes today, so
#: this is headroom, not a limit that bites yet.
_ARCHETYPES_PAGE_LIMIT = 20
#: `/trends` small-multiples grid: two rows of five.
_TRENDS_LIMIT = 10

WindowParam = Annotated[Literal["rolling_30d", "banlist_period"], Query()]
# Wire name stays `format` (the frontend contract); the Python parameter is
# `fmt` to avoid shadowing the builtin.
FormatParam = Annotated[str, Query(alias="format")]
LimitParam = Annotated[int, Query(ge=1, le=100)]
CursorParam = Annotated[str | None, Query()]
#: A `window.label` from a prior response; selects that window's run.
AtParam = Annotated[str | None, Query()]


def _window_out(window: WindowRef) -> WindowOut:
    return WindowOut(
        kind=window.kind.value,
        label=window.label,
        date_from=window.date_from,
        date_to=window.date_to,
    )


def _window_out_opt(window: WindowRef | None) -> WindowOut | None:
    return _window_out(window) if window is not None else None


def _meta(synced_at: datetime | None) -> Meta:
    return Meta(generated_at=datetime.now(UTC), source_synced_at=synced_at)


def _card_ref(ref: CardRefRow) -> CardRef:
    return CardRef(name=ref.name, scryfall_id=ref.scryfall_id)


def _basic_archetype(row: ArchetypeShareRow) -> MetagameArchetype:
    return MetagameArchetype(
        id=str(row.id),
        name=row.name,
        commanders=[_card_ref(ref) for ref in row.commanders],
        deck_count=row.deck_count,
        deck_share=row.share,
        deck_share_delta=row.share_delta,
        momentum=row.momentum,
    )


def _representative(cards: list[RepresentativeCardRow]) -> list[RepresentativeCard]:
    return [
        RepresentativeCard(
            name=card.name,
            qty=card.qty,
            scryfall_id=card.scryfall_id,
            is_land=card.is_land,
            is_signature=card.is_signature,
        )
        for card in cards
    ]


def _decode_cursor(cursor: str | None) -> int:
    """Opaque `cursor` -> row offset. A malformed cursor is a client
    error, not a silent reset."""
    if cursor is None:
        return 0
    try:
        offset = int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc
    if offset < 0:
        raise HTTPException(status_code=400, detail="Invalid cursor")
    return offset


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


async def _snapshot(
    session: DatabaseSession,
    window: str,
    fmt: str,
    at: str | None,
    *,
    with_card_details: bool,
) -> read.MetagameSnapshotData:
    try:
        return await read.metagame_snapshot(
            session,
            fmt,
            KTWindowKind(window),
            at_label=at,
            with_card_details=with_card_details,
        )
    except read.WindowNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No run for that window") from exc


@router.get("/metagame", response_model=Envelope[MetagameSnapshot])
async def get_metagame(
    session: DatabaseSession,
    window: WindowParam,
    fmt: FormatParam = _DEFAULT_FORMAT,
    at: AtParam = None,
) -> Envelope[MetagameSnapshot]:
    snapshot = await _snapshot(session, window, fmt, at, with_card_details=False)
    return Envelope(
        data=MetagameSnapshot(
            format=snapshot.fmt,
            window=_window_out(snapshot.window),
            previous_window=_window_out_opt(snapshot.previous_window),
            next_window=_window_out_opt(snapshot.next_window),
            archetypes=[_basic_archetype(row) for row in snapshot.archetypes],
        ),
        meta=_meta(snapshot.synced_at),
    )


@router.get("/archetypes", response_model=Envelope[ArchetypeDetailPage])
async def get_archetypes(
    session: DatabaseSession,
    window: WindowParam,
    fmt: FormatParam = _DEFAULT_FORMAT,
    at: AtParam = None,
    limit: LimitParam = _ARCHETYPES_PAGE_LIMIT,
    cursor: CursorParam = None,
) -> Envelope[ArchetypeDetailPage]:
    offset = _decode_cursor(cursor)
    snapshot = await _snapshot(session, window, fmt, at, with_card_details=True)
    page_rows = snapshot.archetypes[offset : offset + limit]
    has_more = offset + limit < len(snapshot.archetypes)
    return Envelope(
        data=ArchetypeDetailPage(
            format=snapshot.fmt,
            window=_window_out(snapshot.window),
            previous_window=_window_out_opt(snapshot.previous_window),
            next_window=_window_out_opt(snapshot.next_window),
            archetypes=[
                MetagameArchetypeDetail(
                    id=str(row.id),
                    name=row.name,
                    commanders=[_card_ref(ref) for ref in row.commanders],
                    deck_count=row.deck_count,
                    deck_share=row.share,
                    deck_share_delta=row.share_delta,
                    momentum=row.momentum,
                    representative_mainboard=_representative(row.representative_cards),
                )
                for row in page_rows
            ],
        ),
        meta=_meta(snapshot.synced_at),
        page=Page(
            next_cursor=_encode_cursor(offset + limit) if has_more else None,
            limit=limit,
        ),
    )


@router.get("/trends", response_model=Envelope[list[ArchetypeTrend]])
async def get_trends(
    session: DatabaseSession,
    window: WindowParam,
    fmt: FormatParam = _DEFAULT_FORMAT,
) -> Envelope[list[ArchetypeTrend]]:
    kind = KTWindowKind(window)
    rows = await read.archetype_trends(session, fmt, kind, limit=_TRENDS_LIMIT)
    latest = await read.latest_run(session, fmt, kind)
    return Envelope(
        data=[
            ArchetypeTrend(
                archetype_id=str(row.archetype_id),
                archetype_name=row.archetype_name,
                commanders=[_card_ref(ref) for ref in row.commanders],
                points=[
                    ArchetypeTrendPoint(
                        window=_window_out(point.window),
                        deck_share=point.deck_share,
                    )
                    for point in row.points
                ],
            )
            for row in rows
        ],
        meta=_meta(latest.generated_at if latest is not None else None),
    )
