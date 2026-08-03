# RA2. Merge `proj/v2.0.0-bump` → `staging`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `proj/v2.0.0-bump` → `staging` | / |
| **Initial date** | / | Not started |
| **Status** | 🟡 In progress — PR #46 (`proj/v2.0.0-bump` → `staging`) hit a real, structurally-recurring conflict (`recharts`/`uv.lock`, see Proposal 7); closed and replaced by #49 (`release/v2.0.0-alpha` → `staging`), built with `staging` as a real ancestor per Proposal 7's workaround | / |
| **Source** | Mirrors R1/v1.0.0's B3, scoped to the alpha cut (§1.11) | / |
| **Dependency** | RA1 | Blocks RA3 |

---

## Context

Same shape as R1, at the alpha's smaller scope. `proj/v2.0.0-bump` at
this point still carries T1/T2 (already merged, riding along inert per
§1.11) plus every RA1-confirmed Group S item — nothing from Group T's
remaining items (T3–T8), which stay on `proj/v2.0.0-bump` for the later,
full `v2.0.0` merge and are not part of this step.

**Applies the same §3.1 lesson v1.0.0 learned the hard way**: nothing
about *this* release's release-tracking docs should end up committed
directly to `main` after a squash-merge — anything that can be finalized
now (this document's own status updates) lands here, on `staging`, before
RA3 promotes to `main`.

**What actually happened (2026-08-03), not what was planned above**: the
first attempt (PR #46, `proj/v2.0.0-bump` → `staging` directly) showed
`mergeable: CONFLICTING` — `staging`'s own dependabot bumps
(`@radix-ui/react-tabs` #34, others) landed after `proj/v2.0.0-bump`
branched off, conflicting with `apps/tamiyo_scroll/package.json`/
`package-lock.json` and `apps/barrins_api/uv.lock`. Two sync attempts
into `proj/v2.0.0-bump` (#47, then #48 — the second a no-op, confirming
the first already fully reconciled the *content*) did **not** clear
PR #46's conflict, because this repository's squash-only branch
protection never advances the git merge-base between two long-lived
branches — see [`../consitution-amendment.md`](../consitution-amendment.md)
**Proposal 7** for the full mechanism. The fix: PR #46 was closed, and a
new branch (`release/v2.0.0-alpha`) was built by merging
`proj/v2.0.0-bump` **into** `staging` (the reverse direction), making
`staging` a real ancestor of the result — PR **#49** from that branch
computed as a clean, conflict-free diff. #49, not #46, is this item's
actual merge PR.

## Done statement

- `proj/v2.0.0-bump`, with RA1's merge included, merges cleanly into
  `staging`.
- This document (`v2.0.0-bump/index.md`) and the touched Group S pages
  (S6, S10, S11) are part of that merge, not a follow-up patch.

## Tasks

- [ ] Confirm RA1 is fully merged and CI is green on `proj/v2.0.0-bump`.
- [ ] Merge `proj/v2.0.0-bump` → `staging`.
- [ ] Confirm CI is green on `staging` post-merge.

## UAT (manual)

- [ ] Full test suite green on `staging` post-merge (backend, frontend,
      ops lint, docs build).

## Non-regression tests

- Same cumulative coverage threshold as RA1 — confirm it still holds.
