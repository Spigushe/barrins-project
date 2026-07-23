# B5. Deploy from tag (production)

[← Back to project index](../index.md)

## Tasks

- [ ] **Pre-flight**: confirm `initial.yml`/`setup.yml` have actually
      been run against `146.59.146.57`; DNS A records exist for
      `api.barrins-codex.org` / `tamiyo.barrins-codex.org`; local
      production `.env` files exist, **including the new
      `MOXFIELD_USER_AGENT` secret**.
- [ ] Run `ansible-playbook postgresql_pgadmin.yml` first (brings up the
      new `postgres_backup` timer) so a backup schedule exists before the
      first production migration ever runs.
- [ ] Run `ansible-playbook barrins_api.yml` (production, release-tag
      mode) → confirm the backup role produced at least one dump →
      apply the Alembic migration manually
      (`uv run alembic upgrade head`, §31.3).
- [ ] Run `ansible-playbook tamiyo_scroll.yml` (production, release-tag
      mode).
- [ ] Validate per `backend.md`/`frontend.md`'s existing "Validation"
      sections, plus the new `/health` endpoint and the Moxfield import
      flow end-to-end.

## Done statement

Both apps deployed and healthy in production; migration applied; backup
timer running; monitoring reports green.

## UAT (manual)

- [ ] Re-run, against **production** this time, the UAT already
      performed on staging for A1 (`/health`), A3 (Moxfield import), and
      A5 (combobox/hidden tabs) — this step is the final full manual
      regression pass before calling v1.0.0 live.

## Non-regression tests

This step *is* the cumulative non-regression checkpoint — every earlier
item's UAT re-run once against production, plus the existing signup →
deck-creation → match-record flow already in
`backend.md`/`frontend.md`.
