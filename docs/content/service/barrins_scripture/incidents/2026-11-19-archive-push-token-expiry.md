# Incident: expired ARCHIVE_PUSH_TOKEN stopped Scripture for 32 days

## Status tracking

| Field | Value |
| --- | --- |
| Status | Mitigated: secret rotated on 2026-11-19 and the pipeline runs again; backlog recovery still in progress (see [Recovery checklist](#recovery-checklist)) |
| Severity | High: zero tournaments (MTGO and MTGTop8) archived or ingested into production for 32 days, so `bs_*`, Karn Tablets and Tolaria News `/metagame` all went stale |
| Reported | 2026-11-19 (user noticed production data had not been refreshed for 33 days) |
| Introduced | 2026-10-18 (first failed run; the PAT stored on 2026-09-18 reached its expiry) |
| Resolved | Not yet, pending the recovery checklist |
| Area | `.github/workflows/scripture-scrape.yml`, the `ARCHIVE_PUSH_TOKEN` repository secret |
| Blocking | Every scheduled and manual run of `scripture-scrape`, all legs (scrape, push, sweep) |
| Owner | DevOps (Agent 3), with Barrin's Scripture (Agent 1) for the recovery runs |

## Summary

Every nightly `scripture-scrape` run failed from 2026-10-18 to 2026-11-19
(32 runs in a row) at its second step, `Checkout the JSON archive
(Spigushe/mtg_decklist_cache)`, with:

```text
##[error]Bad credentials - https://docs.github.com/rest
```

Every later step (MTGO scrape, MTGTop8 scrape, gap-check, archive push,
sweep) was skipped. Nothing new reached `Spigushe/mtg_decklist_cache`
(last archive commit `a4cc058`, 2026-10-17T23:45:10Z) and nothing new
reached production `bs_*`. Karn Tablets kept clustering every day, but
always on the same frozen data.

## Timeline (UTC)

| When | What |
| --- | --- |
| 2026-09-18 07:23 | `ARCHIVE_PUSH_TOKEN` repository secret last updated, during the [2026-09-18 incident](./2026-09-18-mtgtop8-explain-deck-500.md) work |
| 2026-10-17 23:35 | Last successful run ([39079627502](https://github.com/Spigushe/barrins-project/actions/runs/39079627502)), archive commit `a4cc058` |
| 2026-10-18 23:46 | First failed run ([39177887076](https://github.com/Spigushe/barrins-project/actions/runs/39177887076)): `Bad credentials` on the archive checkout |
| 2026-10-18 → 2026-11-19 | 32 consecutive failed scheduled runs, about 40 s each, all with the same error |
| 2026-11-19 | Reported, diagnosed from the run logs, PAT regenerated and secret updated by the repository owner |
| 2026-11-19 12:38 | First manual run with the new secret started |

## Root cause

`ARCHIVE_PUSH_TOKEN` is a personal access token (PAT) with push access to
`Spigushe/mtg_decklist_cache`. The secret was stored on 2026-09-18 and the
failures start exactly 30 days later, which matches a PAT created with
the default 30-day expiry. `Bad credentials` is what GitHub answers for an
expired token. The expiry date itself was not recorded anywhere, so
this is inferred from the dates, not read from the token settings.

The archive checkout is the first step that needs the token, and it runs
before any scraping. So an expired token does not only block the push:
it stops the whole pipeline, including the sweep, which by itself only
needs `SCRIPTURE_INGEST_TOKEN`.

## Why this stayed invisible for a month

- The workflow itself failed loudly (red runs, about 40 s each), but
  nobody looked. ADR-12 relies on GitHub's default "failed scheduled
  workflow" email as the only alert, and those emails were not noticed.
  The notification settings
  (<https://github.com/settings/notifications>, Actions section) should
  be checked.
- Nothing watches data freshness downstream. `barrins_api`, Karn Tablets
  and Tolaria News all kept serving the last ingested data without any
  warning: a Karn Tablets run on stale data is still a successful run.
- The PAT's expiry date was not written down anywhere (no ADR, no
  secrets README, no calendar reminder).

## Impact

- MTGO and MTGTop8 tournaments from 2026-10-18 to 2026-11-19 are missing
  from the JSON archive and from production `bs_*` until the recovery
  below is done.
- Karn Tablets' `rolling_30d` window has been computed on an empty or
  shrinking set of recent tournaments since mid-November, and Tolaria
  News `/metagame` / `/archetypes` showed that stale result.
- No data was lost: the sources (mtgo.com, mtgtop8.com) still serve the
  missed tournaments, and ingestion upserts by natural key, so replaying
  is safe.

## Resolution

### 1. Rotate the secret (done 2026-11-19)

The repository owner generated a new PAT and updated the secret
(`gh secret set ARCHIVE_PUSH_TOKEN`). The 12:38 UTC manual run got past
the archive checkout.

Recommended for the next rotation: a fine-grained PAT restricted to
`Spigushe/mtg_decklist_cache` with only "Contents: read and write", an
explicit expiry date written in the [follow-ups](#follow-ups) table, and a
calendar reminder a week before it.

### 2. Make the workflow usable for recovery

A default run cannot catch up a gap this long: the MTGO window is the
month of "5 days ago" through the current month, MTGTop8 inspects 1000
ids after the last archived one, and the sweep only looks 7 days back.

`scripture-scrape.yml` now takes `workflow_dispatch` inputs. Each leg can
be switched off on its own, and each leg's CLI arguments can be set from
the run form or from `gh`. A scheduled run ignores them and behaves as
before.

| Input | Default | Effect |
| --- | --- | --- |
| `mtgo` | `true` | Run the MTGO scrape |
| `mtgo_date_from` / `mtgo_date_to` | empty | `--date-from` / `--date-to`, format `YYYY-MM` |
| `mtgo_force` | `false` | `--force-mtgo` (re-scrape tournaments already archived) |
| `mtgtop8` | `true` | Run the MTGTop8 scrape |
| `mtgtop8_id_from` | empty | `--id-from` (empty: resume after the last archived id) |
| `mtgtop8_span` | empty | `--span` (empty: 1000) |
| `gap_check` | `auto` | `auto` (Sunday parity), `skip`, `top8_check_gaps`, `mtgo_empty_decks` |
| `sweep` | `true` | Run the sweep (ingest into production) |
| `sweep_mode` | `recent` | `recent` or `full` |
| `sweep_days` | empty | `--days` for `recent` (empty: 7) |
| `sweep_fast_forward` | `false` | `--fast-forward`, `full` mode only |

All inputs are validated in a first "Resolve run parameters" step, before
any checkout, so a typo fails in seconds. That step also writes the
resolved parameters to the run summary, so every recovery run documents
itself.

### 3. Recover the backlog

Run these from a machine with `gh` authenticated on the repository, once
the workflow change above is on `staging`. Wait for each run to finish
before starting the next one: they push to the same archive branch (the
workflow's `concurrency` group queues them anyway).

```bash
# a) Normal run: November MTGO, MTGTop8 from the last archived id (+1000),
#    7-day sweep. The 12:38 UTC run on 2026-11-19 already did this.
gh workflow run scripture-scrape.yml
gh run watch

# b) MTGTop8 only, repeated until mtgtop8.com/<year>/<month>/ in the
#    archive reaches today. Each run resumes where the previous one stopped.
gh workflow run scripture-scrape.yml \
  -f mtgo=false -f gap_check=skip -f sweep=false

# c) October MTGO (the default window no longer covers it), then ingest
#    the whole gap: 40 days back from 2026-11-19 covers 2026-10-10 onward.
gh workflow run scripture-scrape.yml \
  -f mtgtop8=false -f mtgo_date_from=2026-10 -f mtgo_date_to=2026-10 \
  -f gap_check=skip -f sweep_days=40
```

Step c's sweep ingests everything the earlier runs archived, so no
separate sweep run is needed. If the sweep cannot run from GitHub Actions
(Actions outage, a broken `SCRIPTURE_INGEST_TOKEN` repository secret...),
use the replay script below from the VPS instead.

Then refresh the clustering on the VPS without waiting for the daily
timer:

```bash
ssh spigushe@146.59.146.57
sudo systemctl start karn_tablets.service
journalctl -u karn_tablets.service -f
```

### 4. Replay script: sweep from the VPS

Fallback for step 3's sweep. It reads the public archive and POSTs it to
`POST /internal/scripture/ingest`. It does **not** scrape: the VPS's IP is
blocked by mtgo.com ([2026-08-10 incident](./2026-08-10-mtgo-network-block.md),
ADR-12), so scraping stays on GitHub Actions or a personal machine.

The canonical file is
[`ops/my-server/scripts/replay_scripture_sweep.sh`](https://github.com/Spigushe/barrins-project/blob/staging/ops/my-server/scripts/replay_scripture_sweep.sh).
The copy below is kept so the procedure can be read and replayed from
this page alone. If the two ever differ, the file wins.

How to run it, from the repository root:

```bash
scp ops/my-server/scripts/replay_scripture_sweep.sh spigushe@146.59.146.57:~/
ssh -t spigushe@146.59.146.57 '~/replay_scripture_sweep.sh'
# wider window, kept work dir, progress bar:
ssh -t spigushe@146.59.146.57 \
  'DAYS=60 KEEP_WORKDIR=true ~/replay_scripture_sweep.sh --progress'
```

It asks for the production `SCRIPTURE_INGEST_TOKEN` without echo (value in
`ops/my-server/secrets/scripture/production_ingest_token.txt`, same as the
repository secret). What it does:

1. Shallow, sparse clone of `Spigushe/mtg_decklist_cache`, restricted to
   the `YYYY/MM` folders the `DAYS` window covers (the full archive is
   about 370 MB). The sweep picks files by their `YYYY/MM/DD` path, not by
   modification time, so a fresh clone is fine.
2. Shallow, sparse clone of `apps/barrins_scripture` from `staging`, then
   `uv sync --frozen`.
3. `sweep --mode recent --days $DAYS` against production.

It runs in a temporary directory removed on exit, touches no deployed
checkout, systemd unit or `.env`, and needs no GitHub token. Re-running it
is safe (idempotent upserts). It exits non-zero if any file failed to
ingest.

Tested on 2026-11-19 with a stubbed `uv run`: both clones and the
dependency install work, and the sparse clone of `2026/10` and `2026/11`
holds 888 files.

```bash
#!/usr/bin/env bash
# Copy of ops/my-server/scripts/replay_scripture_sweep.sh, header comment omitted.
set -euo pipefail

DAYS="${DAYS:-40}"
BRANCH="${BRANCH:-staging}"
BARRINS_API_URL="${BARRINS_API_URL:-https://api.barrins-codex.org}"
UV="${UV:-$HOME/.local/bin/uv}"
KEEP_WORKDIR="${KEEP_WORKDIR:-false}"
ARCHIVE_REPO="https://github.com/Spigushe/mtg_decklist_cache.git"
APP_REPO="https://github.com/Spigushe/barrins-project.git"

if ! [[ "$DAYS" =~ ^[1-9][0-9]*$ ]]; then
  echo "DAYS must be a positive integer, got '$DAYS'." >&2
  exit 1
fi
if [ ! -x "$UV" ]; then
  echo "uv not found at $UV (set UV=/path/to/uv)." >&2
  exit 1
fi
command -v git >/dev/null || { echo "git is required." >&2; exit 1; }

if [ -z "${SCRIPTURE_INGEST_TOKEN:-}" ]; then
  read -rsp "SCRIPTURE_INGEST_TOKEN for $BARRINS_API_URL: " SCRIPTURE_INGEST_TOKEN
  echo
fi
if [ -z "$SCRIPTURE_INGEST_TOKEN" ]; then
  echo "SCRIPTURE_INGEST_TOKEN is empty." >&2
  exit 1
fi
export SCRIPTURE_INGEST_TOKEN BARRINS_API_URL

WORK="$(mktemp -d "$HOME/scripture-replay.XXXXXX")"
cleanup() {
  if [ "$KEEP_WORKDIR" = "true" ]; then
    echo "Kept work dir: $WORK"
  else
    rm -rf "$WORK"
  fi
}
trap cleanup EXIT

# Every YYYY/MM the [today - DAYS, today] window touches, for both sources.
SPARSE=()
month="$(date -u -d "-$DAYS days" +%Y-%m-01)"
last="$(date -u +%Y-%m-01)"
while [[ ! "$month" > "$last" ]]; do
  ym="$(date -u -d "$month" +%Y/%m)"
  SPARSE+=("mtgo.com/$ym" "mtgtop8.com/$ym")
  month="$(date -u -d "$month +1 month" +%Y-%m-01)"
done

echo "[1/3] Cloning the archive (${SPARSE[*]})..."
git clone --quiet --depth 1 --filter=blob:none --sparse "$ARCHIVE_REPO" "$WORK/archive"
git -C "$WORK/archive" sparse-checkout set "${SPARSE[@]}"
echo "      archive HEAD: $(git -C "$WORK/archive" log -1 --format='%h %cI %s')"

echo "[2/3] Cloning apps/barrins_scripture from $BRANCH and installing deps..."
git clone --quiet --depth 1 --branch "$BRANCH" --filter=blob:none --sparse \
  "$APP_REPO" "$WORK/app"
git -C "$WORK/app" sparse-checkout set apps/barrins_scripture
cd "$WORK/app/apps/barrins_scripture"
"$UV" sync --frozen --quiet

echo "[3/3] Sweeping the last $DAYS days into $BARRINS_API_URL..."
"$UV" run --frozen sweep --mode recent --days "$DAYS" \
  --archive-dir "$WORK/archive" "$@"
```

## Recovery checklist

- [x] New PAT generated, `ARCHIVE_PUSH_TOKEN` updated (2026-11-19)
- [x] `scripture-scrape.yml` recovery inputs + `replay_scripture_sweep.sh` written
- [ ] Workflow change merged to `staging`
- [ ] Step 3a run green (normal run with the new secret)
- [ ] Step 3b repeated until MTGTop8 reaches today
- [ ] Step 3c run green (October MTGO + 40-day sweep)
- [ ] Karn Tablets re-run on the VPS
- [ ] Verified: latest `bs_tournaments.date` in production is within the
      last few days, and Tolaria News `/metagame` shows recent tournaments

## Follow-ups

| Item | Status |
| --- | --- |
| Record the new PAT's expiry date here and set a calendar reminder a week before | Open (owner to fill in: expiry `YYYY-MM-DD`) |
| Consider replacing the PAT with a write-enabled deploy key on `Spigushe/mtg_decklist_cache` (`actions/checkout`'s `ssh-key` input): scoped to one repository and does not expire. Needs a decision (ADR-12 addendum) | Open |
| Check GitHub notification settings so failed scheduled runs actually reach the owner | Open |
| Data-freshness alert (for example, flag when the newest `bs_tournaments.date` is more than N days old), so a silent stop is caught downstream as well | Open, needs a design decision |
| `ops/my-server/secrets/github/token.txt` holds the same PAT for the VPS `github_token` role: check whether that role still needs it and update or retire it | Open |
| GitHub disables `schedule` triggers on a public repository after 60 days without activity on that repository (the archive pushes go to another repository and do not count). `barrins-project`'s last commit before this incident was 2026-09-19 | Watch: any merge to `staging` resets the counter |
| Wrong comment in `scripture-scrape.yml` pointing `SCRIPTURE_INGEST_TOKEN` at the staging token file while the workflow targets production | Fixed with the workflow change |

## See also

- `.github/workflows/scripture-scrape.yml`
- `ops/my-server/scripts/replay_scripture_sweep.sh`
- `apps/barrins_scripture/barrins_scripture/__main__.py` (scrape arguments)
- `apps/barrins_scripture/barrins_scripture/sweep.py` (sweep arguments)
- `docs/content/ops/architecture/decisions.md` (ADR-12)
- [2026-09-18 incident](./2026-09-18-mtgtop8-explain-deck-500.md)
- [2026-08-10 incident](./2026-08-10-mtgo-network-block.md)
