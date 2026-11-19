#!/usr/bin/env bash
# Refreshes staging's bs_* reference data from production, then prunes it
# back down to a 90-day retention window, so a staging karn_tablets.yml
# run has realistic, current-but-bounded data to cluster (see
# apps/karn_tablets/karn_tablets/extract.py for the tables it reads).
#
# Does NOT touch mj_sets/mj_cards -- those are refreshed on staging via
# its own MTGJSON import (POST /api/v1/mtgjson/import, X-MTGJSON-Import-
# Token), which is the authoritative way to update them there. Copying
# them from production here would overwrite that with production's data,
# which is also a few migrations behind staging's schema (missing
# mj_cards.legalities entirely as of this writing).
#
# Step 1 (sync): copies bs_tournaments/bs_decks/bs_deck_cards/bs_rounds/
# bs_round_matches/bs_standings from production into staging. Read-only
# against production; only ever writes to the *_staging database.
# Destructive on the staging side: TRUNCATE TABLE bs_tournaments CASCADE
# also cascades to bs_rounds/bs_round_matches/bs_standings (not just
# bs_decks/bs_deck_cards) -- all of bs_tournaments' children go with it,
# so this resyncs all of them, not just the ones Karn Tablets itself
# reads.
#
# Uses psql \copy rather than pg_dump: this VPS runs PostgreSQL 15, and a
# newer local pg_dump (16/17+) emits a session-setup GUC
# (transaction_timeout) that PG15 rejects, aborting the dump. \copy is a
# plain client-side COPY with no version-specific preamble, so it's immune
# to that mismatch.
#
# Step 2 (prune): deletes bs_tournaments rows (and everything that
# cascades from them -- all FK'd ON DELETE CASCADE, see
# apps/barrins_api/app/models/scripture.py) older than 90 days, on staging
# only. This is a genuine, permanent DELETE -- not the archival pattern in
# Constitution Sec.11.8, which only governs user-triggered deletes inside
# the app itself; this is an ops maintenance step, and never touches
# production. Nothing outside the bs_* family has a foreign key into
# bs_decks or bs_tournaments (checked against app/models/*.py), so this
# cascade is self-contained -- no ts_*/kt_* rows are affected.
#
# STAGING ONLY throughout -- never run this against production.
#
# Requires: psql able to reach the VPS's Postgres on 5432, and PGPASSWORD
# set in the environment (never hardcode it here -- Constitution Sec.34).
#
# To redo this later, from the repo root in PowerShell (Git Bash invoked
# explicitly -- plain `bash` on PATH may resolve to the WSL launcher,
# which won't see $env: vars or have psql):
#
#   $env:PGPASSWORD = '<staging DB password>'
#   & "C:\Program Files\Git\bin\bash.exe" ops/my-server/scripts/refresh_karn_tablets_data_staging.sh
#
# or from bash directly:
#
#   PGPASSWORD='<staging DB password>' ops/my-server/scripts/refresh_karn_tablets_data_staging.sh

set -euo pipefail

HOST="146.59.146.57"
PGUSER="spigushe"
PROD_DB="barrins_api"
STAGING_DB="barrins_api_staging"
RETENTION_DAYS=90

if [ -z "${PGPASSWORD:-}" ]; then
  echo "PGPASSWORD must be set in the environment." >&2
  exit 1
fi

# --- Step 1: sync fresh data from production -------------------------------

# Parent-first order so each table's FK targets already exist by the time
# it's restored. mj_sets/mj_cards deliberately excluded -- see header note.
TABLES=(bs_tournaments bs_decks bs_deck_cards bs_rounds bs_round_matches bs_standings)

echo "[1/2] Truncating staging copies (bs_tournaments CASCADE covers everything below)..."
psql -h "$HOST" -U "$PGUSER" -d "$STAGING_DB" -v ON_ERROR_STOP=1 -c \
  "TRUNCATE TABLE bs_tournaments RESTART IDENTITY CASCADE;"

for t in "${TABLES[@]}"; do
  echo "Syncing $t..."
  psql -h "$HOST" -U "$PGUSER" -d "$PROD_DB" -v ON_ERROR_STOP=1 -c "\\copy $t TO STDOUT" \
    | psql -h "$HOST" -U "$PGUSER" -d "$STAGING_DB" -v ON_ERROR_STOP=1 -c "\\copy $t FROM STDIN"
done

# --- Step 2: prune anything older than the retention window -----------------

echo "[2/2] Deleting bs_tournaments older than $RETENTION_DAYS days (cascades to children)..."
psql -h "$HOST" -U "$PGUSER" -d "$STAGING_DB" -v ON_ERROR_STOP=1 -c \
  "DELETE FROM bs_tournaments WHERE date < CURRENT_DATE - INTERVAL '$RETENTION_DAYS days';"

echo "Done. Row counts:"
psql -h "$HOST" -U "$PGUSER" -d "$STAGING_DB" -c "
SELECT 'bs_tournaments' AS table, count(*) FROM bs_tournaments
UNION ALL SELECT 'bs_decks', count(*) FROM bs_decks
UNION ALL SELECT 'bs_deck_cards', count(*) FROM bs_deck_cards
UNION ALL SELECT 'bs_rounds', count(*) FROM bs_rounds
UNION ALL SELECT 'bs_round_matches', count(*) FROM bs_round_matches
UNION ALL SELECT 'bs_standings', count(*) FROM bs_standings;
"
