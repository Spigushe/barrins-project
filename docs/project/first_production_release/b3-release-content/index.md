# B3. Finalize release content, merge `proj/v1.0.0-bump` → `staging`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | monorepo-wide (all 6 sub-repos) | / |
| **Initial date** | 2026-07-23 | / |
| **Status** | 🟡 PR opened, not yet merged | `proj/v1.0.0-bump` → `staging` still 29 commits ahead as of last check |
| **Source** | Release checklist | finalize v1.0.0 content |
| **Dependency** | every Phase A + B1 + B2 item | must be merged into `proj/v1.0.0-bump` with CI green first; B2 (docs site deployment) sequenced before this item by choice |

---

## Context

Once every Phase A + B1 + B2 work item has landed on `proj/v1.0.0-bump`
and CI is green there, this item finalizes the release content and
promotes the branch into `staging`.

## Tasks

- [x] Cut the `[Unreleased]` section (split per A4 into per-sub-repo
      files) into `[1.0.0] "WorldWake" - 2026-07-24` across all six
      sub-repos. `apps/barrins_identity` and `apps/tolaria_news` carry
      no actual v1.0.0 content (neither ships in this release), but are
      still tagged `[1.0.0]` with their existing "Nothing yet." body —
      the tag reflects the state of the whole monorepo at release time,
      not just the sub-repos with new entries.
- [x] Bump `apps/barrins_api/pyproject.toml` (`0.3.0` → `1.0.0`,
      `Development Status :: 2 - Pre-Alpha` →
      `Development Status :: 5 - Production/Stable`) and
      `apps/tamiyo_scroll/package.json` (`0.0.0` → `1.0.0`). This was
      previously (incorrectly) assumed already done on `staging` — it
      isn't, so it's real work here.
- [x] Re-verify all three suites after the bump: backend
      (`uv run python scripts/workflow_ci.py --no-fix`, 237 passed,
      98.21% coverage), frontend (`npm run lint`/`build`/`test`, 54
      passed), docs (`npm run ci` equivalent — build clean, spellcheck
      clean on every changed file).
- [X] Confirm every work-item PR is merged into `proj/v1.0.0-bump` and CI
      is green.
- [X] Open the PR `proj/v1.0.0-bump` → `staging`.

## Done statement

Every sub-repo `CHANGELOG.md` has an accurate `[1.0.0]` section; both
manifests read `1.0.0`; `proj/v1.0.0-bump` merged cleanly into `staging`.

## UAT (manual)

- [X] Read each finalized `CHANGELOG.md`; confirm entries accurately
      reflect what's actually shipping in v1.0.0.
- [X] Confirm both manifests read `1.0.0`.

## Non-regression tests

Docs-only change (plus the version bump) — confirm the `docs` CI job
stays green; no new automated test needed here.
