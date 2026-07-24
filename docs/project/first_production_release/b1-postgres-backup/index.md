# B1. New Ansible role: `postgres_backup`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `ops/my-server` | / |
| **Initial date** | 2026-07-23 | / |
| **Status** | ✅ Implemented (role + docs) | UAT requires production VPS access, not yet performed |
| **Source** | Constitution §36 (backup/verified-restore requirement) | flagged as a release blocker |
| **Dependency** | none | must run before B5 — backup timer needs to exist before the first production migration |

---

## Context

`docs/content/ops/operations/index.md` documents that PostgreSQL has no
backup/verified-restore process today — the single most significant open
gap, and Constitution §36 is explicit that "a backup that has never been
tested is not considered reliable." This is a release blocker.

## Design

- A systemd-timer-driven script (same pattern as pgAdmin's weekly
  auto-update timer in `roles/pgadmin`) runs daily as the `postgres` OS
  user: `pg_dump --format=custom` per non-template database →
  `/var/backups/postgresql/`, plus `pg_dumpall --globals-only` for
  roles/grants. `umask 077` in the script makes every created file
  `0600` by construction rather than a follow-up `chmod`. Retention:
  `find ... -mtime +14 -delete` at the end of each run (14 days,
  configurable). PostgreSQL is already installed natively by
  `setup_packages`, so no new package is needed.
- **Alternative rejected**: offsite storage (S3/Backblaze/rclone) — new
  external dependency/credentials (§22) for a single-VPS setup with no
  second site to protect yet. Tracked as a future improvement.
- **Where it lives**: wired into `ops/my-server/postgresql_pgadmin.yml`
  (host-level infra playbook), not a new playbook — backups are host
  infrastructure like pgAdmin, not a per-app release-tagged deploy.
- New files (existing role conventions: lowercase name, FQCN modules,
  quoted octal `mode:`, `<role>_`-prefixed vars, `name:` on every task):
  - `ops/my-server/roles/postgres_backup/tasks/main.yml`
  - `ops/my-server/roles/postgres_backup/templates/*.j2` (backup script,
    systemd service + timer)
  - `ops/my-server/roles/postgres_backup/vars/main.yml`
  - `ops/my-server/roles/postgres_backup/README.md` (synced by
    `sync_readmes.py` into `docs/content/ops/roles/postgres_backup/index.md`)
- New doc page `docs/content/ops/deployment/backup.md`: preparation,
  deployment, validation, and the restore drill procedure (`pg_restore`
  into a scratch database, verify, drop it). Added to `docs/mkdocs.yml`
  nav under Ops → Deployment and Ops → Roles.
- Drive-by fix: `docs/content/ops/operations/index.md` still referenced
  `/health`'s pre-A7 path (`app/api/health.py`); corrected to
  `app/api/general/health.py`.

## Tasks

- [x] Implement the `postgres_backup` role (tasks, templates, vars,
      README).
- [x] Wire it into `postgresql_pgadmin.yml`.
- [x] Write `docs/content/ops/deployment/backup.md`.
- [x] Update `docs/mkdocs.yml` nav (Deployment + Roles) and
      `docs/content/ops/roles/index.md`, `.gitignore`.
- [x] Update the open-items + backup-strategy sections in
      `docs/content/ops/operations/index.md`.
- [x] `ansible-lint ops/my-server` clean (production profile) — run from
      WSL (Ubuntu), per the Constitution's own note that ansible-lint
      needs the POSIX `grp` module and doesn't run natively on Windows.
- [x] `mkdocs build --strict`, markdownlint, and cspell all clean
      (6 new technical terms added to `cspell.json`:
      `createdb`/`dbname`/`dropdb`/`dumpall`/`datistemplate`/`oneshot`/
      `Backblaze`).

## Done statement

`postgres_backup` role implemented, `ansible-lint` clean, docs build
clean. Timer verification and the restore drill itself still require a
real server — see UAT below.

## UAT (manual)

Requires actual VPS access, not available in the dev sandbox this role
was built in.

- [ ] SSH to the staging host after deploy; confirm
      `systemctl status postgres_backup.timer` is active and a dump file
      exists under `/var/backups/postgresql/`.
- [ ] Personally perform the restore drill: restore a dump into a scratch
      database, verify the data matches, drop the scratch database.

## Non-regression tests

- Automated: `ansible-lint ops/my-server` clean (existing CI gate) —
  verified locally via WSL; full test suite unaffected (backend/frontend
  code untouched by this item).
- Automated: `docs` CI checks (markdownlint/cspell/`mkdocs build --strict`)
  clean with the new `backup.md` page and role doc.
- Manual: pgAdmin (existing role, same playbook) still works after adding
  `postgres_backup` alongside it — no interference between roles (not
  independently re-verified beyond `ansible-lint`'s static check, since
  that requires the same real-server access as the UAT above).
