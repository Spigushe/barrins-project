# A2. Extract and disable the "sharing" feature

[← Back to project index](../index.md)

## Context

"Sharing" = the read-only cross-user viewing feature (`data_shared` /
`owner_id` / "Share my data" checkbox / "View: {user}" selector). The
backend enforcement is fully tested
(`apps/barrins_api/app/services/tamiyo_scroll/ownership.py`,
`tests/tamiyo_scroll/test_ownership.py`, `test_settings.py` — 127 tests
total) — that part is not the concern. The gap is frontend: it's wired
into `apps/tamiyo_scroll/src/components/layout/AppShell.tsx` (checkbox at
~line 135, "View:" selector at ~lines 109–126, `canEdit` branching at
~line 44) with no component-level test, and it's tightly interleaved with
the deck-selector code A5 rewrites.

**Decision**: extract *and* disable for v1.0.0 — not mature enough to
ship to end users yet.

## Design

- Extract the checkbox + "View: {user}" selector + `canEdit`/viewing-mode
  branching out of `AppShell.tsx` into their own component
  (`src/components/layout/SharingControls.tsx`), reusing the existing
  `useSettings`/`useViewingOwner` hooks unchanged.
- Gate its rendering behind a simple in-code constant
  (`const SHARING_ENABLED = false`) — no need for a full feature-flag
  system — so v1.0.0 ships with the control hidden from end users.
  Backend routes/enforcement are untouched.
- Add the missing component test for `SharingControls` while it's
  isolated, even though disabled, so it doesn't bit-rot silently.
- **Consequence**: removes `canEdit`/viewing-mode branching from the
  deck-selector code path for this release, simplifying A5. Re-enabling
  sharing later means re-integrating viewing-mode handling into whatever
  the deck selector looks like at that time.

## Tasks

- [ ] Create `SharingControls.tsx`, moving the checkbox/selector/
      `canEdit` logic out of `AppShell.tsx`.
- [ ] Gate it behind `SHARING_ENABLED = false`.
- [ ] Remove the sharing render block from `AppShell.tsx`.
- [ ] Add `SharingControls.test.tsx`.
- [ ] Confirm existing backend `test_ownership.py`/`test_settings.py`
      still pass untouched.

## Done statement

`SharingControls` extracted into its own component, gated off so v1.0.0
users never see it; component has its own test; `AppShell.tsx` no longer
renders it; backend untouched and its existing test suite still green.

## UAT (manual)

- [ ] On `staging`, log in as two users, with `data_shared` enabled on
      one via a direct API call (not the UI, since it's now hidden).
      Confirm neither the "Share my data" checkbox nor the "View: user"
      selector is visible anywhere in the Tamiyo Scroll UI.
- [ ] Call `GET /api/v1/tamiyo-scroll/personal-decks?owner_id=<shared-user>`
      directly with a valid token; confirm the backend still enforces the
      sharing rule correctly even though the UI entry point is gone.

## Non-regression tests

- Automated: new `SharingControls.test.tsx` (component-level, didn't
  exist before).
- Automated: rerun existing `test_ownership.py`/`test_settings.py`
  (pre-existing, backend untouched) — confirms no backend regression.
- Manual: every other `AppShell` control (deck selector, tabs) still
  renders and functions with the sharing block removed.
