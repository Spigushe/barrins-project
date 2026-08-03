# R1. Finalize release content, merge to `staging`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `proj/v2.0.0-bump` → `staging` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — last of the feature work | / |
| **Source** | Mirrors v1.0.0's B3 | / |
| **Dependency** | Every in-scope item from Groups T/S/F/D, **and R5** (added 2026-07-26) | Blocks R2 |

---

## Context

Same shape as v1.0.0's B3: once every in-scope work item for this
release has landed on `proj/v2.0.0-bump` and is green, this merges into
`staging`.

**Added 2026-07-26 (§3.1)**: R5's ADRs are now a hard prerequisite of
this merge, not independent trailing work. v1.0.0 wrote ADR-4 (and
several "done" confirmations) directly on `main` after its squash-merge
— those commits never existed on `staging`, and reconciling them cost
two dedicated follow-up PRs (`6821380`, `9fa40bf`). This time, R5 must
already be merged into `proj/v2.0.0-bump` before this step runs.

## Done statement

- Every in-scope item (confirmed scope, not necessarily every item
  listed in this plan — some, like S2/S4/S5/S8, may still be blocked or
  descoped by the time this runs) is merged into `proj/v2.0.0-bump` and
  green.
- Every ADR from R5 is merged into `proj/v2.0.0-bump` as well.
- `proj/v2.0.0-bump` merges cleanly into `staging`.

## Tasks

- [ ] Confirm final in-scope item list (some items in this plan may slip
      to a later release if their blocking decision isn't resolved in
      time — decide explicitly, don't let it happen silently).
- [ ] Confirm R5's ADRs are merged into `proj/v2.0.0-bump` — do not
      proceed if any are still pending (§3.1).
- [ ] Version bump across every `CHANGELOG.md` (root + per-app), same
      convention as v1.0.0's B3.
- [ ] Merge to `staging`.

## UAT (manual)

- [ ] Full test suite green on `staging` post-merge (backend, frontend,
      ops lint, docs build).

## Non-regression tests

- Whatever cumulative coverage threshold this release adopts (v1.0.0
  used ≥60% across `barrins_api`/`tamiyo_scroll`) — confirm it still
  holds after the merge.
