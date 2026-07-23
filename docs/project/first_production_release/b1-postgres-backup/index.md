# B1. New Ansible role: `postgres_backup`

[← Back to project index](../index.md)

## Context

`docs/content/ops/operations/index.md` documents that PostgreSQL has no
backup/verified-restore process today — the single most significant open
gap, and Constitution §36 is explicit that "a backup that has never been
tested is not considered reliable." This is a release blocker.

## Design

- A systemd-timer-driven script (same pattern as pgAdmin's weekly
  auto-update timer in `roles/pgadmin`) runs daily as the `postgres` OS
  user: `pg_dump -Fc` per database → `/var/backups/postgresql/`, `0600`
  permissions, plus `pg_dumpall --globals-only` for roles/grants.
  Retention: keep the last 14 daily dumps
  (`find ... -mtime +14 -delete`). PostgreSQL is already installed
  natively by `setup_packages`, so no new package is needed.
- **Alternative rejected**: offsite storage (S3/Backblaze/rclone) — new
  external dependency/credentials (§22) for a single-VPS setup with no
  second site to protect yet. Tracked as a future improvement.
- **Where it lives**: wired into `ops/my-server/postgresql_pgadmin.yml`
  (host-level infra playbook), not a new playbook — backups are host
  infrastructure like pgAdmin, not a per-app release-tagged deploy.
- New files (existing role conventions: lowercase name, FQCN modules,
  quoted octal `mode:`, `changed_when` on every command/shell task,
  `<role>_`-prefixed vars, `name:` on every task):
  - `ops/my-server/roles/postgres_backup/tasks/main.yml`
  - `ops/my-server/roles/postgres_backup/templates/*.j2`
  - `ops/my-server/roles/postgres_backup/vars/main.yml`
  - `ops/my-server/roles/postgres_backup/README.md` (synced by
    `sync_readmes.py`)
- New doc page `docs/content/ops/deployment/backup.md`: preparation,
  deployment, and a real restore drill (`pg_restore` into a scratch
  database, verify, drop it — performed once, not just documented, per
  §36). Add to `docs/mkdocs.yml` nav under Ops → Deployment.

## Tasks

- [ ] Implement the `postgres_backup` role (tasks, templates, vars,
      README).
- [ ] Wire it into `postgresql_pgadmin.yml`.
- [ ] Write `docs/content/ops/deployment/backup.md`.
- [ ] Update `docs/mkdocs.yml` nav.
- [ ] Update the open-items table in
      `docs/content/ops/operations/index.md`.
- [ ] Run `ansible-lint ops/my-server` clean.

## Done statement

`postgres_backup` role implemented, `ansible-lint` clean, timer verified
active on staging, restore drill performed once successfully.

## UAT (manual)

- [ ] SSH to the staging host after deploy; confirm
      `systemctl status postgres_backup.timer` is active and a dump file
      exists under `/var/backups/postgresql/`.
- [ ] Personally perform the restore drill: restore a dump into a scratch
      database, verify the data matches, drop the scratch database.

## Non-regression tests

- Automated: `ansible-lint ops/my-server` clean (existing CI gate).
- Manual: pgAdmin (existing role, same playbook) still works after adding
  `postgres_backup` alongside it — no interference between roles.
