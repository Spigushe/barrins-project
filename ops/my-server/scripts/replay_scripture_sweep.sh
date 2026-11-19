#!/usr/bin/env bash
# Replays Barrin's Scripture's sweep (JSON archive -> barrins_api's
# POST /internal/scripture/ingest) over the last $DAYS days, from any host
# with git + uv — typically the production VPS over SSH.
#
# When to use it: recovering after an outage of the scheduled pipeline
# (.github/workflows/scripture-scrape.yml), once the missing tournaments
# are back in Spigushe/mtg_decklist_cache. The PREFERRED path is the
# workflow's own manual inputs (`gh workflow run scripture-scrape.yml
# -f mtgo=false -f mtgtop8=false -f gap_check=skip -f sweep_days=40`).
# This script is the fallback for when GitHub Actions itself is not an
# option (Actions outage, a broken SCRIPTURE_INGEST_TOKEN repo secret,
# a workflow change not merged yet...). See
# docs/content/service/barrins_scripture/incidents/2026-11-19-archive-push-token-expiry.md.
#
# It does NOT scrape anything — the VPS's outbound IP is blocked by
# mtgo.com (ADR-12, 2026-08-10 incident), so scraping stays on GitHub
# Actions or a personal machine. It only reads the archive and POSTs it.
#
# Self-contained and leaves nothing behind: it works in a fresh
# mktemp directory (removed on exit, unless KEEP_WORKDIR=true), does not
# use or touch any deployed checkout, systemd unit or .env, and needs no
# GitHub token (both repositories are public; clones are read-only):
#   - archive: shallow, blob-filtered, sparse clone restricted to the
#     YYYY/MM directories the --days window spans (the full archive is
#     ~370 MB) — the sweep selects files by their YYYY/MM/DD path, not by
#     mtime, so a fresh clone is fine;
#   - app: shallow sparse clone of apps/barrins_scripture on $BRANCH,
#     then `uv sync --frozen`.
#
# Idempotent: ingestion upserts by natural key, so re-sending tournaments
# that are already in bs_* is harmless — re-running with a wider window
# is always safe.
#
# Requires SCRIPTURE_INGEST_TOKEN for the target environment (production
# by default: ops/my-server/secrets/scripture/production_ingest_token.txt).
# If it is not already exported, it is prompted for without echo — never
# pass it on the command line (shell history, `ps`). Constitution §23.1/§34.
#
# Usage, from the repo root on your machine:
#   scp ops/my-server/scripts/replay_scripture_sweep.sh spigushe@146.59.146.57:~/
#   ssh -t spigushe@146.59.146.57 '~/replay_scripture_sweep.sh'
#
# Overrides (env vars):
#   DAYS=40                 sweep lookback in days (sweep --days)
#   BRANCH=staging          barrins-project branch to run the sweep code from
#   BARRINS_API_URL=...     target API (default: production)
#   UV=~/.local/bin/uv      uv binary
#   KEEP_WORKDIR=false      true keeps the temp dir for inspection
# Any extra arguments are appended to the sweep command, e.g.
#   ~/replay_scripture_sweep.sh --concurrency 2
#
# Exits non-zero if any file failed to ingest (sweep's own contract).
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
