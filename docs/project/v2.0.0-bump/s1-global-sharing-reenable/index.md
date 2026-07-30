# S1. Re-enable and extend global results sharing

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tamiyo_scroll`, `apps/barrins_api` | / |
| **Initial date** | 2026-07-30 | Completed 2026-07-30 |
| **Status** | ✅ Done — per-sharer receive opt-in shipped, `SHARING_ENABLED` gate removed | / |
| **Source** | Request item 2.5 | / |
| **Dependency** | None for the "share" half; I1 only for the new "receive" half | / |

---

## Context

Read-only cross-user sharing already exists and is fully tested:
backend enforcement (`ownership.resolve_owner`,
`ts_user_settings.data_shared`, 127 tests) has been live since v1.0.0.
The frontend half (`components/layout/SharingControls.tsx`) was built,
tested, then deliberately extracted and gated off
(`const SHARING_ENABLED = false`) before the v1.0.0 launch — see
`docs/project/v1.0.0-bump/a2-sharing-extraction/index.md`
for the original reasoning (UI maturity, not backend readiness). The
request adds one genuinely new piece: a "toggle to receive" — today, any
user can view any sharer's data via the "View: {user}" selector with no
opt-in on the *viewing* side; the request wants that to become explicit.

## Done statement

- `SHARING_ENABLED` flipped to `true` (or the constant removed entirely
  if no longer needed) — the existing "Share my data" checkbox and
  "View: {user}" selector are visible again, unmodified from their
  tested v1.0.0 state.
- A new opt-in exists on the *receiving* side: a user only appears able
  to view another's shared data if they've also opted in to receiving
  (exact UX — a checkbox, a per-sharer follow action — not yet decided,
  flagged below).
- No change to `ownership.resolve_owner`'s existing write-side
  enforcement (still: writes only ever target `current_user`, regardless
  of `owner_id`).

## Tasks

- [x] Flip `SHARING_ENABLED` (removed the gate entirely — dead flag with
      no remaining callers); `SharingControls.test.tsx` rewritten for the
      always-rendered component.
- [x] Design the "toggle to receive" concept: **decided — per-sharer
      opt-in** (new `ts_receive_opt_ins` table, `viewer_id`/`sharer_id`),
      escalated to and confirmed by the user per Constitution §16.2.
- [x] Extended `GET /shared-users` to require both `data_shared = True`
      and a matching opt-in row; added `GET /available-sharers`,
      `POST /receive-opt-ins`, `DELETE /receive-opt-ins/{sharer_id}`.
- [x] Updated `SharingControls.tsx` (new "Receive shared data from:"
      checkbox list) and its test suite for the new control.

## UAT (manual)

- [ ] On staging, two accounts: user A enables sharing, user B has not
      opted in to receiving — confirm B does **not** see A in their
      "View: {user}" selector.
- [ ] User B opts in to receiving — confirm A now appears.
- [ ] Confirm every write-side backend test from
      `tests/tamiyo_scroll/test_ownership.py` still passes unmodified.

## Non-regression tests

- Existing: `SharingControls.test.tsx`, `test_ownership.py`,
  `test_settings.py` — updated for the opt-in requirement, all green
  (263 backend tests / 97.29% coverage, 67 frontend tests, all passing).
- New: `TestAvailableSharers`, `TestReceiveOptIns` (backend);
  opt-in/opt-out checkbox tests (frontend) — cover the "receive" opt-in
  gating the selector's contents.

**Not done here**: the UAT checklist above is a manual staging exercise,
out of scope for this implementation pass.
