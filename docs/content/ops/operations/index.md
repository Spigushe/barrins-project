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
`roles/backend-website/templates/https.conf.j2` and
`roles/register-ssl/templates/http.conf.j2`), landing wherever the host's
syslog is configured to write (`journalctl` by default on this Debian
host).

## Health checks

Constitution §31.2 expects the API to expose health information. There is
currently **no dedicated `/health` route** — `barrins_api` redirects `/`
to `/docs`, which is what the deployment guides' "Validation" steps check
instead. Open item: add a real `/health` endpoint that reports service
status (and, ideally, database connectivity) rather than relying on "the
docs page loads" as a proxy signal.

## Monitoring

**Not implemented.** No uptime monitoring, alerting, or certificate
expiration monitoring (Constitution §30 requires the latter) currently
exists for this infrastructure. This is an open gap, not a deliberate
decision — flagged here so it isn't silently assumed to exist.

## Backup strategy

Constitution §36 requires database backups, backup verification, and a
documented restoration procedure — and explicitly states "a backup that
has never been tested is not considered reliable." **None of this is
currently implemented**: there is no automated PostgreSQL backup job, no
verification, and no restoration runbook. This is the most significant
open gap relative to the Constitution's operations requirements and
should be prioritized before this infrastructure is trusted with data
that matters.

## Open items summary

| Item | Constitution ref | Status |
| --- | --- | --- |
| `/health` endpoint | §31.2 | Not implemented |
| Uptime/alerting monitoring | — | Not implemented |
| Certificate expiration monitoring | §30 | Not implemented (renewal itself is automatic via certbot) |
| Database backups + verified restore | §36 | Not implemented |
| nginx security headers (HSTS, etc.) | §29.1 | Not implemented |
| Pre-commit secret-scanning enforced for all contributors | §34 | Opt-in only, see [`../security/secrets.md`](../security/secrets.md) |

## See also

- [`../deployment/backend.md`](../deployment/backend.md),
  [`../deployment/frontend.md`](../deployment/frontend.md) — day-to-day
  validation steps that currently substitute for real monitoring.
- [`../security/index.md`](../security/index.md) — TLS and reverse proxy
  configuration.
