# S6. Admin usage/metrics dashboard

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` (`app/api/tamiyo_scroll/admin.py`, `app/services/metrics/`), `apps/tamiyo_scroll` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — scope resolved 2026-07-25 (§1.7), staged | / |
| **Source** | Request; `v2.0.0-bump/index.md` §1.7 | / |
| **Dependency** | None technical (role infra already exists) | / |

---

## Context

**Confirmed**: this ships embedded in v2.0.0 (routes in `barrins_api`,
UI in `tamiyo_scroll`), gated by the existing `AdminUser`/
`require_role(UserRole.admin)` mechanism
(`app/dependencies/auth.py`) — no new auth work. **Confirmed**: it
externalizes into a standalone cross-app application in v3.0.0, accessed
via Barrin's Identity/Goblin Guide — not scheduled before then.
**Confirmed (2026-07-25)**: Option 1 (product/usage analytics), staged
— v2.0.0 ships only the simplest adoption signals; deeper metrics are
explicit follow-on work. See `../index.md` §1.7.

## v2.0.0 metric set (staged, decided)

**Ship now** — enough to answer "is the app being adopted at all":

- Total accounts created.
- Total personal decks created.
- Total matches recorded.

**Explicitly deferred, not v2.0.0**: active-user counts (daily/weekly),
sharing-adoption rate, per-feature engagement, retention — anything
beyond raw adoption counts. "Smart KPIs" beyond these three are only
worth defining once there's usage data to justify which ones matter.

## Done statement

- A new admin-only route (or small set of routes) under
  `app/api/tamiyo_scroll/admin.py`, gated by `AdminUser`, computing the
  three metrics above server-side via a new `app/services/metrics/`
  module.
- A new admin-only page in `apps/tamiyo_scroll`, reachable only to users
  whose role satisfies `admin`, rendering those metrics.
- The `app/services/metrics/` module is self-contained (not inlined into
  `app/services/tamiyo_scroll/`) and any aggregate value it returns
  carries an explicit app/source tag (even though v2.0.0 only ever
  populates it with `tamiyo_scroll`) — both are the two forward-
  compatibility constraints from §1.7 that make the v3.0.0
  externalization a lift-and-shift rather than a rewrite.
- The privacy/analytics policy gap flagged in §1.7 is addressed before
  this ships — **resolved**: `../consitution-amendment.md` Proposal 1
  was accepted by the user (2026-07-26), so this feature has a real
  policy to point to (aggregate-only data, no new collection, documented
  alongside the feature) instead of an ad hoc per-feature note.

## Tasks

- [ ] Apply `../consitution-amendment.md` Proposal 1 to
      `docs/content/CLAUDE.md` (or confirm R5 has already done so) before
      this ships — accepted 2026-07-26, but not yet written into the
      constitution itself; this item shouldn't be the one to silently
      assume that's already done.
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
