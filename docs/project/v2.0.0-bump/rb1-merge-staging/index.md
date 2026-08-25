# RB1. Confirm alpha.2 scope, decide version-bump convention, merge to `staging`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `feat/tamiyo-scroll-alpha2` → `staging` | / |
| **Initial date** | 2026-08-25 | In progress |
| **Status** | 🟡 In progress — scope confirmed and changelogs bumped 2026-08-25; PR #83 open, CI green, mergeable; not yet merged | / |
| **Source** | §1.12 | / |
| **Dependency** | S4, S8, S13, S14, S15, S16, S17 (all done) | Blocks RB2 |

---

## Context

`feat/tamiyo-scroll-alpha2` branches directly off `staging`'s current
head (confirmed via `git merge-base --is-ancestor staging
feat/tamiyo-scroll-alpha2`) — unlike RA1's `feat/v2-tamiyo-upgrade`,
which went through `proj/v2.0.0-bump` first. There is no intermediate
integration branch to merge through this time: `git diff --stat
staging...feat/tamiyo-scroll-alpha2` confirms the branch touches only
`apps/barrins_api`, `apps/tamiyo_scroll`, `docs/`, and
`ops/my-server` (the new MTGJSON scheduled-refresh timer role) — no
Group T file anywhere. Because `staging` is a direct ancestor, this
merge can be a fast-forward — no conflict resolution expected, same as
RA1's merge into `proj/v2.0.0-bump` was.

## Done statement

- Final in-scope item list for `v2.0.0-alpha.2` confirmed explicitly:
  S4, S8, S13, S14, S15, S16, S17. S18 (the rest of the delete-defaults-
  to-archive audit S17 started) confirmed still out — not started. Every
  Group T item confirmed out, as with alpha1, but this time by
  construction rather than an explicit "ride along inert" carve-out.
- Version-bump convention for this cut decided (§1.12: `v2.0.0-alpha.2`,
  SemVer dot-separated pre-release numbering, correcting alpha1's
  un-numbered `v2.0.0-alpha`) and applied to every affected
  `CHANGELOG.md`.
- `feat/tamiyo-scroll-alpha2` merged into `staging`.

## Tasks

- [x] Decide the version-bump convention (§1.12) and apply it: root
      `docs/CHANGELOG.md`, `apps/tamiyo_scroll/CHANGELOG.md`,
      `apps/barrins_api/CHANGELOG.md`, converting each `[Unreleased]`
      heading to `[2.0.0-alpha.2] - 2026-08-25` — same two-app-plus-root
      scope RA1 decided (`barrins_scripture`/`tolaria_news`/
      `barrins_identity` stay at `[Unreleased]`, nothing to log there).
      **Done 2026-08-25.** Same pass: filled in three items that had
      never been logged in any `CHANGELOG.md` — S8's MTGJSON pipeline
      (models, import route, scheduled-refresh service token), T6's
      `mj_cards` text/keyword/stat columns, and F10 (metagame roster
      scoped to the active personal deck, shipped 2026-08-18 but never
      written up) — same doc-sync-gap pattern RA1 hit for S6/S10/S11.
- [ ] Re-verify no new commits landed on `staging` since the
      `git merge-base` check this plan was written against — re-run
      `git merge-base --is-ancestor staging feat/tamiyo-scroll-alpha2`
      immediately before merging.
- [x] Open PR #83 into `staging` per the branch-protection rule added in
      F9 (`gh pr list --head feat/tamiyo-scroll-alpha2`). **Confirmed
      2026-08-25**: `baseRefName: staging`, `mergeStateStatus: CLEAN`,
      `mergeable: MERGEABLE`. All checks green on HEAD (`2aa6c75`) —
      `ci-required`/`ops`/`back`/`front`/`docs`/`changes` all `success`,
      `scripture` `skipped` (expected, no Barrin's Scripture files
      touched).
- [ ] Merge `feat/tamiyo-scroll-alpha2` → `staging` (fast-forward
      expected).
- [ ] Confirm CI is green on `staging` post-merge.

## UAT (manual)

- [ ] Full test suite green on `staging` post-merge (backend, frontend,
      ops lint, docs build).

## Non-regression tests

- Whatever cumulative coverage threshold this release adopts (v1.0.0
  used ≥60% across `barrins_api`/`tamiyo_scroll`; check the current
  suite's reported percentage post-merge) — confirm it still holds.
