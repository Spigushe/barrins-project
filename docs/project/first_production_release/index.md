# v1.0.0 — First Production Release

**Project orientation for the upcoming days/weeks.** This document is the
foundation for every work item below — read it before picking up any
individual item's page.

Internal project tracking, not part of the public docs site
(`docs.barrins-codex.org`): this directory lives outside `docs/content/`
(mkdocs' `docs_dir`), so it isn't built or published, only version
controlled and reviewed via PR like any other doc.

## Context

This is the first-ever production release of the Barrin's ecosystem
monorepo. `origin/main` currently contains only the initial GitHub Pages
scaffold — no application code has ever reached production, and no git
tag exists yet.

ADR-2 (`docs/content/ops/architecture/decisions.md`) already defines the
deploy mechanism: production always deploys the latest GitHub Release tag
of this monorepo. ADR-2 flags two open gaps this release closes: no
release has ever been cut, and cutting one is currently a manual process
(automating that remains out of scope, tracked separately in ADR-2).

Scope decisions:

1. **`barrins_identity` is excluded from v1.0.0.** It's mid-implementation
   on `feat/barrins-identity`, not merged into `staging`. v1.0.0 ships
   `staging` as it stands: `barrins_api` + `tamiyo_scroll`.
2. **The documented backup gap is a release blocker.**
   `docs/content/ops/operations/index.md` documents that PostgreSQL has
   no backup/verified-restore process today, and Constitution §36 is
   explicit that "a backup that has never been tested is not considered
   reliable."
3. **Six pre-release items must land before the version bump is tagged**:
   monitoring/health, extracting the immature "sharing" feature, a new
   Moxfield deck-import feature, splitting the changelog per app, a
   Tamiyo Scroll deck-selector UX rewrite, and a README rewrite.
4. The version bump itself (`0.3.0`/`0.0.0` → `1.0.0`) is real, not-yet-done
   work — an earlier check during planning mistakenly read an uncommitted
   working-tree edit as if it were already committed on `staging`. It
   isn't; the bump happens in **B2**.

## Branch strategy

All work aggregates on the integration branch **`proj/v1.0.0-bump`**,
branched off `staging`. Each work item below is its own branch/PR merging
into `proj/v1.0.0-bump`. Once every item is in and green, this branch
merges into `staging` (B2), which then promotes to `main` (B3), gets
tagged (B4), and deployed (B5).

**Open item**: `.github/workflows/CI.yml` currently only triggers on PRs
targeting `staging`/`main` — PRs into `proj/v1.0.0-bump` won't
auto-trigger CI as configured today. Either temporarily add this branch
to the workflow's trigger list, or run the equivalent local scripts per
PR review (`uv run python scripts/workflow_ci.py --no-fix` for backend,
`npm run lint`/`build`/`test` for frontend, `npm run ci` for docs).
Not decided yet — confirm before the first work-item PR.

## Work items

| # | Item | Page |
| --- | --- | --- |
| A1 | Monitoring and `/health` | [a1-monitoring-health/](a1-monitoring-health/index.md) |
| A2 | Extract and disable the "sharing" feature | [a2-sharing-extraction/](a2-sharing-extraction/index.md) |
| A3 | Moxfield deck-import feature | [a3-moxfield-import/](a3-moxfield-import/index.md) |
| A4 | Split the changelog per app | [a4-changelog-split/](a4-changelog-split/index.md) |
| A5 | Deck-selector rewrite (combobox) | [a5-deck-selector-ux/](a5-deck-selector-ux/index.md) |
| A6 | Root README rewrite | [a6-readme-rewrite/](a6-readme-rewrite/index.md) |
| B1 | `postgres_backup` Ansible role | [b1-postgres-backup/](b1-postgres-backup/index.md) |
| B2 | Finalize release content, merge to `staging` | [b2-release-content/](b2-release-content/index.md) |
| B3 | Promote `staging` → `main` | [b3-promote-main/](b3-promote-main/index.md) |
| B4 | Tag and cut the release | [b4-tag-release/](b4-tag-release/index.md) |
| B5 | Deploy from tag (production) | [b5-deploy-production/](b5-deploy-production/index.md) |
| B6 | Document the decision (ADR-3) | [b6-adr-commit/](b6-adr-commit/index.md) |

## How each work item's page is structured

Every page under a work item follows the same four sections:

1. **Done statement** — concrete acceptance criteria.
2. **Tasks** — the implementation breakdown.
3. **UAT** — manual steps performed personally by the user to confirm the
   change is applied correctly. A work item isn't done until its UAT has
   actually been run, not just written down.
4. **Non-regression tests** — systematic tests added for this item.

Two rules apply across every item's non-regression tests:

- **No duplicate tests.** No work item may reuse a non-regression test
  already introduced by an earlier item — every item's tests are net-new.
- **Cumulative coverage ≥60%.** After each work item, `pytest --cov`
  (`barrins_api`) and `vitest --coverage` (`tamiyo_scroll`) must show a
  running total of at least 60% — checked and reported at each item's
  completion, not only once at the end.
