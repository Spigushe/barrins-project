# B3. Promote `staging` → `main`

[← Back to project index](../index.md)

## Tasks

- [ ] Open a PR `staging` → `main` once B2 has landed and CI is green.
- [ ] Review the full diff before merging.

## Done statement

PR merged, full CI (back/front/ops/docs jobs) green, diff contains only
what was planned (Phase A + B1, nothing else).

## UAT (manual)

- [ ] Review the PR diff personally before approving the merge — this
      doubles as a final sanity check across every work item.

## Non-regression tests

The full CI suite passing on this PR **is** the cumulative regression
run — every job (`back`, `front`, `ops`, `docs`) triggered by the
combined diff must be green.
