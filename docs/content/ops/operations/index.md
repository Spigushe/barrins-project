# Operations

Logging, monitoring, and backups for the production VPS — Constitution
§§35–36. This page documents current state honestly, including what isn't
implemented yet, rather than describing an aspirational setup.

## Application logs

`barrins_api` logs to its own log file (`LOG_FILE_PATH` in `.env`, see
[`../deployment/backend.md`](../deployment/backend.md)) and to the systemd
journal (`journalctl -u api` / `api-staging`). This is the primary way to
diagnose a failed deploy or a runtime error today — see the
"Troubleshooting" tables in
[`../deployment/backend.md`](../deployment/backend.md) and
[`../deployment/frontend.md`](../deployment/frontend.md).

## Infrastructure logs

nginx access/error logs are sent to syslog (`access_log
syslog:server=unix:/dev/log,nohostname;` in the generated vhosts — see
`roles/backend_website/templates/https.conf.j2` and
`roles/register_ssl/templates/http.conf.j2`), landing wherever the host's
syslog is configured to write (`journalctl` by default on this Debian
host).

## Health checks

Constitution §31.2 expects the API to expose health information.
`barrins_api` now exposes `GET /health` (`app/api/general/health.py`): returns
`200 {"status": "ok"}` when the database is reachable, or `503` (via the
standard `ServiceUnavailableError` error envelope) otherwise. The
deployment guides' "Validation" steps can check this endpoint directly
instead of relying on "the docs page loads" as a proxy signal.

## Monitoring

**Live.** [HetrixTools](https://hetrixtools.com/) (private status pages,
minimal signup PII) is set up with monitors against both `barrins_api`'s
staging and production `/health` URLs; both report `200`/"up". The free
tier caps trackers at 2, so `tamiyo_scroll` isn't separately monitored —
accepted because both frontends share this backend (a `barrins_api`
outage is caught either way; a frontend-only failure with the backend
still healthy is not). Certificate expiration monitoring is part of the
same HetrixTools setup and is live.

## Backup strategy

Constitution §36 requires database backups, backup verification, and a
documented restoration procedure — and explicitly states "a backup that
has never been tested is not considered reliable." The `postgres_backup`
role (wired into `postgresql_pgadmin.yml`) now takes a daily `pg_dump`/
`pg_dumpall` backup of an explicit allowlist of databases, kept for 3
days — see [`../deployment/backup.md`](../deployment/backup.md) for the
full procedure, including the restore drill that must actually be
performed (not just documented) before this is considered reliable. A
2026-08-15 incident (dumping every database unconditionally at 14-day
retention filled the host's disk and took Postgres down) is what
narrowed this — see the role's README for detail. No offsite
copy yet — tracked as a future improvement, not silently skipped (see
that page for why).

## Open items summary

| Item | Constitution ref | Status |
| --- | --- | --- |
| `/health` endpoint | §31.2 | Implemented (`GET /health`, `apps/barrins_api/app/api/health.py`) |
| Uptime/alerting monitoring | — | Implemented (HetrixTools, `barrins_api` prod + staging — free tier caps trackers at 2, `tamiyo_scroll` not separately monitored) |
| Certificate expiration monitoring | §30 | Implemented (HetrixTools, same setup as uptime monitoring) |
| Database backups + verified restore | §36 | Implemented (`postgres_backup` role) — restore drill personally performed on staging, data matched exactly |
| nginx security headers (HSTS, etc.) | §29.1 | Not implemented |
| Pre-commit secret-scanning enforced for all contributors | §34 | Opt-in only, see [`../security/secrets.md`](../security/secrets.md) |

## See also

- [`../deployment/backend.md`](../deployment/backend.md),
  [`../deployment/frontend.md`](../deployment/frontend.md) — day-to-day
  validation steps that currently substitute for real monitoring.
- [`../security/index.md`](../security/index.md) — TLS and reverse proxy
  configuration.
