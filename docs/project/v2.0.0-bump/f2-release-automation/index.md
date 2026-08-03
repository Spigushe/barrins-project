# F2. Automate release cutting

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | GitHub Actions (new workflow), or a documented manual checklist | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — should fix, not blocking | / |
| **Source** | `docs/content/ops/roadmap.md` (carried from v1.0.0), ADR-2 | / |
| **Dependency** | None | / |

---

## Context

ADR-2 flagged this from the start: production only ever deploys a
GitHub Release tag (never a branch), but cutting that tag/release is
still fully manual. More apps sharing one monorepo tag (this release
adds up to three) makes the manual process more error-prone, not less.

## Done statement

- Either a GitHub Actions workflow that cuts a release (tag + GitHub
  Release notes, likely triggered on a version bump commit to `main`),
  or, if automating fully is judged out of scope for this release, a
  written, followed checklist reducing the chance of a mis-tagged
  release across more apps.

## Tasks

- [ ] Decide scope: full automation vs. a documented checklist
      improvement for this release (escalate — this is real process
      change, Constitution §16.2).
- [ ] If automating: design the trigger (manual `workflow_dispatch`
      vs. automatic on `main` push) and the release-notes source
      (aggregate `CHANGELOG.md`s, matching the existing per-app
      changelog-split convention).

## UAT (manual)

- [ ] Cut a real release (this release's own tag) using whatever the
      new process is; confirm the GitHub Release and tag are correct.

## Non-regression tests

- N/A (process/tooling item).
