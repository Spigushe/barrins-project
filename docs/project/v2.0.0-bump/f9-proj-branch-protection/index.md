# F9. Branch protection & CI coverage for `proj/*` branches

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `.github/workflows/CI.yml`, GitHub repo ruleset settings | / |
| **Initial date** | / | Not started |
| **Status** | 🟡 Verified — ruleset live, CI trigger + direct-push rejection both confirmed; pending merge of PR #23 | / |
| **Source** | Carried over from v1.0.0 as an open item; decided this release | / |
| **Dependency** | None | Should land early — every `proj/*` PR this release benefits from it |

---

## Context

v1.0.0's plan already flagged "confirm `.github/workflows/CI.yml`
triggers on PRs targeting `proj/*`" as an open item, never resolved.
**Verified 2026-07-26**: it's still open —

```yaml
on:
  pull_request:
    branches: [staging, main]
  push:
    branches: [staging, main]
```

`proj/*` branches (including this release's own `proj/v2.0.0-bump` and
any sub-branches under it) get **no CI run** on their own PRs today —
every PR merging into `proj/v2.0.0-bump` is currently unverified by CI
until it eventually reaches `staging`. Separately, no GitHub
branch-protection ruleset covers `proj/*`, so "PRs mandatory, no direct
pushes" for `proj/*` is a convention this plan states (§3) but nothing
actually enforces.

## Done statement

- `.github/workflows/CI.yml`'s `pull_request`/`push` triggers include
  `proj/**` (or an equivalent pattern matching `proj/v2.0.0-bump` and
  any sub-branches), alongside the existing `staging`/`main`.
- A GitHub branch-protection ruleset exists for `proj/*` branches,
  mirroring `staging`'s existing required-review/required-status-check
  rules, so direct pushes are actually rejected, not just discouraged by
  convention.

## Tasks

- [x] Add `proj/**` to `CI.yml`'s `pull_request`/`push` branch filters
      (`fix(ci): trigger CI on proj/* branches`, PR #23, not yet merged).
- [x] Confirm the `changes`/path-filter jobs (back/front/ops/docs) still
      behave correctly against `proj/*` PRs — verified on PR #23:
      `changes` ran, `back`/`front`/`ops`/`docs` correctly skipped
      (only `CI.yml` changed), `ci-required` completed successfully.
- [x] Create or extend a GitHub ruleset covering `proj/*`, matching
      `staging`'s existing protection rules —
      `proj-release-branch-protection` (ruleset id `19839693`) created,
      `enforcement: active`, rules identical to `staging`'s
      `preprod-staging-protection` apart from the ref pattern
      (`refs/heads/proj/**`).
- [x] Confirm on a real `proj/v2.0.0-bump` PR that CI now runs — done via
      PR #23.
- [x] Confirm a direct push to `proj/v2.0.0-bump` is rejected by the new
      ruleset — confirmed: GitHub returned `GH013: Repository rule
      violations` ("Changes must be made through a pull request",
      "Required status check \"ci-required\" is expected") on a direct
      push attempt.

## UAT (manual)

- [x] Open a test PR into `proj/v2.0.0-bump`; confirm CI runs
      automatically — PR #23, `ci-required` succeeded.
- [x] Attempt a direct push to `proj/v2.0.0-bump`; confirm it's rejected
      by the new ruleset — confirmed rejected (`GH013`).

## Non-regression tests

- Confirm existing `staging`/`main` CI triggers and rulesets are
  unaffected (this only adds `proj/*` coverage, doesn't change existing
  behavior).
