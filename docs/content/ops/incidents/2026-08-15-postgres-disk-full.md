# Incident: Backup retention filled the disk, took down PostgreSQL (prod + staging)

## Status tracking

| Field | Value |
| --- | --- |
| Status | Resolved — service restored, backup-policy fix deployed; network-hardening follow-up intentionally deferred to the v2.0.0 release (see below) |
| Severity | Critical — both production and staging fully down (503 on every request) |
| Reported | 2026-08-15, ~08:00 UTC (503s observed on both environments) |
| Resolved | 2026-08-15 08:24:14 UTC (both `/health` endpoints back to 200) |
| Area | Infrastructure — shared PostgreSQL instance on `146.59.146.57`, `postgres_backup` Ansible role |
| Blocking | Every `barrins_api` request, both environments (they share one host and one Postgres instance) |
| Owner | Infrastructure (Agent 3) |

## Summary

Both `api.barrins-codex.org` and `api-staging.barrins-codex.org` were
returning 503 on every request. Root cause: `/var/backups/postgresql/`
had grown to 26G — the `postgres_backup` role dumped *every* non-template
database on the instance daily with 14-day retention, and one database
(`barrins_db`, ~1.6-1.7GB per dump) alone accounted for the bulk of it.
The host's 74G disk filled to 100% (355M free), PostgreSQL crashed when
it could no longer write WAL/checkpoint data, and every subsequent
restart attempt failed because it couldn't even write its own lock file.

Both backend services (`api`, `api-staging`) stayed up throughout — they
were healthy processes failing every request with
`ConnectionRefusedError: [Errno 111] Connect call failed ('146.59.146.57', 5432)`
— confirming the outage was the shared database, not either
application.

## Timeline

1. **~08:00** — 503s reported on both environments.
2. **08:00-08:12** — `df -h /` showed `/` at 100% (355M free of 74G);
   `free -h`/`uptime` ruled out OOM or a general host problem.
   `du -xh --max-depth=2 /var` isolated `/var/backups/postgresql` at 26G.
3. **08:12-08:18** — `ls -lat` + `journalctl -u postgres_backup.service`
   showed daily backups succeeding every night from 2026-07-31 through
   2026-08-14, then failing at 2026-08-15 03:27 with
   `pg_dump: error: could not write to output file: No space left on device`.
   Per-database sizing showed `barrins_db` (~1.6-1.7GB/dump × ~15 days
   retained) as the dominant contributor, not a single runaway file.
4. **Immediate mitigation**: `sudo find /var/backups/postgresql -type f -mtime +5 -delete`
   freed ~17G (74G disk: 355M → 17G free).
5. **`postgresql-15-main.log` review** (no corruption found):
   - 2026-08-15 03:27:14 — the backup's `pg_dump` COPY on `barrins_db`
     was cut off by the full disk, which crashed the whole cluster
     (`all server processes terminated; reinitializing`). WAL replay on
     restart completed cleanly (`redo done`, no errors) and the cluster
     came back up at 03:27:37 — ran normally for ~3 hours.
   - 2026-08-15 06:29:57 — a **fast shutdown request** was issued
     (a deliberate stop, not a crash — source not yet identified, see
     Open items). The shutdown itself hit the still-full disk while
     checkpointing: `PANIC: could not write to file
     "pg_logical/replorigin_checkpoint.tmp": No space left on device`.
   - Every restart from 06:30 to 08:18 failed at
     `FATAL: could not write lock file "postmaster.pid": No space left on device`
     — simply out of room to write a few bytes.
6. **08:18** — `sudo systemctl start postgresql` succeeded once space was
   freed; `pg_lsclusters` confirmed `15/main` back `online`, listening on
   5432.
7. **08:24:14** — both `api` and `api-staging` `/health` returned 200;
   journal logs on both showed clean DB connections with no further
   errors.

## Root cause

Two compounding issues in the `postgres_backup` Ansible role
(`ops/my-server/roles/postgres_backup/`):

1. **Unbounded scope**: the backup script dumped every non-template
   database returned by
   `SELECT datname FROM pg_database WHERE NOT datistemplate` — including
   throwaway/test/dev databases never meant to carry 14 days of full
   daily backups. `barrins_db` alone (~1.6-1.7GB/dump) made up the
   majority of the 26G.
2. **`set -euo pipefail` in the backup script**: when today's `pg_dump`
   failed (disk full), the script exited immediately and never reached
   the `find "$BACKUP_DIR" -type f -mtime "+${RETENTION_DAYS}" -delete`
   cleanup line — so the one day cleanup was needed most, it didn't run,
   removing any chance of self-healing.

Neither issue alone would necessarily have caused an outage this fast;
together, unbounded growth eventually hit the disk ceiling, and the
failure mode itself disabled the mechanism that would have recovered
from it.

## Fix

`ops/my-server/roles/postgres_backup/`:

- **Explicit database allowlist** (`postgres_backup_databases`, default
  `[barrins_api, barrins_api_dev, postgres, tabriz_assembly]`) replaces
  "every non-template database."
- **Retention lowered** from 14 to 3 days (`postgres_backup_retention_days`).
- **Removed `set -e`** from the backup script; each `pg_dump`/`pg_dumpall`
  failure is now caught individually (script still exits non-zero if any
  failed, so the systemd unit still reports failure), but the retention
  `find ... -delete` now always runs regardless.

Full detail: `ops/my-server/roles/postgres_backup/README.md`.

## Follow-up: network exposure remediation

Same session, discovered while pruning backups. `postgresql.conf` had
`listen_addresses = '*'` and `pg_hba.conf` had
`host all all 0.0.0.0/0 md5` — Postgres accepting password auth from the
entire internet, with the log showing repeated
`password authentication failed for user "postgres"` attempts every
1-2 minutes plus port-scanner noise, consistent with an ongoing
brute-force/scan. Root cause: both `barrins_api`'s `production.env` and
`staging.env` had `DATABASE_URL` pointing at the server's **public IP**
(`146.59.146.57`) rather than `localhost`, even though the app and
Postgres run on the same host — the wide-open rule existed to let the
app reach itself over the public interface. Confirmed no other client
needs remote access (pgAdmin's web UI already uses its own
Docker-subnet-scoped rule; no external psql/GUI client in use anymore).

Full fix agreed: switch `DATABASE_URL` to `localhost` in both
environments, verify connectivity, then remove the `0.0.0.0/0` rule and
narrow `listen_addresses`.

- **Staging**: `secrets/barrins_api/staging.env` updated (vault-edited),
  redeployed via
  `ansible-playbook barrins_api.yml -e deploy_env=staging -e fastapi_backend_git_branch=<branch>`,
  validated — `/health` returns 200, clean DB connection over
  `localhost` in `journalctl -u api-staging`.
- **Production**: `secrets/barrins_api/production.env` updated locally
  (`DATABASE_URL` now points at `localhost`) but **not yet deployed**.
  The deploy hit an unrelated blocker (see below) and was left there
  deliberately — the old `api` process kept running untouched on the
  old config throughout, so production was never at risk. Decision:
  leave production as-is until the v2.0.0 release ships (expected soon)
  rather than force a migration decision on production tonight.
  `production.env` is already prepared, so the localhost switch will
  take effect automatically on the next successful production deploy.
- **`pg_hba.conf`/`listen_addresses` narrowing**: deliberately **not**
  done yet — production still depends on the public-IP path until it
  redeploys, so removing `0.0.0.0/0` now would break it. Do this only
  after a production deploy succeeds with the `localhost` `DATABASE_URL`
  confirmed working.

### Blocker found during the production deploy: DB migration state ahead of `main`

`alembic upgrade head` failed on both environments with "Can't locate
revision" — staging: `b7d1f4a290ec`, production: `3e8e2a2dc724`. Neither
revision is missing/deleted; both migration files exist, but not on the
branch/tag actually being deployed:

- `3e8e2a2dc724_add_game_and_category_to_ts_personal_.py` exists on
  `origin/main`, but apparently postdates whatever release tag
  production's "latest release" deploy resolved to.
- `b7d1f4a290ec_add_text_features_to_mj_cards.py` doesn't exist on
  `origin/main` at all yet — nor do `7d3f9a1c5e26`
  (`add_mtgjson_sets_and_cards_tables`), `cfef9209e088`
  (`prefix_mtgjson_tables_add_import_runs`), or `a3c7f912e5b8`
  (`add_sequence_to_bs_rounds`).

Conclusion: these migrations were applied directly to the staging/
production databases by hand over SSH (the documented manual-migration
step) from an unreleased branch, ahead of what's been merged into
`main`. Redeploying from an official release tag/branch can't locate
the revision the database says it's already on. Not a data-loss risk —
the databases' actual schema is fine, it's the deployed *code* that's
behind. Needs the missing migrations merged into `main` before the next
clean release; tracked as part of the v2.0.0 release work, not a
standalone fix.

### Unrelated bug found and fixed along the way

`ops/my-server/roles/github_token/tasks/main.yml` had no `tags:` on any
task, so `ansible-playbook <playbook>.yml --tags deploy` (documented as
"skip cert/nginx setup, just redeploy code") silently skipped the role
that sets the `github_token` fact the clone task needs — breaking every
tagged fast-redeploy for `barrins_api`/`tamiyo_scroll`/`tolaria_news`/
`docs`. Fixed by tagging those tasks `always`.

## Open items

- **Source of the 06:29:57 fast shutdown request is unidentified.** It
  wasn't the disk-full crash (that happened separately at 03:27 and
  recovered on its own) — something explicitly stopped PostgreSQL a
  second time. Needs a check of cron/systemd timers, any Ansible run
  history, and who had shell access around that time.
- **`pg_hba.conf`/`listen_addresses` still wide open** — blocked on the
  production `DATABASE_URL`/migration work above, see "Follow-up" section.
- **Missing migrations need merging into `main`** before the next
  production release — see "Blocker" section above.
- **`barrins_api_staging` dump size jumped from 113KB (Aug 9) to 408MB
  (Aug 14)** — a ~3600x increase in five days. Noted during triage but
  not investigated; worth a look independent of this incident.

## Rollout status

- [x] Root cause identified.
- [x] Immediate mitigation applied (old dumps pruned, PostgreSQL and both
      backends restored).
- [x] `postgres_backup` role fixed (allowlist, 3-day retention, cleanup
      no longer gated on dump success) and deployed.
- [x] Remaining dumps for now-excluded databases removed from
      `/var/backups/postgresql/`.
- [x] Staging `DATABASE_URL` switched to `localhost`, redeployed, validated.
- [x] `github_token` role tagging bug found and fixed (unblocked
      `--tags deploy` generally, not specific to this incident).
- [ ] Production `DATABASE_URL` switch — deferred to next clean release
      (v2.0.0), `production.env` already prepared locally.
- [ ] Missing migrations (`b7d1f4a290ec` and others) merged into `main`.
- [ ] `pg_hba.conf`/`listen_addresses` narrowed — deferred until
      production no longer needs the public-IP path.
- [ ] Source of the 06:29:57 shutdown request identified.
- [ ] `barrins_api_staging` dump-size anomaly investigated.

## See also

- `ops/my-server/roles/postgres_backup/README.md`
- [`../deployment/backup.md`](../deployment/backup.md) — backup & restore
  procedure
- [`../operations/index.md`](../operations/index.md) — backup strategy
  summary
