# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [Unreleased]

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
