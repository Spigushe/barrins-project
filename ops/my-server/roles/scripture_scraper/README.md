# scripture_scraper

Clones/updates `apps/barrins_scripture` from this monorepo, installs its
dependencies with `uv`, and schedules its daily MTGO + MTGTop8 scrape (plus
the Sunday-only biweekly gap-check) via a `systemd` `.service`/`.timer`
pair — this app has no HTTP-facing component, so unlike
`fastapi_backend`/`react_frontend` there's no domain/SSL/reverse-proxy
role involved, just a scheduled job.

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

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `scripture_scraper_repo` | yes | / | `owner/repo` to clone (this monorepo). |
| `scripture_scraper_repo_subdir` | no | `''` | Subdirectory `apps/barrins_scripture` lives at within the repo. |
| `scripture_scraper_app_name` | yes | / | Used to name the checkout directory under `~/projects/`. |
| `scripture_scraper_git_branch` | no | `main` | Branch to deploy from. |
| `scripture_scraper_output_dir` | no | `<work_dir>/scraped` | Where the JSON archive is written — see the note below. |
| `scripture_scraper_daily_hour` | no | `22` | Hour (0-23, UTC) the daily timer fires. |
| `scripture_scraper_github_token` | no | falls back to the shared `github_token` role | Only needed if a different token than the shared one is required. |

## Requirements

- `github_token` role must run first (provides the shared clone
  credential this role falls back to).

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

## Example

```yaml
- role: scripture_scraper
  tags: [scripture, deploy]
```

See `ops/my-server/barrins_scripture.yml` for how it's wired into this
repo.
