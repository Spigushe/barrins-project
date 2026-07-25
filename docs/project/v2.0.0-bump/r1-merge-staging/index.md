# R1. Finalize release content, merge to `staging`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `proj/v2.0.0-bump` → `staging` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — last of the feature work | / |
| **Source** | Mirrors v1.0.0's B3 | / |
| **Dependency** | Every in-scope item from Groups T/S/F/D | Blocks R2 |

---

## Context

Same shape as v1.0.0's B3: once every in-scope work item for this
release has landed on `proj/v2.0.0-bump` and is green, this merges into
`staging`.

## Done statement

- Every in-scope item (confirmed scope, not necessarily every item
  listed in this plan — some, like T6/S2/S4/S5, may still be blocked or
  descoped by the time this runs) is merged into `proj/v2.0.0-bump` and
  green.
- `proj/v2.0.0-bump` merges cleanly into `staging`.

## Tasks

- [ ] Confirm final in-scope item list (some items in this plan may slip
      to a later release if their blocking decision isn't resolved in
      time — decide explicitly, don't let it happen silently).
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
