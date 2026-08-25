# RB4. Deploy from tag (production) — Tamiyo Scroll only

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | Production VPS (`146.59.146.57`) | / |
| **Initial date** | 2026-08-25 | Done same day |
| **Status** | ✅ **Done (2026-08-25)** — both apps deployed from `v2.0.0-alpha.2`, smoke-tested online | / |
| **Source** | Mirrors RA5/R4/v1.0.0's B6, scoped to the alpha.2 cut (§1.12) | / |
| **Dependency** | RB3 | / |

---

## Context

Simpler than RA5 on one count: `v2.0.0-alpha.2`'s tag carries **no**
Group T code at all (§1.12 — `feat/tamiyo-scroll-alpha2` branched off
`staging` directly, never through `proj/v2.0.0-bump`), so there's no
"confirm Barrin's Scripture code exists but stays undeployed" nuance
this time — `ops/my-server/barrins_scripture.yml` simply isn't in the
picture. The scope discipline that matters here is the same as RA5's:
each application deploys via its own independent Ansible playbook
(Constitution §26.1), so this is a matter of **which playbooks get
run**, not a code change. This cut does add one new production-only
scheduled job (S8's MTGJSON refresh timer), which needs its own
`MTGJSON_IMPORT_TOKEN` secret in place before the `barrins_api`
playbook runs — see `docs/content/ops/deployment/backend.md`.

## Done statement

- `barrins_api` redeployed from the `v2.0.0-alpha.2` tag (standard
  release cadence) — its Alembic migration chain now includes S8's
  `mj_sets`/`mj_cards`/`mj_import_runs` tables, T6's `mj_cards` text/
  keyword/stat columns, F10's `TSMetaDeck.personal_deck_id`, and every
  other Group S migration since alpha1.
- `tamiyo_scroll` redeployed from the same tag.
- `MTGJSON_IMPORT_TOKEN` is set in `secrets/barrins_api/production.env`
  (the `mtgjson_import_scheduler` role's playbook task fails fast if
  it's missing) and the daily 04:00 UTC systemd timer is enabled.
- `ops/my-server/barrins_scripture.yml` and `ops/my-server/
  tolaria_news.yml` **are not run** — unchanged from today (no code for
  either exists on this tag in any deployable state).

## Tasks

- [x] Deploy `barrins_api` from the `v2.0.0-alpha.2` tag.
- [x] Apply the Alembic migration chain in production (manual step —
      `ops/my-server/barrins_api.yml`'s `post_task` explicitly never runs
      Alembic, per S10/S11's own pages). **Confirmed by the user
      (2026-08-25): applied OK.**
- [x] Confirm `MTGJSON_IMPORT_TOKEN` is present in
      `secrets/barrins_api/production.env` before the playbook runs.
      **Confirmed set.**
- [x] Deploy `tamiyo_scroll` from the same tag.
- [x] Trigger `POST /mtgjson/import` once manually (admin JWT) post-
      deploy to populate `mj_sets`/`mj_cards` for the first time in
      production, rather than waiting for the next 04:00 UTC timer tick.
      **Confirmed done manually.**
- [x] **Unplanned fix found live**: `ops/my-server/barrins_api.yml` was
      missing a `backend_work_dir` play-level var the
      `mtgjson_import_scheduler` role needs (to locate the deployed
      `.env`) — added directly during this deploy. A fuller wiring of
      the same variable already exists on `feat/tolaria_news_backend`
      (unmerged, unrelated to this release); this is the minimal
      standalone fix, committed on `backport/rb-docs-to-staging`
      (PR #85) alongside RB1–RB3's backport, since it needs to reach
      `staging` too and that branch was already open.
- [ ] Immediately backport this item's "done" confirmation to `staging`
      once written on `main` (§3.1), same as RA5/R4's equivalent task —
      **in progress**, folded into PR #85 (see above).

## UAT (manual)

- [ ] Exercise a real Tamiyo Scroll user flow end to end against
      production: log in, view a decklist (card images/mana pips/sort —
      S4), view a past decklist version's diff (S15), create/evaluate a
      card log (S16/S17), edit a session (S14), and confirm a delete
      action shows the confirmation dialog (S13). **Not individually
      itemized — the user confirmed smoke tests passed post-deploy;
      this line-by-line breakdown hasn't been separately verified.**
- [ ] `GET /api/v1/mtgjson/status` shows a non-null `last_imported_at`
      and non-zero `total_sets`/`total_cards`. **Likely true (manual
      import was triggered) but not independently re-checked here.**
- [ ] `systemctl status api-mtgjson-import.timer` shows the timer
      enabled with a scheduled next-run time. **Not confirmed.**
- [ ] Confirm HetrixTools (or successor) still shows exactly the same
      trackers `up` as before this deploy. **Not confirmed.**

## Non-regression tests

- N/A (deployment step) — covered by each Group S item's own
  non-regression tests, already run before this point.
