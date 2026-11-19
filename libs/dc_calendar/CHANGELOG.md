# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [Unreleased]

### Fixed

- Banlist periods are now anchored on the last Monday of each odd month
  (the announcement day, 20:00 Europe/Paris) instead of the last
  Tuesday. The two only disagree when an odd month ends on a Monday:
  November 2026 used to end the Sep -> Nov period on Nov 23 and announce
  the next banlist on Nov 24; it now ends on Nov 30 and the next period
  starts Dec 1. `effective_banlist_period` now reports `next_at` on the
  current period's last day at 20:00 (it used to use the next period's
  first day), and `banlist_period_number` reads the anchor month from the
  day before `date_from`, since `date_from` can now fall in an even
  month.

### Added

- Initial package, extracted from `karn_tablets/windowing.py`: rolling-
  30-day and banlist-period window resolution, with the banlist-period
  boundary math (last Tuesday of an odd month -> last Monday of the
  following odd month, including year rollover) isolated and
  independently tested.
- `all_time_periods`: every banlist period across an arbitrary date
  range, oldest first — backs "all time" trend bucketing and "any
  previous banlist period" lookups for Tolaria News' commander-trend
  endpoint.
