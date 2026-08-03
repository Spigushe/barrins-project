# B4. Promote `staging` → `main`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | repo (branch promotion) | / |
| **Initial date** | 2026-07-23 | / |
| **Status** | ✅ Merged | PR #20 squash-merged into `main` (`ba54ef4`) |
| **Source** | Release checklist | / |
| **Dependency** | B3 | PR merged into `staging`, CI green |

---

## Tasks

- [X] Open a PR `staging` → `main` once B3 has landed and CI is green
      (PR #20).
- [X] Review the full diff before merging.
- [X] Squash-merge the PR into `main`.

## Done statement

PR merged, full CI (back/front/ops/docs jobs) green, diff contains only
what was planned (Phase A + B1, nothing else).

## UAT (manual)

- [X] Review the PR diff personally before approving the merge — this
      doubles as a final sanity check across every work item.

## Non-regression tests

The full CI suite passing on this PR **is** the cumulative regression
run — every job (`back`, `front`, `ops`, `docs`) triggered by the
combined diff must be green.
