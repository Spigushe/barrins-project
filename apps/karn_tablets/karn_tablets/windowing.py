"""Metagame window calculation: rolling 30-day and banlist-period modes.

Two windowing strategies, both shipped (T6, ADR-13):

- Rolling 30-day: always the most recent 30 days as of the run date.
- Banlist-period: non-overlapping periods aligned to Magic's Banned &
  Restricted announcement rhythm -- from the last Tuesday of an
  odd-numbered month to the last Monday of the following odd-numbered
  month (e.g. last Tuesday of March -> last Monday of May).

The banlist-period boundary math is the trickiest part of this whole
pipeline (T6's own doc flags it explicitly) -- year rollover (Nov -> Jan)
and month-length edge cases -- so it's isolated here as pure functions,
independently tested, before anything else in the pipeline depends on it.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

#: Odd-numbered months, in calendar order. A banlist period starts on one
#: of these and ends on the next one in this cycle (wrapping Nov -> Jan).
_ODD_MONTHS: tuple[int, ...] = (1, 3, 5, 7, 9, 11)

_TUESDAY = 1

ROLLING_WINDOW_DAYS = 30


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


def _next_odd_month(month: int) -> tuple[int, int]:
    """The next odd month after `month`, and the year offset to add (0 or 1)."""
    idx = _ODD_MONTHS.index(month)
    next_idx = (idx + 1) % len(_ODD_MONTHS)
    year_offset = 1 if _ODD_MONTHS[next_idx] < month else 0
    return _ODD_MONTHS[next_idx], year_offset


def banlist_period_containing(reference_date: date) -> tuple[date, date]:
    """The (start, end) banlist period that `reference_date` falls within.

    Searches backward from `reference_date`'s month for the most recent
    odd-month anchor whose resulting period actually contains the date --
    at most 6 months back, since periods are 2 calendar months wide and
    odd months repeat every other month.

    A period's end is the day *before* the next period's start (`last
    Tuesday of the following odd month`), not that month's independently
    computed `last Monday` -- those two disagree whenever the following
    odd month's last calendar day is itself a Monday (e.g. November
    2026: last Monday = Nov 30, but last Tuesday = Nov 24, six days
    *earlier* -- computing the end independently would make this
    period's end fall after the next period's own start, a real overlap
    caught by `test_every_day_of_a_full_year_resolves_with_no_gap_or_overlap`).
    Deriving `end` from the next period's `start` instead guarantees
    "non-overlapping periods" (T6's own requirement) holds unconditionally,
    at the cost of occasionally ending a period a few days earlier than a
    literal "last Monday" reading would.
    """
    for months_back in range(7):
        total_month_index = (reference_date.month - 1) - months_back
        year_offset, month0 = divmod(total_month_index, 12)
        year = reference_date.year + year_offset
        month = month0 + 1
        if month not in _ODD_MONTHS:
            continue

        start = last_weekday_of_month(year, month, _TUESDAY)
        end_month, end_year_offset = _next_odd_month(month)
        next_period_start = last_weekday_of_month(
            year + end_year_offset, end_month, _TUESDAY
        )
        end = next_period_start - timedelta(days=1)

        if start <= reference_date <= end:
            return start, end

    # Unreachable: every date falls in exactly one period within 6 months
    # of searching backward from its own month (odd months repeat every
    # other calendar month) -- kept as a defensive guard, not a real path.
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


def resolve_windows(date_to: date, kinds: tuple[WindowKind, ...]) -> list[Window]:
    """Resolve the requested window kind(s) against a single reference date."""
    resolvers = {
        WindowKind.rolling_30d: rolling_30d_window,
        WindowKind.banlist_period: banlist_period_window,
    }
    return [resolvers[kind](date_to) for kind in kinds]
