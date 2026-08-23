# Karn Tablets: Duel Commander metagame clustering

Clusters Duel Commander tournament decks (`bs_*`, scraped by Barrin's
Scripture) into archetypes over a time window, and aggregates that into a
deck-type distribution — feeding Tolaria News' public `/metagame`/
`/archetypes` routes and Tamiyo Scroll's S6 admin dashboard (T6, see
ADR-13, `docs/content/ops/architecture/decisions.md`, for the full
context/alternatives/decision record).

## Scope (v1)

- **Format**: Duel Commander only, matching Tolaria News' own identity
  (`apps/tolaria_news/README.md`).
- **Windowing**: both rolling-30-day and banlist-period modes (the
  period between consecutive Banned & Restricted announcement windows —
  last Tuesday of an odd month through the last Monday of the following
  odd month).
- **Data in**: a read-only Postgres credential scoped to `bs_*`/`mj_cards`
  only — this app never writes to `barrins_api`'s schema.
- **Data out**: pushes results to `barrins_api`'s
  `POST /internal/karn/ingest` after each run — it does not expose any
  API of its own (ADR-13's push-based data flow). No inbound network
  access needed at all.
- **Scheduling**: a systemd timer (mirrors `scripture_scraper`'s shape),
  not an internal scheduler library.

## Tech stack

| Component | Technology |
| --------- | ----------- |
| Language | Python 3.14 |
| DB access | `sqlalchemy` + `psycopg2` (sync — this is a batch job, not a web server) |
| Feature engineering | `pandas`, `numpy` |
| Clustering | `scikit-learn` (KMeans/DBSCAN/GaussianMixture, PCA, silhouette score), `scipy` |
| Push | `requests` |
| Tests | pytest + pytest-cov |

## Origin

The clustering/feature-engineering/aggregation logic is adapted from a
prior, unmerged attempt at this same problem
(`barrins-archive/barrins_api/app/services/ml/`), which targeted an
earlier, superseded schema (`dl_*` tables, a bare `cards` table) — ported
here against the schema actually shipped (`bs_*`, T2; `mj_cards`, S8),
with a real orchestration/push layer (`pipeline.py`/`push.py`) replacing
the original's Parquet-file output (`run_all.py`). Table/column renames
aside, the feature engineering and clustering math are unchanged. Not
ported: `dc_report.py`'s PDF/Markdown/Moxfield-export and personal-deck
card-swap-suggestion engine, and `visualize.py`'s treemap/radar/sankey
dataset generation — neither fits a "push structured data, let the
consuming frontend render it" architecture; whether either becomes real
scope later is an open product question, not decided here.

`aggregation_advanced.py`'s `standing_weights`/`weighted_aggregate` were
**not** ported: the original derived a per-deck weight from a plain
`rank` integer column the current `bs_decks` schema doesn't have (only a
free-form `result` string and a separately-keyed `bs_standings` table) —
building a reliable deck-to-standing linkage is its own small design
problem, not a mechanical port.

## Usage

```sh
uv run karn-tablets --window both --date-to 2026-06-15
uv run karn-tablets --window rolling_30d --dry-run
```

`--help` lists every option. `--window` (`rolling_30d` / `banlist_period`
/ `both`) defaults to `both`; `--date-to` defaults to today; `--algorithm`
(`kmeans` / `dbscan` / `gmm`) defaults to `kmeans`; `--dry-run` runs
clustering but skips the push, for local inspection.

## Configuration

| Variable | Purpose |
| -------- | ------- |
| `KARN_TABLETS_DATABASE_URL_RO` | Read-only Postgres credential, scoped to `bs_*`/`mj_cards` |
| `BARRINS_API_URL` | `barrins_api` base URL |
| `KARN_INGEST_TOKEN` | Shared secret for `POST /internal/karn/ingest` (`X-Karn-Token` header) |

Loaded from `apps/karn_tablets/.env` in local dev (`python-dotenv`); the
systemd unit sets real environment variables in production, no `.env`
there.
