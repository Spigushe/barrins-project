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
- Deployment (T8): `ops/my-server/karn_tablets.yml` + the `karn_tablets`
  Ansible role run this pipeline as a daily `systemd`-timer job on the
  VPS (03:00 UTC, `Persistent`), `deploy_env` staging/production
  side-by-side. The shared `KARN_INGEST_TOKEN` is provisioned by the
  `karn_ingest_token` role; `KARN_TABLETS_DATABASE_URL_RO` points at a
  hand-created read-only Postgres role. See
  `ops/my-server/roles/karn_tablets/README.md`.
- CI: a `karn` job in `.github/workflows/CI.yml`
  (`apps/karn_tablets/**` / `apps/dc_calendar/**` paths-filter) running
  `ruff` / `ty` / `pytest`.
