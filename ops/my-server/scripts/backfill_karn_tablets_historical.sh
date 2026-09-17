#!/usr/bin/env bash
# Backfills historical Karn Tablets clustering windows by running the
# `karn-tablets` CLI once per completed historical banlist-period boundary
# between an earliest date and today, pushing BOTH window kinds per date
# (`--window both`) since `rolling_30d` and `banlist_period` both take the
# same `--date-to` reference.
#
# This is the "wrapper script iterating [all_time_periods]" flow
# roles/karn_tablets/README.md's "Backfilling historical windows" section
# describes as not built into the CLI itself. Run manually, once, after a
# deploy/cutover -- never scheduled, never invoked by the systemd timer.
#
# Run ON the target host (production or staging), inside the deployed
# checkout -- not from a local repo clone -- since it needs the deployed
# `.env` (BARRINS_API_URL/KARN_INGEST_TOKEN/KARN_TABLETS_DATABASE_URL_RO)
# and the `uv`-managed venv the karn_tablets role already set up there.
#
# Usage (as the deploy user, e.g. spigushe):
#   cd ~/projects/<app_name>/apps/karn_tablets
#   ~/backfill_karn_tablets_historical.sh                  # EARLIEST defaults to 2024-07-01
#   EARLIEST=2024-01-01 ~/backfill_karn_tablets_historical.sh
#
# The still-in-progress current banlist period (the one containing today,
# whose `date_to` can be a future date) is deliberately excluded: it has
# no complete tournament history yet, and the daily timer -- plus the
# one-shot run `karn_tablets.yml` fires immediately on a production
# cutover -- already covers it. Only periods whose `date_to` has already
# passed (or is today) are backfilled here.
#
# `generated_at` on every pushed run is real wall-clock time regardless of
# `--date-to` (`ingest_run`'s own idempotency contract -- see
# roles/karn_tablets/README.md); only the window's date range is
# backdated, so re-running this script is a safe, idempotent no-op for
# any date that already succeeded.
#
# Continues past a single date's failure (mirrors `karn-tablets` itself
# never raising past `main()` for one window's failure) -- prints a final
# summary and exits non-zero if ANY date failed, so a caller can tell.
set -uo pipefail

EARLIEST="${EARLIEST:-2024-07-01}"
UV="${UV:-$HOME/.local/bin/uv}"

if [ ! -f pyproject.toml ] || [ ! -f karn_tablets/__main__.py ]; then
  echo "Run this from the apps/karn_tablets checkout directory (pyproject.toml / karn_tablets/__main__.py not found here)." >&2
  exit 1
fi

echo "Computing completed banlist-period boundaries from $EARLIEST through today..."
DATES=$("$UV" run python -c "
from datetime import date
from dc_calendar.windowing import all_time_periods

earliest = date.fromisoformat('$EARLIEST')
today = date.today()
for window in all_time_periods(earliest, today):
    if window.date_to <= today:
        print(window.date_to.isoformat())
")

if [ -z "$DATES" ]; then
  echo "No completed periods resolved between $EARLIEST and today -- nothing to backfill." >&2
  exit 1
fi

echo "Completed periods to backfill (one --window both run per date-to):"
echo "$DATES"
echo

FAILED=()
for d in $DATES; do
  echo "=== $d ==="
  if "$UV" run karn-tablets --window both --date-to "$d"; then
    echo "OK: $d"
  else
    echo "FAILED: $d" >&2
    FAILED+=("$d")
  fi
  echo
done

if [ "${#FAILED[@]}" -gt 0 ]; then
  echo "Backfill finished with ${#FAILED[@]} failed date(s): ${FAILED[*]}" >&2
  exit 1
fi

echo "Backfill finished -- all dates succeeded."
