# Backup & Restore — PostgreSQL

Operational guide for the `postgres_backup` role (wired into
`ops/my-server/postgresql_pgadmin.yml`, alongside `pgadmin` — backups are
host-level infrastructure, not a per-app release-tagged deploy).
Structured per Constitution §37.1 and closes the open item flagged in
[`../operations/index.md`](../operations/index.md): no database backup
process existed before this.

| | Detail |
| --- | --- |
| Playbook | `postgresql_pgadmin.yml` |
| Backup location | `/var/backups/postgresql/` (host, `postgres`-owned, mode `0700`) |
| Schedule | Daily, 03:00 ± 30 min, via `postgres_backup.timer` |
| Retention | 14 days (deleted on each run) |

## Preparation

**Server requirements** — `setup_packages` must have already run
(installs `postgresql` natively on the host — see
[`database.md`](database.md)).

**Nothing else to prepare** — unlike the backend `.env` files or
pgAdmin's admin password, this role needs no local secret: the backup
script runs as the `postgres` OS user and connects via local peer
authentication, the same access `pgAdmin`'s own Postgres role setup
already relies on.

## Deployment

```bash
ansible-playbook postgresql_pgadmin.yml
```

Code-only redeploy (skip cert/nginx setup, already idempotent but
faster): add `--tags backup`.

## Validation

```bash
ssh spigushe.org
systemctl status postgres_backup.timer   # active, next run scheduled
systemctl list-timers postgres_backup.timer
ls -la /var/backups/postgresql/          # a *_<timestamp>.dump per database
                                          # + one globals_<timestamp>.sql
```

To trigger a run immediately rather than waiting for 03:00:

```bash
sudo systemctl start postgres_backup.service
journalctl -u postgres_backup.service -n 50
```

## Restore drill (perform this at least once — Constitution §36)

A backup that has never been restored is not considered reliable. Do
this once after the role first deploys, and again after any schema
change you're unsure about:

```bash
ssh spigushe.org
sudo -u postgres bash

# Pick a real dump, e.g. /var/backups/postgresql/barrins_api_staging_20260101-030000.dump
createdb barrins_restore_test
pg_restore --dbname=barrins_restore_test /var/backups/postgresql/<dump-file>

# Verify — row counts, a spot-checked table, whatever gives real confidence
psql barrins_restore_test -c "SELECT count(*) FROM users;"

# Clean up
dropdb barrins_restore_test
```

Globals (`globals_<timestamp>.sql`) restore differently — it's plain SQL,
not a `pg_dump --format=custom` archive:

```bash
psql -f /var/backups/postgresql/<globals-file> postgres
```

## Rollback

Nothing to roll back on the backup side — re-running the playbook is
idempotent (same script, same timer, no state to diverge). For rolling
back application code/database state itself, see
[`rollback.md`](rollback.md); a backup restored via the drill above is
exactly what that page's "restore from a database backup taken before
the migration ran" step means in practice.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `postgres_backup.timer` not listed by `systemctl list-timers` | Role hasn't deployed yet, or the playbook was run with a `--tags` filter that excluded it. |
| `postgres_backup.service` fails, `journalctl` shows a `psql`/`pg_dump` connection error | PostgreSQL isn't running (`systemctl status postgresql`), or `setup_packages` hasn't run on this host yet. |
| `/var/backups/postgresql/` is empty after the timer's scheduled time | Check `journalctl -u postgres_backup.service` for the actual error; confirm the timer is `enabled` *and* `active`. |
| Dumps keep growing past 14 days | The `find ... -delete` step only runs at the *end* of a successful backup run — if every run has been failing, cleanup never executes either. Fix the underlying failure first. |

## See also

- [`database.md`](database.md) — pgAdmin, the other role in this same
  playbook.
- [`rollback.md`](rollback.md) — application/database rollback, which
  this backup process supports.
- `ops/my-server/roles/postgres_backup/README.md` — full role technical
  detail.
