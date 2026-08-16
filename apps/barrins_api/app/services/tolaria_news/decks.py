"""Deck detail queries backing the Tolaria News BFF.

Joins `bs_deck_cards` (T2, raw `card_name` strings) against `mj_cards`
(S8's MTGJSON import) to surface real card data -- `cmc`/`type_line`/
`scryfall_id`/`color_identity` -- instead of bare strings. Reuses
`app.services.scripture.card_resolver`'s name normalization (the same
logic T3's ingestion route already validates scraped names against) so
this doesn't re-implement accent/Unicode folding a second time.

Commander derivation: confirmed against real fixtures (both MTGO and
MTGTop8) that for Duel Commander tournaments, the `sideboard` board of
`bs_deck_cards` holds exactly the commander(s) -- 1 card solo, 2 for a
partner pair -- since Commander has no traditional sideboard zone.
"""

import uuid
from collections.abc import Sequence
from datetime import date as date_type
from datetime import timedelta

from dc_calendar.windowing import (
    all_time_periods,
    banlist_period_window,
    rolling_30d_window,
)
from sqlalchemy import and_, exists, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.mtgjson import Card
from app.models.scripture import BSDeck, BSDeckBoard, BSDeckCard, BSSource, BSTournament
from app.schemas.responses_tolaria_news import (
    CommanderRef,
    CommanderTrendPoint,
    CommanderTrendSeries,
    CommanderTrendsResponse,
    DeckCardOut,
    DeckCardTypeGroup,
    DeckDetail,
    DeckListItem,
    Page,
    TrendWindowMode,
    WindowOut,
)
from app.services.decklist_sort import decklist_sort_key, group_by_category
from app.services.scripture.card_resolver import resolve_card_name
from app.services.tolaria_news.pagination import decode_cursor, encode_cursor

_TOP_TRENDING_COMMANDERS = 10
_BUCKET_DAYS = 7

#: Mirrors `barrins_scripture.schemas.formats.Formats.DUEL_COMMANDER`
#: (the exact string that source stores into `bs_tournaments.format`).
#: Not imported cross-app on purpose -- `barrins_api` doesn't depend on
#: `barrins_scripture`'s package, only on the string it writes.
DUEL_COMMANDER_FORMAT = "Duel Commander"

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50


async def resolved_cards(
    session: AsyncSession, card_rows: Sequence[BSDeckCard]
) -> dict[uuid.UUID, Card | None]:
    """`{bs_deck_cards.id: matching mj_cards row or None}` for every row.

    One resolver pass (per-name, cached) + one batched `mj_cards` query,
    not N+1 queries per card line. When a name resolves to a printing
    that exists more than once (multiple sets), an arbitrary matching
    printing is used -- `cmc`/`type_line`/`color_identity` are the same
    across printings, `scryfall_id` isn't (picks *a* printing's image,
    not necessarily the newest); acceptable for v1, not guaranteed
    "preferred art".

    Exported (not module-private) -- `app.services.tolaria_news.tournaments`
    reuses this for the tournament deck list's commander column, rather
    than re-implementing the same resolve-then-batch-join.
    """
    canonical_by_card_id: dict[uuid.UUID, str] = {}
    for card in card_rows:
        canonical = await resolve_card_name(session, card.card_name)
        if canonical is not None:
            canonical_by_card_id[card.id] = canonical

    names = set(canonical_by_card_id.values())
    if not names:
        return dict.fromkeys(c.id for c in card_rows)

    matches = (
        (
            await session.execute(
                select(Card).where(or_(Card.name.in_(names), Card.face_name.in_(names)))
            )
        )
        .scalars()
        .all()
    )
    card_by_name: dict[str, Card] = {}
    for match in matches:
        card_by_name.setdefault(match.name, match)
        if match.face_name:
            card_by_name.setdefault(match.face_name, match)

    return {
        card.id: card_by_name.get(canonical_by_card_id.get(card.id, ""))
        for card in card_rows
    }


def commander_ref(name: str, match: Card | None) -> CommanderRef:
    """Builds one `CommanderRef` from a raw sideboard card name and its
    resolved `mj_cards` match (`None` if resolution failed) -- shared by
    `get_deck`, `list_trending_commanders`, and (cross-module)
    `app.services.tolaria_news.tournaments.list_decks`'s commander column,
    so this fallback shape is defined once."""
    return CommanderRef(
        name=match.name if match is not None else name,
        scryfall_id=match.scryfall_id if match is not None else None,
        color_identity=match.color_identity if match is not None else [],
        mana_cost=match.mana_cost if match is not None else None,
        text=match.text if match is not None else None,
        keywords=match.keywords if match is not None else [],
    )


def _as_deck_card_out(card: BSDeckCard, resolved: Card | None) -> DeckCardOut:
    return DeckCardOut(
        name=resolved.name if resolved is not None else card.card_name,
        qty=card.count,
        cmc=resolved.mana_value if resolved is not None else None,
        type_line=resolved.type_line if resolved is not None else None,
        scryfall_id=resolved.scryfall_id if resolved is not None else None,
        mana_cost=resolved.mana_cost if resolved is not None else None,
        text=resolved.text if resolved is not None else None,
        keywords=resolved.keywords if resolved is not None else [],
    )


async def get_deck(session: AsyncSession, deck_id: uuid.UUID) -> DeckDetail | None:
    deck = await session.get(BSDeck, deck_id)
    if deck is None:
        return None
    tournament = await session.get(BSTournament, deck.tournament_id)
    assert (
        tournament is not None
    )  # FK guarantees this (bs_decks.tournament_id NOT NULL)

    card_rows = (
        (await session.execute(select(BSDeckCard).where(BSDeckCard.deck_id == deck_id)))
        .scalars()
        .all()
    )
    resolved = await resolved_cards(session, card_rows)

    sorted_mainboard = sorted(
        (
            _as_deck_card_out(c, resolved[c.id])
            for c in card_rows
            if c.board == BSDeckBoard.mainboard
        ),
        key=lambda c: decklist_sort_key(c.type_line, c.cmc, c.name),
    )
    mainboard = [
        DeckCardTypeGroup(category=category, count=len(group), cards=group)
        for category, group in group_by_category(
            sorted_mainboard, lambda c: c.type_line
        )
    ]

    commanders: list[CommanderRef] = []
    if tournament.format == DUEL_COMMANDER_FORMAT:
        for c in card_rows:
            if c.board != BSDeckBoard.sideboard:
                continue
            commanders.append(commander_ref(c.card_name, resolved[c.id]))

    return DeckDetail(
        id=deck.id,
        tournament_id=deck.tournament_id,
        date=deck.date,
        player=deck.player,
        result=deck.result,
        anchor_uri=deck.anchor_uri,
        notes=deck.notes,
        commanders=commanders,
        mainboard=mainboard,
    )


def _sideboard_card_exists(*extra: ColumnElement[bool]) -> ColumnElement[bool]:
    """`EXISTS` probe over the current deck's sideboard rows (the
    commander slot for Duel Commander -- see the module docstring's
    "Commander derivation" note), correlated against the outer `BSDeck`.
    Shared shape for the `commander` and `colors` filters below."""
    return exists(
        select(BSDeckCard.id).where(
            BSDeckCard.deck_id == BSDeck.id,
            BSDeckCard.board == BSDeckBoard.sideboard,
            *extra,
        )
    )


def _sideboard_card_joined_to_mj_cards(
    *extra: ColumnElement[bool],
) -> ColumnElement[bool]:
    """Same as `_sideboard_card_exists`, joined to `mj_cards` for a
    `Card.color_identity` predicate. Safe as a plain equality join (no
    `card_resolver` call needed here): `bs_deck_cards.card_name` is
    already canonicalized against `mj_cards.name`/`face_name` at ingest
    time (`app/services/scripture/ingester.py::_replace_deck_cards` runs
    every card, mainboard and sideboard, through `resolve_card_name`
    before storing it -- a name that doesn't resolve is skipped, never
    stored). So a stored `card_name` is guaranteed to equal some
    `Card.name`/`Card.face_name` exactly, unless `mj_cards` was
    re-imported and renamed that exact card since -- an accepted, rare
    edge case (that row just won't match, same "acceptable for v1"
    posture as `get_deck`'s own resolution)."""
    return exists(
        select(BSDeckCard.id)
        .join(
            Card,
            or_(
                Card.name == BSDeckCard.card_name,
                Card.face_name == BSDeckCard.card_name,
            ),
        )
        .where(
            BSDeckCard.deck_id == BSDeck.id,
            BSDeckCard.board == BSDeckBoard.sideboard,
            *extra,
        )
    )


async def list_decks(
    session: AsyncSession,
    *,
    player: str | None,
    source: BSSource | None,
    commander: str | None,
    colors: frozenset[str] | None,
    date_from: date_type | None,
    date_to: date_type | None,
    cursor: str | None,
    limit: int,
) -> tuple[list[DeckListItem], Page]:
    """Global, cross-tournament decklist index (`GET /decks`).

    Restricted to Duel Commander tournaments server-side -- this app's
    sole scope (`apps/tolaria_news/README.md`), same reasoning as
    `TournamentListPage` fixing `format` client-side rather than exposing
    it as a filter.

    `colors` (color identity) is matched exactly -- the union of every
    sideboard card's `color_identity` must equal `colors` precisely, not
    "contains" or "any of". Expressed as two conditions, both plain SQL
    (see `_sideboard_card_joined_to_mj_cards`'s docstring for why no
    Python-side resolution is needed):

    - no sideboard card's identity has a color outside `colors` (this
      alone guarantees the *union* has no extra color too, since a union
      of subsets of `colors` is itself a subset of `colors`);
    - every color in `colors` is covered by at least one sideboard card
      (one `EXISTS` per selected color rather than an aggregate --
      `colors` is at most 5 elements, and this correctly captures a
      partner pair's *combined* identity without needing to aggregate
      across their up-to-2 rows).
    """
    limit = min(limit, _MAX_LIMIT) if limit else _DEFAULT_LIMIT
    stmt = (
        select(BSDeck, BSTournament.name, BSTournament.source)
        .join(BSTournament, BSDeck.tournament_id == BSTournament.id)
        .where(BSTournament.format == DUEL_COMMANDER_FORMAT)
        .order_by(BSDeck.date.desc(), BSDeck.id.desc())
    )
    if player is not None:
        stmt = stmt.where(BSDeck.player.ilike(f"%{player}%"))
    if source is not None:
        stmt = stmt.where(BSTournament.source == source)
    if commander is not None:
        stmt = stmt.where(_sideboard_card_exists(BSDeckCard.card_name == commander))
    if colors:
        color_list = list(colors)
        stmt = stmt.where(
            ~_sideboard_card_joined_to_mj_cards(
                ~Card.color_identity.contained_by(color_list)
            ),
            and_(
                *(
                    _sideboard_card_joined_to_mj_cards(
                        Card.color_identity.contains([color])
                    )
                    for color in color_list
                )
            ),
        )
    if date_from is not None:
        stmt = stmt.where(BSDeck.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(BSDeck.date <= date_to)
    if cursor is not None:
        cursor_date, cursor_id = decode_cursor(cursor)
        stmt = stmt.where(
            tuple_(BSDeck.date, BSDeck.id)
            < (date_type.fromisoformat(cursor_date), uuid.UUID(cursor_id))
        )
    rows = (await session.execute(stmt.limit(limit + 1))).all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        encode_cursor(rows[-1][0].date.isoformat(), str(rows[-1][0].id))
        if has_more and rows
        else None
    )
    return (
        [
            DeckListItem(
                id=deck.id,
                tournament_id=deck.tournament_id,
                date=deck.date,
                player=deck.player,
                result=deck.result,
                anchor_uri=deck.anchor_uri,
                tournament_name=tournament_name,
                tournament_source=tournament_source,
            )
            for deck, tournament_name, tournament_source in rows
        ],
        Page(next_cursor=next_cursor, limit=limit),
    )


async def list_commanders(session: AsyncSession) -> list[str]:
    """Distinct commander names across all Duel Commander tournaments --
    backs the `/decklists` commander dropdown. Already-canonical values
    (see `_sideboard_card_joined_to_mj_cards`'s docstring): no
    accent-variant near-duplicates, and every returned name is directly
    usable as-is for `list_decks`'s `commander` filter. Small (bounded by
    the legal commander pool, not deck count) and deliberately not
    cursor-paginated -- a dropdown doesn't need it."""
    stmt = (
        select(BSDeckCard.card_name)
        .distinct()
        .join(BSDeck, BSDeckCard.deck_id == BSDeck.id)
        .join(BSTournament, BSDeck.tournament_id == BSTournament.id)
        .where(
            BSDeckCard.board == BSDeckBoard.sideboard,
            BSTournament.format == DUEL_COMMANDER_FORMAT,
        )
        .order_by(BSDeckCard.card_name.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


def _weekly_buckets(
    date_from: date_type, date_to: date_type
) -> list[tuple[date_type, date_type]]:
    """Non-overlapping `_BUCKET_DAYS`-wide buckets spanning
    `[date_from, date_to]`, oldest first. The final bucket may be shorter
    than a full week if the span isn't an exact multiple of one -- the
    same "shared intervals, trailing partial one allowed" shape a rolling
    30-day window naturally produces (31 inclusive days -> 4 full weeks
    plus a 3-day tail)."""
    buckets: list[tuple[date_type, date_type]] = []
    cursor = date_from
    while cursor <= date_to:
        bucket_end = min(cursor + timedelta(days=_BUCKET_DAYS - 1), date_to)
        buckets.append((cursor, bucket_end))
        cursor = bucket_end + timedelta(days=1)
    return buckets


async def _resolve_trend_window(
    session: AsyncSession, *, mode: TrendWindowMode, period_offset: int
) -> tuple[WindowOut, list[tuple[date_type, date_type]]]:
    """Resolves the outer date range for `mode` (walking `period_offset`
    banlist periods into the past when `mode` is `banlist_period`) and the
    equal-length sub-buckets the trend line plots one point per.

    `all_time`'s buckets are the historical banlist periods themselves
    (`dc_calendar.all_time_periods`), not weekly slices -- weekly buckets
    across an open-ended, potentially years-long span would produce an
    unreadable number of points; one point per banlist era is the natural
    granularity "all time" implies.
    """
    today = date_type.today()

    if mode == "rolling_30d":
        window = rolling_30d_window(today)
        return (
            WindowOut(
                kind=mode,
                label=window.label,
                date_from=window.date_from,
                date_to=window.date_to,
            ),
            _weekly_buckets(window.date_from, window.date_to),
        )

    if mode == "banlist_period":
        window = banlist_period_window(today)
        for _ in range(period_offset):
            window = banlist_period_window(window.date_from - timedelta(days=1))
        return (
            WindowOut(
                kind=mode,
                label=window.label,
                date_from=window.date_from,
                date_to=window.date_to,
            ),
            _weekly_buckets(window.date_from, window.date_to),
        )

    # all_time
    earliest = (
        await session.execute(
            select(func.min(BSTournament.date)).where(
                BSTournament.format == DUEL_COMMANDER_FORMAT
            )
        )
    ).scalar_one()
    if earliest is None:
        return (
            WindowOut(
                kind=mode, label="all_time:empty", date_from=today, date_to=today
            ),
            [],
        )
    periods = all_time_periods(earliest, today)
    return (
        WindowOut(
            kind=mode,
            label=f"all_time:{earliest.isoformat()}_{today.isoformat()}",
            date_from=earliest,
            date_to=today,
        ),
        [(p.date_from, p.date_to) for p in periods],
    )


async def list_trending_commanders(
    session: AsyncSession,
    *,
    mode: TrendWindowMode,
    period_offset: int,
) -> CommanderTrendsResponse:
    """Top `_TOP_TRENDING_COMMANDERS` commanders (solo or partner pairs) by
    deck count in `mode`'s window, each with a per-bucket play-count trend.

    Partner pairs are grouped by the sorted tuple of their resolved
    commander names, so a pair groups identically regardless of which
    card `bs_deck_cards` happened to store first.
    """
    window_out, buckets = await _resolve_trend_window(
        session, mode=mode, period_offset=period_offset
    )
    if not buckets:
        return CommanderTrendsResponse(window=window_out, series=[])
    date_from, date_to = buckets[0][0], buckets[-1][1]

    rows = (
        await session.execute(
            select(BSDeckCard.card_name, BSDeck.id, BSDeck.date)
            .join(BSDeck, BSDeckCard.deck_id == BSDeck.id)
            .join(BSTournament, BSDeck.tournament_id == BSTournament.id)
            .where(
                BSDeckCard.board == BSDeckBoard.sideboard,
                BSTournament.format == DUEL_COMMANDER_FORMAT,
                BSDeck.date >= date_from,
                BSDeck.date <= date_to,
            )
        )
    ).all()
    if not rows:
        return CommanderTrendsResponse(window=window_out, series=[])

    canonical_by_name: dict[str, str] = {}
    for name in {row[0] for row in rows}:
        canonical = await resolve_card_name(session, name)
        if canonical is not None:
            canonical_by_name[name] = canonical

    names_by_deck: dict[uuid.UUID, set[str]] = {}
    date_by_deck: dict[uuid.UUID, date_type] = {}
    for card_name, deck_id, deck_date in rows:
        canonical = canonical_by_name.get(card_name)
        if canonical is None:
            continue
        names_by_deck.setdefault(deck_id, set()).add(canonical)
        date_by_deck[deck_id] = deck_date

    total_counts: dict[tuple[str, ...], int] = {}
    bucket_counts: dict[tuple[str, ...], list[int]] = {}
    for deck_id, names in names_by_deck.items():
        if not names:
            continue
        key = tuple(sorted(names))
        deck_date = date_by_deck[deck_id]
        total_counts[key] = total_counts.get(key, 0) + 1
        counts = bucket_counts.setdefault(key, [0] * len(buckets))
        for i, (bucket_from, bucket_to) in enumerate(buckets):
            if bucket_from <= deck_date <= bucket_to:
                counts[i] += 1
                break

    top_keys = sorted(total_counts, key=lambda k: total_counts[k], reverse=True)[
        :_TOP_TRENDING_COMMANDERS
    ]

    all_names = {name for key in top_keys for name in key}
    matches = (
        (
            await session.execute(
                select(Card).where(
                    or_(Card.name.in_(all_names), Card.face_name.in_(all_names))
                )
            )
        )
        .scalars()
        .all()
    )
    card_by_name: dict[str, Card] = {}
    for match in matches:
        card_by_name.setdefault(match.name, match)
        if match.face_name:
            card_by_name.setdefault(match.face_name, match)

    series = [
        CommanderTrendSeries(
            commanders=[commander_ref(name, card_by_name.get(name)) for name in key],
            total_deck_count=total_counts[key],
            points=[
                CommanderTrendPoint(
                    date_from=bucket_from,
                    date_to=bucket_to,
                    deck_count=bucket_counts[key][i] or None,
                )
                for i, (bucket_from, bucket_to) in enumerate(buckets)
            ],
        )
        for key in top_keys
    ]
    return CommanderTrendsResponse(window=window_out, series=series)
