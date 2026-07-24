# B2. Finalize release content, merge `proj/v1.0.0-bump` → `staging`

[← Back to project index](../index.md)

## Context

Once every Phase A + B1 work item has landed on `proj/v1.0.0-bump` and CI
is green there, this item finalizes the release content and promotes the
branch into `staging`.

## Tasks

- [x] Cut the `[Unreleased]` section (split per A4 into per-sub-repo
      files) into `[1.0.0] - 2026-07-24` for the four sub-repos with
      actual v1.0.0 content (`apps/barrins_api`, `apps/tamiyo_scroll`,
      `docs`, `ops/my-server`). `apps/barrins_identity` and
      `apps/tolaria_news` are left as `[Unreleased] — Nothing yet.`
      since neither ships in this release (matches the "only sub-repos
      with actual changes appear" rule `sync_changelogs.py` already
      encodes).
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
- [ ] Confirm every work-item PR is merged into `proj/v1.0.0-bump` and CI
      is green.
- [ ] Open the PR `proj/v1.0.0-bump` → `staging`.

## Done statement

Every sub-repo `CHANGELOG.md` has an accurate `[1.0.0]` section; both
manifests read `1.0.0`; `proj/v1.0.0-bump` merged cleanly into `staging`.

## UAT (manual)

- [ ] Read each finalized `CHANGELOG.md`; confirm entries accurately
      reflect what's actually shipping in v1.0.0.
- [ ] Confirm both manifests read `1.0.0`.

## Non-regression tests

Docs-only change (plus the version bump) — confirm the `docs` CI job
stays green; no new automated test needed here.
