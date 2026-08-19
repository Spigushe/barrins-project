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
from typing import Literal

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
    StapleRow,
    StaplesResponse,
    TrendWindowMode,
    WindowOut,
)
from app.services.decklist_sort import categorize, decklist_sort_key, group_by_category
from app.services.scripture.card_resolver import resolve_card_name
from app.services.tolaria_news.pagination import decode_cursor, encode_cursor

_TOP_TRENDING_COMMANDERS = 10
_BUCKET_DAYS = 7

#: Staples rows are capped to one deck's worth -- a long window's full
#: mainboard pool can run into hundreds of unique names once 1-of tech
#: cards are included; 60 keeps the table to what's actually "staple"
#: without an unbounded response.
_TOP_STAPLES = 60

#: A card only counts as a "staple" if played in at least this fraction of
#: the pooled decks -- below this it's just a played card, not a defining
#: trend of the metagame. Applied on top of `_TOP_STAPLES`'s cap. Real
#: pooled data (real dev-DB spot check, 2026-08-16) tops out well under
#: the 75% this was originally set to -- 65% is a floor real windows can
#: actually clear. Exposed as `list_staples`/the route's default
#: `min_percentage` rather than hardcoded, so retuning this again doesn't
#: need a deploy -- a query param override is enough.
DEFAULT_STAPLE_MIN_PERCENTAGE = 65.0

#: If `min_percentage` leaves zero rows for a window, `list_staples`
#: retries once at this lower floor before giving up -- a softer bar for
#: thinner/more diverse metagame snapshots, rather than surfacing nothing
#: at all. Same query-param-overridable posture as
#: `DEFAULT_STAPLE_MIN_PERCENTAGE`.
DEFAULT_STAPLE_FALLBACK_MIN_PERCENTAGE = 45.0

#: Below this window span, every tournament in range is pooled -- a
#: narrow window is a small enough sample on its own. At or above it,
#: `_STAPLES_MTGTOP8_MIN_PLAYERS`/MTGO-source gating kicks in instead (see
#: `list_staples`), so a long/all-time window's pool doesn't include every
#: small local event ever recorded.
_STAPLES_POOL_WINDOW_MAX_DAYS = 65

#: MTGTop8-sourced tournaments need more players than this to qualify for
#: the pool once the window is `_STAPLES_POOL_WINDOW_MAX_DAYS` or wider.
#: MTGO-sourced tournaments have no such gate (any player count, including
#: leagues' `players == 0`) -- see `list_staples`.
_STAPLES_MTGTOP8_MIN_PLAYERS = 80

#: Mirrors `barrins_scripture.schemas.formats.Formats.DUEL_COMMANDER`
#: (the exact string that source stores into `bs_tournaments.format`).
#: Not imported cross-app on purpose -- `barrins_api` doesn't depend on
#: `barrins_scripture`'s package, only on the string it writes.
DUEL_COMMANDER_FORMAT = "Duel Commander"

#: Default lower bound applied to every date-filtered Tolaria News query
#: (`list_decks`, `list_tournaments`, `list_staples`, `all_time` trends)
#: whenever the caller doesn't supply an explicit `date_from` -- the first
#: MTGO Duel Commander events predate this only with noise too sparse to
#: be representative of the current meta. An explicit caller-supplied
#: `date_from` (e.g. the frontend's "custom range" preset) always
#: overrides this, even when it's earlier.
EARLIEST_RELEVANT_DATE = date_type(2015, 11, 1)

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50

TournamentSizeBucket = Literal["leagues", "small", "medium", "large", "major"]


def exclude_mtgtop8_mtgo_mirrors() -> ColumnElement[bool]:
    """True when a `BSTournament` is *not* an MTGTop8 mirror of a native
    MTGO event -- MTGTop8 sometimes lists an MTGO event under its own
    tournament entry (name contains "MTGO"); the decks are already
    counted via the native `mtgo`-sourced tournament, so listing or
    aggregating both would double up the same decks. Applied
    unconditionally (not a user-toggleable filter) everywhere tournaments
    or their decks are listed or aggregated: `list_decks`,
    `list_commanders`, `list_trending_commanders`, `list_staples` (this
    module) and `tournaments.list_tournaments`."""
    return ~and_(
        BSTournament.source == BSSource.mtgtop8,
        BSTournament.name.ilike("%MTGO%"),
    )


def size_bucket_condition(bucket: TournamentSizeBucket) -> ColumnElement[bool]:
    """SQL condition for one `TournamentSizeBucket` -- both `list_decks`'s
    and (cross-module) `tournaments.list_tournaments`'s `sizes` filters OR
    one or more of these together. Numeric buckets start at `players >=
    1` (not `>= 0`) so a non-league tournament that happens to report
    `players == 0` (an ingestion anomaly, not a real "0 players" event)
    doesn't silently land in `small`, and so leagues never double-match a
    numeric bucket."""
    if bucket == "leagues":
        return and_(
            BSTournament.source == BSSource.mtgo,
            BSTournament.players == 0,
            BSTournament.name.contains("League"),
        )
    if bucket == "small":
        return and_(BSTournament.players >= 1, BSTournament.players <= 16)
    if bucket == "medium":
        return and_(BSTournament.players >= 17, BSTournament.players <= 63)
    if bucket == "large":
        return and_(BSTournament.players >= 64, BSTournament.players <= 99)
    return BSTournament.players >= 100  # "major"


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
    sizes: frozenset[TournamentSizeBucket] | None,
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

    `sizes` is additive -- a deck matches if its tournament falls into
    *any* selected `TournamentSizeBucket` (see `size_bucket_condition`).
    """
    limit = min(limit, _MAX_LIMIT) if limit else _DEFAULT_LIMIT
    stmt = (
        select(BSDeck, BSTournament.name, BSTournament.source)
        .join(BSTournament, BSDeck.tournament_id == BSTournament.id)
        .where(
            BSTournament.format == DUEL_COMMANDER_FORMAT,
            exclude_mtgtop8_mtgo_mirrors(),
        )
        .order_by(BSDeck.date.desc(), BSDeck.id.desc())
    )
    if player is not None:
        stmt = stmt.where(BSDeck.player.ilike(f"%{player}%"))
    if source is not None:
        stmt = stmt.where(BSTournament.source == source)
    if commander is not None:
        stmt = stmt.where(_sideboard_card_exists(BSDeckCard.card_name == commander))
    if sizes:
        stmt = stmt.where(or_(*(size_bucket_condition(b) for b in sizes)))
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
    # No explicit date_from -> default to EARLIEST_RELEVANT_DATE rather than
    # leaving the lower bound open; an explicit date_from (even one earlier
    # than the floor) always overrides it.
    stmt = stmt.where(BSDeck.date >= (date_from or EARLIEST_RELEVANT_DATE))
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
            exclude_mtgtop8_mtgo_mirrors(),
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


#: Above this span, a custom window buckets by banlist period instead of
#: by week (see `_resolve_trend_window`'s `custom` branch) -- roughly 3x
#: a banlist period's own ~60-day span, comfortably separating "a custom
#: range shaped like banlist_period/rolling_30d" from "a custom range
#: shaped like all_time".
_CUSTOM_WEEKLY_BUCKET_MAX_DAYS = 180


async def _resolve_trend_window(
    session: AsyncSession,
    *,
    mode: TrendWindowMode,
    period_offset: int,
    date_from: date_type | None,
    date_to: date_type | None,
) -> tuple[WindowOut, list[tuple[date_type, date_type]]]:
    """Resolves the outer date range for `mode` (walking `period_offset`
    banlist periods into the past when `mode` is `banlist_period`) and the
    equal-length sub-buckets the trend line plots one point per.

    `all_time`'s buckets are the historical banlist periods themselves
    (`dc_calendar.all_time_periods`), not weekly slices -- weekly buckets
    across an open-ended, potentially years-long span would produce an
    unreadable number of points; one point per banlist era is the natural
    granularity "all time" implies. `custom` picks between the two
    strategies by span (see `_CUSTOM_WEEKLY_BUCKET_MAX_DAYS`), since a
    caller-supplied range can be either shape.
    """
    today = date_type.today()

    if mode == "custom":
        assert date_from is not None  # the route 400s otherwise
        resolved_to = date_to or today
        buckets = (
            _weekly_buckets(date_from, resolved_to)
            if (resolved_to - date_from).days <= _CUSTOM_WEEKLY_BUCKET_MAX_DAYS
            else [
                (p.date_from, p.date_to)
                for p in all_time_periods(date_from, resolved_to)
            ]
        )
        return (
            WindowOut(
                kind=mode,
                label=f"custom:{date_from.isoformat()}_{resolved_to.isoformat()}",
                date_from=date_from,
                date_to=resolved_to,
            ),
            buckets,
        )

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
    # Never plot further back than EARLIEST_RELEVANT_DATE even if older
    # data exists -- same floor list_decks/list_tournaments/list_staples
    # apply by default.
    earliest = max(earliest, EARLIEST_RELEVANT_DATE)
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
    date_from: date_type | None = None,
    date_to: date_type | None = None,
) -> CommanderTrendsResponse:
    """Top `_TOP_TRENDING_COMMANDERS` commanders (solo or partner pairs) by
    deck count in `mode`'s window, each with a per-bucket play-count trend.

    Partner pairs are grouped by the sorted tuple of their resolved
    commander names, so a pair groups identically regardless of which
    card `bs_deck_cards` happened to store first.

    `date_from`/`date_to` only apply to `mode=custom` (see the route's
    validation -- `date_from` is required in that case).
    """
    window_out, buckets = await _resolve_trend_window(
        session,
        mode=mode,
        period_offset=period_offset,
        date_from=date_from,
        date_to=date_to,
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
                exclude_mtgtop8_mtgo_mirrors(),
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


def _staple_row(
    name: str, match: Card | None, deck_count: int, decks_considered: int
) -> StapleRow:
    return StapleRow(
        name=match.name if match is not None else name,
        cmc=match.mana_value if match is not None else None,
        type_line=match.type_line if match is not None else None,
        scryfall_id=match.scryfall_id if match is not None else None,
        mana_cost=match.mana_cost if match is not None else None,
        text=match.text if match is not None else None,
        keywords=match.keywords if match is not None else [],
        deck_count=deck_count,
        percentage=round(deck_count / decks_considered * 100, 1),
    )


async def list_staples(
    session: AsyncSession,
    *,
    date_from: date_type,
    date_to: date_type,
    min_percentage: float = DEFAULT_STAPLE_MIN_PERCENTAGE,
    fallback_min_percentage: float = DEFAULT_STAPLE_FALLBACK_MIN_PERCENTAGE,
) -> StaplesResponse:
    """Mainboard card frequency (`GET /decks/staples`) pooled across every
    qualifying Duel Commander tournament in `[date_from, date_to]` -- a
    metagame-wide "staples" view, not scoped to a single tournament.

    `min_percentage`/`fallback_min_percentage` default to values tuned
    against real pooled data, but are caller-overridable (via the route's
    own query params) so retuning them again doesn't need a deploy.

    Qualifying tournaments:
    - if the window spans fewer than `_STAPLES_POOL_WINDOW_MAX_DAYS` days,
      every tournament dated in the window (a narrow window doesn't need
      further gating -- the pool stays small on its own);
    - otherwise, only "major" tournaments: MTGTop8 tournaments with more
      than `_STAPLES_MTGTOP8_MIN_PLAYERS` players, or any MTGO-sourced
      tournament (leagues and other MTGO event types alike) -- keeps a
      long/all-time window's pool from including every small local event
      ever recorded.
    - Always excluded (`exclude_mtgtop8_mtgo_mirrors`): MTGTop8
      tournaments whose name contains "MTGO" -- MTGTop8 mirrors some
      MTGO events under its own listing, and the underlying decks are
      already counted via the native `mtgo`-sourced tournament, so
      counting both would double-count the same decks.

    Sideboard rows are excluded entirely (see this module's docstring:
    for Duel Commander that's the commander, already covered by the
    commander-trend chips). Lands are excluded too -- near-ubiquitous by
    deck-building necessity, not by strategic choice; a card that can't be
    resolved against `mj_cards` can't be classified as a land, so it's
    kept rather than silently dropped.
    """
    span_days = (date_to - date_from).days

    tournament_ids_stmt = select(BSTournament.id).where(
        BSTournament.format == DUEL_COMMANDER_FORMAT,
        BSTournament.date >= date_from,
        BSTournament.date <= date_to,
        exclude_mtgtop8_mtgo_mirrors(),
    )
    if span_days >= _STAPLES_POOL_WINDOW_MAX_DAYS:
        tournament_ids_stmt = tournament_ids_stmt.where(
            or_(
                and_(
                    BSTournament.source == BSSource.mtgtop8,
                    BSTournament.players > _STAPLES_MTGTOP8_MIN_PLAYERS,
                ),
                BSTournament.source == BSSource.mtgo,
            )
        )
    tournament_ids = (await session.execute(tournament_ids_stmt)).scalars().all()

    if not tournament_ids:
        return StaplesResponse(
            date_from=date_from,
            date_to=date_to,
            tournaments_considered=0,
            decks_considered=0,
            min_percentage=min_percentage,
            rows=[],
        )

    deck_count = (
        await session.execute(
            select(func.count())
            .select_from(BSDeck)
            .where(BSDeck.tournament_id.in_(tournament_ids))
        )
    ).scalar_one()
    if deck_count == 0:
        return StaplesResponse(
            date_from=date_from,
            date_to=date_to,
            tournaments_considered=len(tournament_ids),
            decks_considered=0,
            min_percentage=min_percentage,
            rows=[],
        )

    card_rows = (
        (
            await session.execute(
                select(BSDeckCard)
                .join(BSDeck, BSDeckCard.deck_id == BSDeck.id)
                .where(
                    BSDeck.tournament_id.in_(tournament_ids),
                    BSDeckCard.board == BSDeckBoard.mainboard,
                )
            )
        )
        .scalars()
        .all()
    )
    resolved = await resolved_cards(session, card_rows)

    decks_by_name: dict[str, set[uuid.UUID]] = {}
    match_by_name: dict[str, Card | None] = {}
    for card in card_rows:
        match = resolved[card.id]
        if match is not None and categorize(match.type_line) == "land":
            continue
        name = match.name if match is not None else card.card_name
        decks_by_name.setdefault(name, set()).add(card.deck_id)
        match_by_name.setdefault(name, match)

    sorted_rows = sorted(
        (
            _staple_row(name, match_by_name[name], len(decks), deck_count)
            for name, decks in decks_by_name.items()
        ),
        key=lambda row: (-row.deck_count, row.name),
    )

    applied_min_percentage = min_percentage
    rows = [row for row in sorted_rows if row.percentage >= applied_min_percentage][
        :_TOP_STAPLES
    ]
    if not rows:
        # The primary floor left nothing -- retry once at the softer
        # fallback rather than surfacing an empty table outright.
        applied_min_percentage = fallback_min_percentage
        rows = [row for row in sorted_rows if row.percentage >= applied_min_percentage][
            :_TOP_STAPLES
        ]

    return StaplesResponse(
        date_from=date_from,
        date_to=date_to,
        tournaments_considered=len(tournament_ids),
        decks_considered=deck_count,
        min_percentage=applied_min_percentage,
        rows=rows,
    )
