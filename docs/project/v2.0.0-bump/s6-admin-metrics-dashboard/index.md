# S6. Admin usage/metrics dashboard

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` (`app/api/tamiyo_scroll/admin.py`, `app/services/metrics/`), `apps/tamiyo_scroll` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Confirmed for v2.0.0, embedded scope — what "metrics" means concretely still needs sign-off | / |
| **Source** | Request; `v2.0.0-bump/index.md` §1.7 | / |
| **Dependency** | None technical (role infra already exists) | / |

---

## Context

**Confirmed**: this ships embedded in v2.0.0 (routes in `barrins_api`,
UI in `tamiyo_scroll`), gated by the existing `AdminUser`/
`require_role(UserRole.admin)` mechanism
(`app/dependencies/auth.py`) — no new auth work. **Confirmed**: it
externalizes into a standalone cross-app application in v3.0.0, accessed
via Barrin's Identity/Goblin Guide — not scheduled before then. **Not
yet confirmed**: the exact metric set (assumed default: product/usage
analytics — signups, active users, decks, matches, sharing adoption).

## Done statement

- A new admin-only route (or small set of routes) under
  `app/api/tamiyo_scroll/admin.py`, gated by `AdminUser`, computing the
  confirmed metric set server-side via a new `app/services/metrics/`
  module.
- A new admin-only page in `apps/tamiyo_scroll`, reachable only to users
  whose role satisfies `admin`, rendering those metrics.
- The `app/services/metrics/` module is self-contained (not inlined into
  `app/services/tamiyo_scroll/`) and any aggregate value it returns
  carries an explicit app/source tag (even though v2.0.0 only ever
  populates it with `tamiyo_scroll`) — both are the two forward-
  compatibility constraints from §1.7 that make the v3.0.0
  externalization a lift-and-shift rather than a rewrite.
- A short written note (even a paragraph) on what data this surfaces and
  why, given the constitution has no existing privacy/data-retention
  policy to point to.

## Tasks

- [ ] Confirm the exact metric set with the user before implementing
      (currently only an assumed default).
- [ ] Build `app/services/metrics/` (pure, tested aggregation functions
      — same pattern as `services/tamiyo_scroll/stats.py`).
- [ ] Build the admin route(s), `dependencies=[Depends(require_role(
      UserRole.admin))]`.
- [ ] Build the admin-only frontend route/page, gated the same way
      `ProtectedRoute` gates authenticated routes today (a new
      `AdminRoute` wrapper checking `session.role`, or equivalent).
- [ ] Write the short data-usage note.

## UAT (manual)

- [ ] Log in as a non-admin user; confirm the admin route/page is
      unreachable (403 on the API, hidden/redirected in the UI).
- [ ] Log in as an admin; confirm the dashboard reflects real aggregate
      numbers matching a manual count against the database.

## Non-regression tests

- New `tests/tamiyo_scroll/test_admin_metrics.py`: 403 for non-admin,
  200 + correct aggregates for admin.
- A test asserting the metrics service never queries with an
  unfiltered/unbounded query that could regress under real data volume
  (a basic sanity check, not a full performance test).
