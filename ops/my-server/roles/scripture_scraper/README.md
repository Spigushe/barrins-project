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

## Dormant since ADR-12 (2026-08-10)

Full circle: mtgo.com's edge/WAF started silently blackholing the VPS's
static outbound IP (confirmed IP-specific, not a datacenter-range policy
— see
`docs/content/service/barrins_scripture/incidents/2026-08-10-mtgo-network-block.md`),
so scraping+sweep scheduling moved back to GitHub Actions
(`.github/workflows/scripture-scrape.yml`), this time for a concrete,
confirmed reason rather than being replaced on principle. See ADR-12 in
`docs/content/ops/architecture/decisions.md` for the full alternatives/
trade-offs writeup.

This role's deploy logic (`tasks/deploy.yml`) is unchanged and still the
default — only `barrins_scripture.yml` now also sets
`scripture_scraper_teardown: true`, which runs `tasks/teardown.yml`
instead: stops+disables both timers/services, removes the four unit
files, the two wrapper scripts, the local archive clone (pushing any
pending changes first), and the app checkout. Nothing here was deleted —
re-running with `scripture_scraper_teardown: false` (or omitted)
redeploys the full VPS-scheduled stack from scratch, unchanged, if
GitHub Actions ever needs to be rolled back from.

## What it does

0. Installs `chromium` and `chromium-driver` from Debian's own apt repos —
   the MTGO scrape (`barrins_scripture/utils/selenium_driver.py`) drives
   headless Chrome via Selenium, and a bare VPS has neither the browser
   nor its runtime shared libraries. Using Debian's paired packages (rather
   than Selenium Manager's own Chrome-for-Testing auto-download) guarantees
   browser/driver version compatibility with no outbound network call
   needed at scrape time — see `chrome_binary_path`/`chromedriver_path`
   below.
1. Clones/updates the monorepo at `scripture_scraper_git_branch` into
   `scripture_scraper_config.app_root`, the same `github_token`-based
   auth every other app-deploying role here uses.
2. Installs Python 3.14 + dependencies via `uv sync --all-extras --dev`.
3. Clones/updates `scripture_scraper_config.archive_repo`
   (default `Spigushe/mtg_decklist_cache`) at `output_dir`, same
   `github_token`-based HTTPS auth as above — this is what makes
   `output_dir` a real git working tree the sweep wrapper script can
   commit/push from, not a plain directory (T1, 2026-08-08). Sets a local
   `user.name`/`user.email` on that clone (`archive_commit_name`/
   `archive_commit_email`) so the sweep's own commits have an identity.
4. Templates `scripture_scraper_config.scrape_script_path` (default
   `/usr/local/bin/<app_name>_scrape.sh`): runs
   `uv run scrape --source mtgo --output-dir ...` and
   `--source mtgtop8`, then — only on Sundays (UTC), alternating by ISO
   week parity — either
   `python -m barrins_scripture.scripts.top8_check_gaps` or
   `python -m barrins_scripture.scripts.mtgo_empty_decks`.
5. Templates a oneshot systemd service and a daily timer, both named
   `scripture_scraper_config.service_name` (default `<app_name>`, i.e.
   `<app_name>.service`/`.timer` — default 22:00 UTC ±30 min
   `RandomizedDelaySec`, `Persistent=true`). Basing the unit name on
   `app_name` (rather than a fixed `barrins_scripture`) is what lets
   `barrins_scripture.yml` run staging and production as fully
   independent, side-by-side instances instead of one shared install —
   see that playbook's `deploy_env`/`env_suffix` vars.
6. Deploys the local `.env` (`scripture_scraper_env_file`, if present —
   same "use it if available" pattern as `fastapi_backend_env_file`) to
   `{{ work_dir }}/.env`, mode `0600`. `SCRIPTURE_INGEST_TOKEN` is then
   injected into that same file by the playbook's own `post_tasks` (the
   `scripture_ingest_token` role), not carried in this local `.env` —
   see `barrins_scripture.yml`. Templates
   `scripture_scraper_config.sweep_script_path` (default
   `/usr/local/bin/<app_name>_sweep.sh`): commits and pushes any
   pending archive changes at `output_dir` (git add/commit/push, only if
   there's something to commit) *before* sourcing `.env`
   (`BARRINS_API_URL`/`SCRIPTURE_INGEST_TOKEN`) and running
   `uv run sweep --mode recent --days <sweep_days> --archive-dir ...`.
   Templates a oneshot systemd service and timer, both named
   `scripture_scraper_config.sweep_service_name` (default
   `<app_name>_sweep`, every 6 hours, `RandomizedDelaySec=900`,
   `Persistent=true`) — independent of the scrape timer above.

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `scripture_scraper_repo` | yes | / | `owner/repo` to clone (this monorepo). |
| `scripture_scraper_repo_subdir` | no | `''` | Subdirectory `apps/barrins_scripture` lives at within the repo. |
| `scripture_scraper_app_name` | yes | / | Used to name the checkout directory under `~/projects/`, and (derived config keys below) the systemd unit names and script paths. `barrins_scripture.yml` sets this to `barrins_scripture{{ env_suffix }}` so staging/production get distinct values. |
| `scripture_scraper_git_branch` | no | `main` | Branch to deploy from. |
| `scripture_scraper_output_dir` | no | `~/archives/<app_name>` | Where the JSON archive is written — deliberately outside `app_root`/`work_dir`, see the note below. |
| `scripture_scraper_daily_hour` | no | `22` | Hour (0-23, UTC) the daily scrape timer fires. |
| `scripture_scraper_github_token` | no | falls back to the shared `github_token` role | Only needed if a different token than the shared one is required. |
| `scripture_scraper_env_file` | no | `''` | Local, git-ignored path to a `.env` holding `BARRINS_API_URL` for the sweep (`SCRIPTURE_INGEST_TOKEN` is injected separately by the `scripture_ingest_token` role, not carried in this file) — see `secrets/barrins_scripture/{staging,production}.env.example`. `barrins_scripture.yml` picks which one via its own `deploy_env` var (default `staging`). Deployed to `{{ work_dir }}/.env` if present, skipped (with a note) otherwise. |
| `scripture_scraper_sweep_days` | no | `7` | Lookback window (days) the sweep's `--mode recent` rescans on every tick — mirrors `sweep.py`'s own `DEFAULT_RECENT_DAYS`. |
| `scripture_scraper_archive_repo` | no | `Spigushe/mtg_decklist_cache` | `owner/repo` the JSON archive is cloned from/pushed to at `output_dir`. |
| `scripture_scraper_archive_git_branch` | no | `main` | Branch the archive clone tracks and the sweep pushes to. |
| `scripture_scraper_archive_commit_name` | no | `Barrin's Scripture` | Git `user.name` set locally on the archive clone, used by the sweep's commits. |
| `scripture_scraper_archive_commit_email` | no | `scripture@barrins-codex.org` | Git `user.email` set locally on the archive clone, used by the sweep's commits. |
| `scripture_scraper_chrome_binary_path` | no | `/usr/bin/chromium` | Passed to the scrape service as `CHROME_BINARY_PATH`. Only needed if a host installs Chrome/Chromium somewhere other than Debian's standard apt path. |
| `scripture_scraper_chromedriver_path` | no | `/usr/bin/chromedriver` | Passed to the scrape service as `CHROMEDRIVER_PATH`. Same caveat as above. |

Derived (not settable directly — computed from `scripture_scraper_app_name` in `vars/main.yml`, exposed as `scripture_scraper_config.*`):

| Key | Default | Description |
| --- | --- | --- |
| `service_name` | `<app_name>` | Base name for the scrape service/timer (`<service_name>.service`/`.timer`). |
| `sweep_service_name` | `<app_name>_sweep` | Base name for the sweep service/timer. |
| `scrape_script_path` | `/usr/local/bin/<app_name>_scrape.sh` | Where the scrape wrapper script is deployed. |
| `sweep_script_path` | `/usr/local/bin/<app_name>_sweep.sh` | Where the sweep wrapper script is deployed. |
| `chrome_binary_path` | `/usr/bin/chromium` | Set as `CHROME_BINARY_PATH` on the scrape systemd service — see `barrins_scripture/utils/selenium_driver.py`. |
| `chromedriver_path` | `/usr/bin/chromedriver` | Set as `CHROMEDRIVER_PATH` on the scrape systemd service, same file. |

## Requirements

- `github_token` role must run first (provides the shared clone
  credential this role falls back to, for both the app repo and the
  archive repo).
- The `github_token` PAT must have **push**, not just read, access to
  `scripture_scraper_archive_repo` — the shared token was only ever used
  for `git clone`/`git pull` before this role's archive-push step; this
  is the first role in this repo to actually push with it. Verify this
  before relying on the sweep timer, e.g. `git -C <output_dir> push
  --dry-run`.
- `scripture_ingest_token` role should run before this one in the
  playbook's `roles:` list, and the playbook needs its own `post_tasks`
  step injecting `scripture_ingest_token` into the deployed `.env` — see
  `barrins_scripture.yml`. Without it, `.env` has no
  `SCRIPTURE_INGEST_TOKEN` and every sweep tick's ingestion POST fails
  with 401/503.
- `scripture_scraper_env_file` should point at a real, filled-in `.env`
  (for `BARRINS_API_URL`) before the sweep timer can succeed — without it
  the timer still gets installed and enabled, but every tick fails at
  `source .env` (missing file). See `secrets/README.md`.

## Validation

Per [`new-service-checklist.md`](../../../../docs/content/ops/deployment/new-service-checklist.md)
Step 0.3 — this service has no HTTP surface, so there is no `GET /health`
to poll:

- **Signal**: `systemctl status <service_name>.service` (last exit
  code) / `journalctl -u <service_name>.service -n 50` (a timer-driven
  job's equivalent of a health check) — `<service_name>` is
  `barrins_scripture` for production, `barrins_scripture-staging` for
  staging (see the derived-keys table above). Currently manual — see
  "Not automated yet" below.
- **Idempotency**: each scrape writes to a filename derived
  deterministically from the tournament URL/date
  (`save_tournament_scrape` in `barrins_scripture/utils/{mtgo,mtgtop8}.py`)
  and overwrites that path in place. Re-running the same day's scrape —
  a manual redeploy, or the timer's own `Persistent=true` catch-up run
  after a missed boot — does not duplicate archive files.

The sweep (T3/T8) has its own service/timer pair, checked the same way:

- **Signal**: `systemctl status <sweep_service_name>.service` /
  `journalctl -u <sweep_service_name>.service -n 50` (`barrins_scripture_sweep`
  for production, `barrins_scripture-staging_sweep` for staging). Same
  "manual for now" caveat as above.
- **Idempotency**: `barrins_api`'s ingestion route upserts on each table's
  natural key (T2), so a sweep tick re-posting an already-ingested file is
  a no-op, not a duplicate row — confirmed by
  `apps/barrins_api/tests/scripture/test_ingest.py::
  test_ingest_is_idempotent`. A failed tick (network error, `barrins_api`
  down/misconfigured, malformed JSON) is logged and skipped per-file, not
  retried within the run; the next scheduled tick (every 6h) picks it up.
  The wrapper script's own archive commit/push step (ahead of the sweep
  proper) is idempotent the same way: `git status --porcelain` gates
  `git add`/`commit`/`push`, so a tick with nothing new to archive does
  nothing and exits clean rather than creating an empty commit.

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
  it's an append-only, replayable record (§1.3 of the v2.0.0-bump plan),
  now pushed to `scripture_scraper_archive_repo` on every sweep tick.
  Rolling code back can at most overwrite that day's already-written
  files (see idempotency above); it never deletes prior history — and a
  bad write, once pushed, is a normal `git revert` on
  `scripture_scraper_archive_repo` if it ever needs undoing, not
  something this playbook automates.
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
real clone of `scripture_scraper_config.archive_repo`
(`Spigushe/mtg_decklist_cache` by default) — every sweep tick pushes any
new/changed archive files there (T1, 2026-08-07/08). A VPS disk failure
can now only lose whatever's been scraped since the *last sweep tick* (at
most the sweep timer's own 6-hour interval), not everything since the
last manual commit. The archive itself stays disposable/replayable in
principle regardless (it can be re-scraped from source tournaments).

**2026-08-09 incident**: a redeploy mid-backfill wiped the entire local
archive clone, not just the last sweep interval's worth. Root cause: the
app-repo clone task (above) runs `force: true`, and `output_dir` used to
live nested inside `app_root` (`<work_dir>/scraped`) — the force-clean
swept away the nested (git-ignored) archive clone, including everything
scraped since the last sweep push, before the archive-clone task even
ran. `output_dir` now defaults outside `app_root` entirely (`~/archives/
<app_name>`) so this class of hazard is structurally impossible — a
force-clean of the app repo cannot reach a directory it doesn't contain.

## Not automated yet

- **Backfilling `Spigushe/mtg_decklist_cache`'s history.** The repo this
  role now clones was created fresh, README-only (T1, 2026-08-07) — the
  historical archive that used to live in the (now-archived) old
  `mtg_decklist_cache` doesn't carry forward as-is (schema change). A
  from-scratch backfill (MTGO `--date-from`/`--date-to`, MTGTop8
  `--id-from`) is still an open, not-yet-run T1 task, separate from this
  role's own clone/push wiring. A first attempt on 2026-08-09 was lost
  mid-run to the `output_dir` nesting hazard above (see Data ownership &
  backup) before any sweep tick pushed it — restart from scratch once
  `output_dir`'s relocation is deployed.
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
