# RA5. Deploy from tag (production) — Tamiyo Scroll only

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | Production VPS (`146.59.146.57`) | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started | / |
| **Source** | Mirrors R4/v1.0.0's B6, scoped to the alpha cut (§1.11) | / |
| **Dependency** | RA4 | / |

---

## Context

**The one step where this release's scope discipline actually has to be
enforced by hand**, not just by what's in the diff. `v2.0.0-alpha`'s tag
on `main` contains T1 (Barrin's Scripture rewrite) and T2 (`bs_*` schema)
inert, per §1.11's decision — the code and migration are there, but
nothing about deploying `barrins_api`/`tamiyo_scroll` from this tag
should touch `ops/my-server/barrins_scripture.yml`. Each application
deploys via its own independent Ansible playbook (Constitution §26.1),
so this is a matter of **which playbooks get run**, not a code change.

## Done statement

- `barrins_api` redeployed from the `v2.0.0-alpha` tag (standard release
  cadence) — its Alembic migration chain now includes T2's `bs_*` tables
  (additive, no existing data touched) and every Group S migration.
- `tamiyo_scroll` redeployed from the same tag.
- `ops/my-server/barrins_scripture.yml` **is not run** — Barrin's
  Scripture stays undeployed, its systemd service/timer never installed.
- `ops/my-server/tolaria_news.yml` **is not run** — unchanged from
  today (still README-only, §0).

## Tasks

- [ ] Deploy `barrins_api` from the `v2.0.0-alpha` tag.
- [ ] Apply the Alembic migration chain in production (manual step —
      `ops/my-server/barrins_api.yml`'s `post_task` explicitly never runs
      Alembic, per S10/S11's own pages).
- [ ] Deploy `tamiyo_scroll` from the same tag.
- [ ] **Explicitly confirm** `barrins_scripture.yml` was not invoked this
      deploy — a deliberate check, not an assumption, since the playbook
      exists and could be run by habit.
- [ ] Immediately backport this item's "done" confirmation to `staging`
      once written on `main` (§3.1), same as R4's equivalent task.

## UAT (manual)

- [ ] Exercise a real Tamiyo Scroll user flow end to end against
      production (sign up or log in, create a personal deck with the new
      required game/macrotype fields, log a BO3 match, check the demo
      route at `/demo`).
- [ ] Confirm HetrixTools (or successor) still shows exactly the same
      trackers `up` as before this deploy — no new tracker should appear
      (Barrin's Scripture isn't running).
- [ ] Confirm no `bs_*`-scoped route or Barrin's Scripture process is
      reachable/running on the production host.

## Non-regression tests

- N/A (deployment step) — covered by each Group S item's own
  non-regression tests, already run before this point.
