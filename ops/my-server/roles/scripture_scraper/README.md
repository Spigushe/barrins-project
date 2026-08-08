# scripture_scraper

Clones/updates `apps/barrins_scripture` from this monorepo, installs its
dependencies with `uv`, and schedules its daily MTGO + MTGTop8 scrape (plus
the Sunday-only biweekly gap-check) via a `systemd` `.service`/`.timer`
pair — this app has no HTTP-facing component, so unlike
`fastapi_backend`/`react_frontend` there's no domain/SSL/reverse-proxy
role involved, just a scheduled job. It also schedules the T3 sweep
(`apps/barrins_scripture/barrins_scripture/sweep.py`) on its own,
independent `.service`/`.timer` pair — ingesting the JSON archive into
`barrins_api`'s `bs_*` tables is a separate concern from scraping it, on
its own tick (T3/T8's 2026-08 decision).

Mirrors `mtg_scraper`'s existing GitHub Actions schedule
(`daily_scraping.yml` + `biweekly_check_gaps.yml`, both retired once this
is proven equivalent — see T1,
`docs/project/v2.0.0-bump/t1-scripture-repo-migration/`), moved to the
VPS per that item's own scheduling decision, using the same
`.service`/`.timer` pattern `postgres_backup` already established rather
than inventing a new one.

## What it does

1. Clones/updates the monorepo at `scripture_scraper_git_branch` into
   `scripture_scraper_config.app_root`, the same `github_token`-based
   auth every other app-deploying role here uses.
2. Installs Python 3.14 + dependencies via `uv sync --all-extras --dev`.
3. Templates `/usr/local/bin/barrins_scripture_scrape.sh`: runs
   `uv run scrape --source mtgo --output-dir ...` and
   `--source mtgtop8`, then — only on Sundays (UTC), alternating by ISO
   week parity — either
   `python -m barrins_scripture.scripts.top8_check_gaps` or
   `python -m barrins_scripture.scripts.mtgo_empty_decks`.
4. Templates a oneshot systemd service (`barrins_scripture.service`) and
   a daily timer (`barrins_scripture.timer`, default 22:00 UTC ±30 min
   `RandomizedDelaySec`, `Persistent=true`).
5. Deploys the local `.env` (`scripture_scraper_env_file`, if present —
   same "use it if available" pattern as `fastapi_backend_env_file`) to
   `{{ work_dir }}/.env`, mode `0600`. Templates
   `/usr/local/bin/barrins_scripture_sweep.sh`: sources that `.env`
   (`BARRINS_API_URL`/`SCRIPTURE_INGEST_TOKEN`) and runs
   `uv run sweep --mode recent --days <sweep_days> --archive-dir ...`
   against `output_dir`. Templates a oneshot systemd service
   (`barrins_scripture_sweep.service`) and a timer
   (`barrins_scripture_sweep.timer`, every 6 hours,
   `RandomizedDelaySec=900`, `Persistent=true`) — independent of the
   scrape timer above.

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `scripture_scraper_repo` | yes | / | `owner/repo` to clone (this monorepo). |
| `scripture_scraper_repo_subdir` | no | `''` | Subdirectory `apps/barrins_scripture` lives at within the repo. |
| `scripture_scraper_app_name` | yes | / | Used to name the checkout directory under `~/projects/`. |
| `scripture_scraper_git_branch` | no | `main` | Branch to deploy from. |
| `scripture_scraper_output_dir` | no | `<work_dir>/scraped` | Where the JSON archive is written — see the note below. |
| `scripture_scraper_daily_hour` | no | `22` | Hour (0-23, UTC) the daily scrape timer fires. |
| `scripture_scraper_github_token` | no | falls back to the shared `github_token` role | Only needed if a different token than the shared one is required. |
| `scripture_scraper_env_file` | no | `''` | Local, git-ignored path to a `.env` holding `BARRINS_API_URL`/`SCRIPTURE_INGEST_TOKEN` for the sweep — see `secrets/barrins_scripture/production.env.example`. Deployed to `{{ work_dir }}/.env` if present, skipped (with a note) otherwise. |
| `scripture_scraper_sweep_days` | no | `7` | Lookback window (days) the sweep's `--mode recent` rescans on every tick — mirrors `sweep.py`'s own `DEFAULT_RECENT_DAYS`. |

## Requirements

- `github_token` role must run first (provides the shared clone
  credential this role falls back to).
- `scripture_scraper_env_file` should point at a real, filled-in `.env`
  before the sweep timer can succeed — without it the timer still gets
  installed and enabled, but every tick fails at `source .env` (missing
  file) or at the ingestion POST (missing/wrong token). See
  `secrets/README.md`.

## Validation

Per [`new-service-checklist.md`](../../../../docs/content/ops/deployment/new-service-checklist.md)
Step 0.3 — this service has no HTTP surface, so there is no `GET /health`
to poll:

- **Signal**: `systemctl status barrins_scripture.service` (last exit
  code) / `journalctl -u barrins_scripture.service -n 50` (a timer-driven
  job's equivalent of a health check). Currently manual — see "Not
  automated yet" below.
- **Idempotency**: each scrape writes to a filename derived
  deterministically from the tournament URL/date
  (`save_tournament_scrape` in `barrins_scripture/utils/{mtgo,mtgtop8}.py`)
  and overwrites that path in place. Re-running the same day's scrape —
  a manual redeploy, or the timer's own `Persistent=true` catch-up run
  after a missed boot — does not duplicate archive files.

The sweep (T3/T8) has its own service/timer pair, checked the same way:

- **Signal**: `systemctl status barrins_scripture_sweep.service` /
  `journalctl -u barrins_scripture_sweep.service -n 50`. Same "manual for
  now" caveat as above.
- **Idempotency**: `barrins_api`'s ingestion route upserts on each table's
  natural key (T2), so a sweep tick re-posting an already-ingested file is
  a no-op, not a duplicate row — confirmed by
  `apps/barrins_api/tests/scripture/test_ingest.py::
  test_ingest_is_idempotent`. A failed tick (network error, `barrins_api`
  down/misconfigured, malformed JSON) is logged and skipped per-file, not
  retried within the run; the next scheduled tick (every 6h) picks it up.

## Rollback

Per Step 0.4/0.6:

- **Code**: this service isn't release-tagged (Step 0.6) — redeploy by
  re-running the playbook with an older `scripture_scraper_git_branch`/
  commit, same as any other role here (see
  [`rollback.md`](../../../../docs/content/ops/deployment/rollback.md)).
  `scripture_scraper_git_branch` currently defaults to `staging` until
  this rewrite is proven equivalent to `mtg_scraper` (T1's own done
  statement).
- **Data/artifact**: the JSON archive itself is never rolled back —
  it's an append-only, replayable record (§1.3 of the v2.0.0-bump plan).
  Rolling code back can at most overwrite that day's already-written
  files (see idempotency above); it never deletes prior history, and
  nothing outside this service reads `output_dir` directly today.
- **Sweep/ingested data**: also never rolled back by this playbook. If a
  bad sweep needs undoing, that's a `barrins_api`/database-side operation
  (T3's ingestion route, not this role) — re-running `--mode full` from
  this role only re-applies the current archive contents, it doesn't
  delete rows a bad ingest already wrote.

## Data ownership & backup

Per Step 0.5 — this service holds no database (§1.2: Barrin's Scripture
never gets its own `DATABASE_URL`), so
[`database.md`](../../../../docs/content/ops/deployment/database.md)'s
Postgres backup story doesn't apply. `scripture_scraper_output_dir` is a
plain directory of JSON files on the VPS. It's disposable/replayable in
principle (the archive can be re-scraped from source tournaments), but
nothing currently backs up or rotates `output_dir` on the VPS itself, and
it isn't yet a git submodule (see below) — until that wiring lands, a
VPS disk failure would lose any scrape newer than the last commit to
`mtg_decklist_cache`.

## Not automated yet

- **The JSON archive isn't a git submodule.** `scripture_scraper_output_dir`
  is a plain directory on the VPS — nothing here commits or pushes it
  anywhere. Per T1's plan, the archive belongs in its own git repository
  (a submodule pointing at `mtg_decklist_cache`/its durable successor);
  wiring that up, and adding the commit/push step this role's wrapper
  script would then need, is still an open T1 task.
- **No email/notification on failure**, unlike the GitHub Actions
  workflows this replaces (`dawidd6/action-send-mail`) — a known,
  accepted behavior change. `systemctl status`/`journalctl -u
  barrins_scripture.service` is how a failed run is currently surfaced.
  Same applies to `barrins_scripture_sweep.service` — **decided
  2026-08-07**: wait for D2/F1's generic scheduled-job notification
  mechanism rather than build a scripture-only stopgap (T8).

## Example

```yaml
- role: scripture_scraper
  tags: [scripture, deploy]
```

See `ops/my-server/barrins_scripture.yml` for how it's wired into this
repo.
