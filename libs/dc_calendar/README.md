# dc_calendar: Duel Commander banlist/window date math

A small, dependency-free package holding the date-boundary rules shared
by every Duel Commander metagame feature that needs to bucket data by
time window: `karn_tablets` (metagame clustering, T6) and `barrins_api`'s
Tolaria News BFF (commander-trend chips, T4 iteration 2).

Extracted from `karn_tablets/windowing.py`, where this logic originally
lived — moved here once a second consumer needed the exact same rules,
rather than duplicating it (Constitution §4.2).

## Scope

- **Rolling 30-day windows**: the most recent 30 days as of a reference
  date.
- **Banlist-period windows**: non-overlapping periods aligned to Magic's
  Banned & Restricted announcement rhythm — last Tuesday of an
  odd-numbered month through the last Monday of the following
  odd-numbered month. The boundary math (year rollover, month-length
  edge cases) is the highest-risk part of this package and is
  independently, exhaustively tested (`tests/test_windowing.py`).
- **All-time period listing**: every banlist period spanning an
  arbitrary date range, oldest first — backs "all time" trend buckets
  and "any previous banlist period" lookups by offset.

## Non-scope

No database access, no HTTP, no framework dependency of any kind — pure
`datetime` arithmetic only. Consumers own everything downstream of
"which date range is this" (querying, aggregation, presentation).

## Usage

```python
from dc_calendar.windowing import (
    WindowKind,
    all_time_periods,
    banlist_period_window,
    resolve_windows,
    rolling_30d_window,
)
```

See `dc_calendar/windowing.py`'s docstrings for the full function
reference.
