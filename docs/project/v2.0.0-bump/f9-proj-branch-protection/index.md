# F9. Branch protection & CI coverage for `proj/*` branches

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `.github/workflows/CI.yml`, GitHub repo ruleset settings | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — decided 2026-07-26 (§3) | / |
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

- [ ] Add `proj/**` to `CI.yml`'s `pull_request`/`push` branch filters.
- [ ] Confirm the `changes`/path-filter jobs (back/front/ops/docs) still
      behave correctly against `proj/*` PRs (no assumption baked in that
      only applies to `staging`/`main`).
- [ ] Create or extend a GitHub ruleset covering `proj/*`, matching
      `staging`'s existing protection rules.
- [ ] Confirm on a real `proj/v2.0.0-bump` sub-branch PR that CI now
      runs and a direct push to `proj/v2.0.0-bump` is rejected.

## UAT (manual)

- [ ] Open a test PR into `proj/v2.0.0-bump`; confirm CI runs
      automatically.
- [ ] Attempt a direct push to `proj/v2.0.0-bump`; confirm it's rejected
      by the new ruleset.

## Non-regression tests

- Confirm existing `staging`/`main` CI triggers and rulesets are
  unaffected (this only adds `proj/*` coverage, doesn't change existing
  behavior).
