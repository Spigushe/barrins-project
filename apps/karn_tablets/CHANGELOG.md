# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [Unreleased]

### Added

- Initial project scaffold (`pyproject.toml`, package layout, tooling).
- `windowing`: rolling-30-day and banlist-period window resolution, with
  the banlist-period boundary math (last Tuesday of an odd month -> last
  Monday of the following odd month, including year rollover) isolated
  and independently tested.
- `extract`: read-only extraction of Duel Commander decks from `bs_*`,
  resolving `bs_deck_cards.card_name` against `mj_cards` (T2's schema has
  no FK between the two).
- `features`: per-card and per-deck feature engineering, including
  oracle-text functional classification (Removal, Card Draw, Ramp,
  Tutor, Board Wipe, ...) — adapted from a prior, unmerged attempt at
  this problem (`barrins-archive/barrins_api/app/services/ml/`).
- `clustering`: KMeans/DBSCAN/GaussianMixture over a PCA-reduced feature
  space, with automatic cluster-count selection (silhouette score / BIC).
- `aggregation`/`aggregation_advanced`: frequency-based representative
  decklist synthesis, prototype-deck selection, consensus aggregation,
  temporal decay weighting.
- `pipeline`: orchestrates one clustering run end-to-end and builds the
  push payload, with §45.2 provenance (pipeline version, generated-at).
- `push`: posts a run's result to `barrins_api`'s
  `POST /internal/karn/ingest`.
- `__main__`: `karn-tablets` CLI, the systemd-timer entry point.
