# postgres_backup

Daily `pg_dump`/`pg_dumpall` backups of every database on the host's
PostgreSQL instance, via a systemd timer. Closes Constitution §36 (backup
\+ verified restore procedure) — the most significant pre-existing
operations gap, tracked in `docs/content/ops/operations/index.md`.

Local backups on the same host, not offsite storage — offsite (S3/
Backblaze/etc.) would add a new external dependency and credentials
(§22) for a single-VPS setup with no second site to protect yet, so it's
recorded as a tracked future improvement instead of built now.

## What it does

1. Creates `postgres_backup_dir` (default `/var/backups/postgresql`),
   owned by the `postgres` OS user, mode `0700` — only `postgres`/`root`
   can read the dumps (they can contain user data, e.g. password hashes).
2. Templates `/usr/local/bin/postgres_backup.sh`: for every database in
   `postgres_backup_databases`, runs `pg_dump --format=custom` into a
   timestamped file; separately runs `pg_dumpall --globals-only` for
   roles/grants (not part of any single database dump). `umask 077` so
   every created file is `0600` by construction, not a follow-up `chmod`.
   Deletes anything older than `postgres_backup_retention_days` (default
   3) at the end of each run — this step is not gated behind a successful
   dump (no `set -e`): a single failed `pg_dump` still lets cleanup run,
   so a bad day doesn't compound into a full disk (see the 2026-08-15
   incident in `docs/content/ops/operations/index.md`).
3. Templates a oneshot systemd service (`postgres_backup.service`,
   `User=postgres` — connects via local peer authentication, no password
   needed, nothing new to keep secret) and a daily timer
   (`postgres_backup.timer`, default 03:00 ± up to 30 min
   `RandomizedDelaySec`, `Persistent=true` so a missed run — e.g. host
   was off — catches up on next boot).

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `postgres_backup_dir` | no | `/var/backups/postgresql` | Where dumps are written. |
| `postgres_backup_databases` | no | `[barrins_api, barrins_api_dev, postgres, tabriz_assembly]` | Explicit allowlist of databases to dump — deliberately not "every database on the instance" (see incident note below). |
| `postgres_backup_retention_days` | no | `3` | Dumps older than this are deleted on each run. |
| `postgres_backup_hour` | no | `3` | Hour (0-23, host local time) the daily timer fires. |

## 2026-08-15 incident

The original version of this role dumped every non-template database
unconditionally and kept 14 days of history. That silently included
throwaway/test/dev databases alongside the real ones, and one of them
(`barrins_db`, ~1.6-1.7GB/day) alone accounted for the majority of a 26G
backup set that filled the host's disk, crashed PostgreSQL, and took
down both `api` and `api-staging` (503s on both). The `set -e` in the
backup script also meant that day's `pg_dump` failure (itself caused by
the full disk) skipped the retention cleanup that would otherwise have
reclaimed space — compounding the failure instead of self-healing.
Fixed by switching to an explicit database allowlist, shortening default
retention to 3 days, and removing `set -e` so cleanup always runs.

## Requirements

- `setup_packages` must have run first (installs `postgresql`).

## Not automated

- **No offsite copy.** These backups protect against data-loss bugs
  (a bad migration, an accidental delete) but not against the VPS itself
  being lost — see "What it does" above for why that's deferred rather
  than silently skipped.
- **Restoring is a manual, deliberate action** — this role only takes
  backups, it never restores one automatically (that should never happen
  without a human deciding to do it). See
  `docs/content/ops/deployment/backup.md` for the restore procedure.

## Example

```yaml
- role: postgres_backup
  tags: [backup, deploy]
```

No required variables — every default is safe to run as-is. See
`postgresql_pgadmin.yml` for how it's wired into this repo (alongside
`pgadmin`, since backups are host-level infrastructure like pgAdmin, not
a per-app release-tagged deploy).
