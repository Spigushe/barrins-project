"""Duel Commander metagame window calculation: rolling 30-day and
banlist-period modes.

Originally scaffolded inside `karn_tablets` (T6, ADR-13) and extracted
into this standalone package once `barrins_api`'s Tolaria News BFF needed
the same date math for its commander-trend endpoint (T4 iteration 2) --
one owner for the calendar rules, imported by both instead of duplicated.

Two windowing strategies:

- Rolling 30-day: always the most recent 30 days as of the run date.
- Banlist-period: non-overlapping periods aligned to the Duel Commander
  banlist announcement rhythm -- from the day after the last Monday of an
  odd-numbered month to the last Monday of the following odd-numbered
  month (e.g. Mar 31 -> May 25 2026). That start is usually the last
  Tuesday of the odd month, but not when the month ends on a Monday
  (Nov 30 2026 -> the next period starts Dec 1).

The banlist-period boundary math is the trickiest part of this whole
pipeline (T6's own doc flags it explicitly) -- year rollover (Nov -> Jan)
and month-length edge cases -- so it's isolated here as pure functions,
independently tested, before anything else depends on it.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

#: Odd-numbered months, in calendar order. A banlist period starts on one
#: of these and ends on the next one in this cycle (wrapping Nov -> Jan).
_ODD_MONTHS: tuple[int, ...] = (1, 3, 5, 7, 9, 11)

_MONDAY = 0

ROLLING_WINDOW_DAYS = 30

#: A Duel Commander banlist change is announced (and takes effect) at this
#: time on the *last day* of the outgoing period -- the last Monday of an
#: odd month -- see `effective_banlist_period`.
BANLIST_EFFECTIVE_TIME = time(20, 0)
BANLIST_TIMEZONE = ZoneInfo("Europe/Paris")


class WindowKind(StrEnum):
    rolling_30d = "rolling_30d"
    banlist_period = "banlist_period"


@dataclass(frozen=True)
class Window:
    """A concrete, resolved date range a clustering run operates over."""

    kind: WindowKind
    date_from: date
    date_to: date

    #: Stable identifier for this specific window instance -- used as the
    #: natural key when Karn Tablets pushes results (`kt_windows`), so a
    #: re-run of the same period is an idempotent upsert, not a duplicate.
    @property
    def label(self) -> str:
        if self.kind is WindowKind.rolling_30d:
            return f"rolling_30d:{self.date_to.isoformat()}"
        return f"banlist_period:{self.date_from.isoformat()}_{self.date_to.isoformat()}"


def last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """The last occurrence of `weekday` (Monday=0 ... Sunday=6) in `year`-`month`.

    Handles December -> next-January rollover and every month-length edge
    case by computing the last calendar day of the month first, then
    walking backward to the target weekday -- no fixed "day count" that
    could be wrong for a 28/29/30/31-day month.
    """
    if not 0 <= weekday <= 6:
        raise ValueError(f"weekday must be 0-6 (Monday-Sunday), got {weekday}")
    next_month_first = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    last_day_of_month = next_month_first - timedelta(days=1)
    offset = (last_day_of_month.weekday() - weekday) % 7
    return last_day_of_month - timedelta(days=offset)


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """(year, month) `delta` calendar months away from `year`-`month`."""
    year_offset, month0 = divmod((month - 1) + delta, 12)
    return year + year_offset, month0 + 1


def banlist_period_containing(reference_date: date) -> tuple[date, date]:
    """The (start, end) banlist period that `reference_date` falls within.

    The *anchor* of every period is its end: the last Monday of an odd
    month, the day the next banlist is announced. A period runs from the
    day after the previous anchor through its own anchor, inclusive.

    The start is derived from the previous anchor (`last Monday + 1`), not
    computed independently as "last Tuesday of the odd month" -- those two
    disagree whenever the odd month's last calendar day is itself a
    Monday (e.g. November 2026: last Monday = Nov 30, but last Tuesday =
    Nov 24, six days *earlier*). Anchoring on the Tuesday made the Sep ->
    Nov 2026 period end on Nov 23 and announced the next banlist a week
    early; anchoring on the Monday keeps the announcement date right and
    lets the following period start in the even month instead (Dec 1).

    The anchor is the first odd-month last Monday on or after
    `reference_date` -- at most 2 months ahead, since odd months repeat
    every other calendar month.
    """
    for months_ahead in range(3):
        year, month = _shift_month(
            reference_date.year, reference_date.month, months_ahead
        )
        if month not in _ODD_MONTHS:
            continue
        end = last_weekday_of_month(year, month, _MONDAY)
        if end < reference_date:
            continue
        prev_year, prev_month = _shift_month(year, month, -2)
        start = last_weekday_of_month(prev_year, prev_month, _MONDAY) + timedelta(
            days=1
        )
        return start, end

    # Unreachable: the reference month or one of the next two is odd and
    # its last Monday is on or after the reference date -- kept as a
    # defensive guard, not a real path.
    raise ValueError(
        f"could not resolve a banlist period for {reference_date}"
    )  # pragma: no cover


def rolling_30d_window(date_to: date) -> Window:
    """The rolling 30-day window ending on (inclusive of) `date_to`."""
    return Window(
        kind=WindowKind.rolling_30d,
        date_from=date_to - timedelta(days=ROLLING_WINDOW_DAYS),
        date_to=date_to,
    )


def banlist_period_window(date_to: date) -> Window:
    """The banlist-period window containing `date_to`."""
    start, end = banlist_period_containing(date_to)
    return Window(kind=WindowKind.banlist_period, date_from=start, date_to=end)


def effective_banlist_period(now: datetime) -> tuple[Window, datetime]:
    """The banlist period actually in effect at `now`, and the datetime
    the *next* banlist takes effect (20:00 Europe/Paris on the current
    period's last day -- the last Monday of an odd month).

    `banlist_period_window` only knows calendar-date boundaries -- a
    period's last day still "belongs" to it until midnight, even though
    the next banlist is announced at `BANLIST_EFFECTIVE_TIME` that same
    day. From that moment until midnight the *calendar* period is still
    the outgoing one while the *effective* (real-world) period is already
    the next one. This reconciles the two so "current season" flips and
    "next banlist" moves on as soon as the announcement lands.
    """
    now_paris = now.astimezone(BANLIST_TIMEZONE)
    raw = banlist_period_window(now_paris.date())
    announcement = datetime.combine(
        raw.date_to, BANLIST_EFFECTIVE_TIME, tzinfo=BANLIST_TIMEZONE
    )
    if now_paris < announcement:
        return raw, announcement
    following = banlist_period_window(raw.date_to + timedelta(days=1))
    next_at = datetime.combine(
        following.date_to, BANLIST_EFFECTIVE_TIME, tzinfo=BANLIST_TIMEZONE
    )
    return following, next_at


def banlist_period_number(window: Window) -> tuple[int, int]:
    """(year, 1-based index within that year) for a banlist-period
    `Window` -- Jan-anchored = 1, Mar-anchored = 2, ... Nov-anchored = 6.
    Resets every January; the year alone already disambiguates across year
    boundaries, so the index doesn't climb forever.

    Reads off the day before `date_from` -- the previous period's anchor,
    always the last Monday of one of `_ODD_MONTHS`. `date_from` itself
    can spill into the following even month (Nov 30 2026 is a Monday, so
    that period starts Dec 1) and `date_to` can roll into the following
    year, so neither can be read directly.
    """
    if window.kind is not WindowKind.banlist_period:
        raise ValueError(
            "banlist_period_number only applies to banlist_period windows, "
            f"got {window.kind}"
        )
    anchor = window.date_from - timedelta(days=1)
    return anchor.year, _ODD_MONTHS.index(anchor.month) + 1


def resolve_windows(date_to: date, kinds: tuple[WindowKind, ...]) -> list[Window]:
    """Resolve the requested window kind(s) against a single reference date."""
    resolvers = {
        WindowKind.rolling_30d: rolling_30d_window,
        WindowKind.banlist_period: banlist_period_window,
    }
    return [resolvers[kind](date_to) for kind in kinds]


def all_time_periods(earliest: date, date_to: date) -> list[Window]:
    """Every banlist period from the one containing `earliest` through the
    one containing `date_to`, oldest first.

    Used for "all time" trend bucketing (one point per historical banlist
    period) and for indexing "any previous banlist period" by offset from
    the end of this list. Walking backward from `date_to` is the natural
    direction (each period's start determines the next lookup); the
    result is reversed at the end since callers want oldest-first.
    """
    if earliest > date_to:
        raise ValueError(f"earliest ({earliest}) must not be after date_to ({date_to})")

    periods: list[Window] = []
    cursor = date_to
    while True:
        window = banlist_period_window(cursor)
        periods.append(window)
        if window.date_from <= earliest:
            break
        cursor = window.date_from - timedelta(days=1)
    periods.reverse()
    return periods
