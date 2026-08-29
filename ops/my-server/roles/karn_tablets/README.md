# karn_tablets

Deploys the Karn Tablets clustering pipeline (`apps/karn_tablets`) as a
**VPS `systemd`-timer job** — a scheduled batch job with no inbound API
(T6, ADR-13), the same service shape as `scripture_scraper`. A daily
oneshot `.service`/`.timer` runs `karn-tablets --window <mode>`, which
reads `bs_*`/`mj_*` over a read-only DB credential, clusters that
window's Duel Commander decks into archetypes, and pushes each result to
`barrins_api`'s `POST /internal/karn/ingest` (`X-Karn-Token`).

Unlike `scripture_scraper` there is **no external scraping, no Chromium,
no JSON archive, no sweep** — DB in, HTTP out, nothing else. ADR-12's
move of the Scripture schedule to GitHub Actions was specific to
mtgo.com blocking this VPS's IP; it does not apply here.

## Step 0 answers (`docs/content/ops/deployment/new-service-checklist.md`)

1. **Trigger**: a `systemd` timer, daily at
   `karn_tablets_daily_hour` UTC (default `03:00`, `RandomizedDelaySec`
   30 min, `Persistent=true` so a missed run catches up). Daily because
   the rolling-30-day window shifts every day and `/trends` wants a
   steady run history (T8 cadence decision, 2026-08-28).
2. **HTTP surface**: none of its own. It makes outbound HTTPS calls to
   `BARRINS_API_URL` — no `register_ssl`/DNS/nginx steps. The three
   public read routes it feeds (`/bff/tolaria-news/{metagame,archetypes,
   trends}`) are served by `barrins_api` and already covered by that
   vhost's `location /bff/tolaria-news` rate-limit block
   (`backend_website` role) — nothing to add here.
3. **Validation**: `systemctl status {{ app_name }}.service` /
   `journalctl -u {{ app_name }}.service -n 50` for the timer-driven
   run, plus `GET /bff/tolaria-news/metagame` returning a `window` whose
   date matches the run as an application-level signal.
4. **Rollback**: no artifact of its own beyond the venv/checkout. Its
   output lives in `barrins_api`'s `kt_*` tables via idempotent,
   cross-run-stable ingestion; that data's rollback story belongs to
   `barrins_api`/`rollback.md`. To stop the job, disable the timer
   (`systemctl disable --now {{ app_name }}.timer`).
5. **Data ownership**: none. No new database — reads `bs_*`/`mj_*`
   (owned by `barrins_scripture`/`barrins_api`), writes only through the
   ingest API. No new backup/retention story.
6. **Release-tagged?** Follows `deploy_env`: production checks out the
   `main` branch by default (override `karn_tablets_git_branch`), staging
   the `staging` branch — the same convention `scripture_scraper` uses.
   `apps/karn_tablets` has no independent release tag.

## What it does

1. Clones/updates `karn_tablets_repo` (the monorepo) to
   `~/projects/<app_name>/` at `karn_tablets_git_branch` (`force: true`
   — this checkout owns nothing the job writes to). The whole repo is
   cloned so `apps/karn_tablets`'s `../../libs/dc_calendar` path dependency
   resolves, same as `scripture_scraper`.
2. Installs `uv`, Python 3.14, and runs `uv sync --all-extras --dev` in
   `apps/karn_tablets`.
3. Copies the local, git-ignored `karn_tablets_env_file` to
   `<work_dir>/.env` if it exists on the operator's machine (skipped
   with a note otherwise — same "use it if available" pattern as
   `fastapi_backend`). `karn_tablets.yml` then injects the shared
   `KARN_INGEST_TOKEN` into that file via a `post_tasks` step.
4. Templates `/usr/local/bin/<app_name>_run.sh` (sources `.env`, then
   `uv run karn-tablets --window <mode> --algorithm <algo>`), a oneshot
   `<app_name>.service` (`TimeoutStartSec=infinity`, `User=<username>`),
   and a daily `<app_name>.timer`.
5. Enables and starts the timer (`daemon_reload: true`).

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `karn_tablets_repo` | yes | — | `owner/name` of the repo to clone (the monorepo, e.g. `Spigushe/barrins-project`). |
| `karn_tablets_app_name` | yes | — | Base name for the `systemd` unit, checkout dir, and wrapper script — distinct per `deploy_env` for side-by-side installs. |
| `karn_tablets_repo_subdir` | no | `apps/karn_tablets` | Path within the repo holding the pipeline. |
| `karn_tablets_git_branch` | no | `main` | Branch to check out. |
| `karn_tablets_env_file` | no | `""` | Local path to the `.env` to deploy. Empty = never touch the server's `.env`. |
| `karn_tablets_daily_hour` | no | `3` | Hour (0–23, UTC) the daily timer fires. |
| `karn_tablets_window_mode` | no | `both` | `--window` value: `rolling_30d`, `banlist_period`, or `both`. |
| `karn_tablets_algorithm` | no | `kmeans` | `--algorithm` value: `kmeans`, `dbscan`, or `gmm`. |
| `karn_tablets_github_token` | no | `github_token` | PAT for the clone — defaults to the shared `github_token` fact. |

## Requirements

- The `github_token` role must run before this one (clone auth).
- The `karn_ingest_token` role must run before this one, and
  `karn_tablets.yml` injects `KARN_INGEST_TOKEN` into the deployed `.env`
  in `post_tasks` after this role copies it.
- A read-only Postgres role reachable as `KARN_TABLETS_DATABASE_URL_RO`
  must exist on the DB host — created **by hand**, like the `postgres`
  superuser password (`postgresql_pgadmin.yml`'s reminder). The exact
  `CREATE ROLE karn_tablets_ro … GRANT SELECT …` snippet is in
  `secrets/karn_tablets/{staging,production}.env.example` and
  `karn_tablets.yml`'s post-run reminder.
- `collections`: none beyond `ansible.builtin`.

## Example

```yaml
- role: karn_tablets
  tags: [karn]
  karn_tablets_repo: Spigushe/barrins-project
  karn_tablets_app_name: "karn_tablets{{ env_suffix }}"
  karn_tablets_git_branch: "{{ env_branch }}"
  karn_tablets_env_file: "{{ karn_tablets_env_file_path }}"
  karn_tablets_daily_hour: 3
```

See `karn_tablets.yml` for how it's wired in (staging/production
side-by-side via `deploy_env`, same as `barrins_scripture.yml`).
