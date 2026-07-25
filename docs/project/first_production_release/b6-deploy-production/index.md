# B6. Deploy from tag (production)

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | production VPS (`146.59.146.57`) | / |
| **Initial date** | 2026-07-23 | / |
| **Status** | ✅ Deployed to production, UAT fully confirmed | / |
| **Source** | Release checklist | first production deploy |
| **Dependency** | B5 + B1 + B2 | release tag must exist; backup timer must run before the first production migration; B2's `docs_site` role/`docs.yml` playbook must already exist (built in B2, staging-verified) |

---

## Tasks

- [X] **Pre-flight**: confirm `initial.yml`/`setup.yml` have actually
      been run against `146.59.146.57`; DNS A records exist for
      `api.barrins-codex.org` / `tamiyo.barrins-codex.org` /
      `docs.barrins-codex.org`; local production `.env` files exist,
      **including the new `MOXFIELD_USER_AGENT` secret**.
- [X] Run `ansible-playbook postgresql_pgadmin.yml` first (brings up the
      new `postgres_backup` timer) so a backup schedule exists before the
      first production migration ever runs.
- [X] Run `ansible-playbook barrins_api.yml` (production, release-tag
      mode) → confirm the backup role produced at least one dump →
      apply the Alembic migration manually
      (`uv run alembic upgrade head`, §31.3).
- [X] Run `ansible-playbook tamiyo_scroll.yml` (production, release-tag
      mode).
- [X] Run `ansible-playbook docs.yml` (production, release-tag mode) —
      B2's deferred production UAT item, only possible now that a
      release tag exists (B5).
- [X] Validate per `backend.md`/`frontend.md`'s existing "Validation"
      sections, plus the new `/health` endpoint and the Moxfield import
      flow end-to-end.

## Done statement

Both apps deployed and healthy in production; migration applied; backup
timer running; docs site live at `docs.barrins-codex.org` from the
release tag; monitoring reports green.

## UAT (manual)

- [X] Re-run, against **production** this time, the UAT already
      performed on staging for A1 (`/health`), A3 (Moxfield import), and
      A5 (combobox/hidden tabs) — this step is the final full manual
      regression pass before calling v1.0.0 live.
- [X] B2's deferred item: confirm `https://docs.barrins-codex.org`
      serves the release tag's content.

## Non-regression tests

This step *is* the cumulative non-regression checkpoint — every earlier
item's UAT re-run once against production, plus the existing signup →
deck-creation → match-record flow already in
`backend.md`/`frontend.md`.
