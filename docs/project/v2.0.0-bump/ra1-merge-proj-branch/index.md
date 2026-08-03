# RA1. Confirm alpha scope, decide version-bump convention, merge to `proj/v2.0.0-bump`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `feat/v2-tamiyo-upgrade` → `proj/v2.0.0-bump` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started | / |
| **Source** | §1.11 | / |
| **Dependency** | Every done Group S item (S1, S2, S3, S5, S6, S7, S9, S10, S11, S12) | Blocks RA2 |

---

## Context

`feat/v2-tamiyo-upgrade` branches directly off `proj/v2.0.0-bump`'s
current head (confirmed via `git merge-base --is-ancestor
proj/v2.0.0-bump feat/v2-tamiyo-upgrade`) and carries every done Group S
commit on top, touching only `apps/tamiyo_scroll` and `apps/barrins_api`
(confirmed via `git diff --stat`). Because `proj/v2.0.0-bump` is a direct
ancestor, this merge can be a fast-forward — no conflict resolution
expected.

## Done statement

- Final in-scope item list for `v2.0.0-alpha` confirmed explicitly: S1,
  S2, S3, S5, S6, S7, S9, S10, S11, S12. S4 and S8 confirmed still out
  (both depend on MTGJSON data, deferred to the full v2.0.0).
- Version-bump convention for this cut decided (see open question
  below) and applied to every affected `CHANGELOG.md`.
- `feat/v2-tamiyo-upgrade` merged into `proj/v2.0.0-bump`.

## Tasks

- [ ] Re-verify no new commits landed on either branch since the
      `git merge-base` check this plan was written against — re-run
      `git merge-base --is-ancestor proj/v2.0.0-bump
      feat/v2-tamiyo-upgrade` immediately before merging.
- [x] Decide the version-bump convention (open question below) and apply
      it: root `docs/CHANGELOG.md`, `apps/tamiyo_scroll/CHANGELOG.md`,
      `apps/barrins_api/CHANGELOG.md`, and — depending on the answer —
      `apps/barrins_scripture/CHANGELOG.md` / `apps/tolaria_news/
      CHANGELOG.md`, converting each `[Unreleased]` heading to
      `[2.0.0-alpha]` with today's date (same convention v1.0.0's B3
      used, mind the heading-level bug tracked as **F3**). **Done
      2026-08-03**: `apps/tamiyo_scroll/CHANGELOG.md` and
      `apps/barrins_api/CHANGELOG.md` bumped to `[2.0.0-alpha] -
      2026-08-03`; `docs/CHANGELOG.md` gained its own `[2.0.0-alpha]`
      entry (the `docs/mkdocs.yml`/`docs/cspell.json` changes since
      v1.0.0 that had never been logged); `apps/barrins_scripture/
      CHANGELOG.md` and `apps/tolaria_news/CHANGELOG.md` stay at
      `[Unreleased]` per the decision above. Same pass: both bumped
      files' `[Unreleased]`→`[2.0.0-alpha]` content was also **filled
      in** — S6, S10, S11, and S12 had no entries at all (the
      changelogs had fallen behind the same way the S6/S10/S11 project
      pages had, §0's 2026-08-03 doc-sync note), plus two undocumented
      fixes (`GET /meta-decks` 422 on a shared roster; the decklist
      legend swatch color). `apps/barrins_identity/CHANGELOG.md` and
      `ops/my-server/CHANGELOG.md` intentionally left untouched — no
      Tamiyo-Scroll-scoped changes to log there, and they're outside
      the two-app bump decision.
- [ ] Merge `feat/v2-tamiyo-upgrade` → `proj/v2.0.0-bump` (fast-forward
      expected; open a PR regardless per the `proj/*` branch-protection
      rule added in F9).
- [ ] Confirm CI is green on `proj/v2.0.0-bump` post-merge.

## Open question: version-bump scope

v1.0.0 used **one version number shared across the monorepo** (every app
at `1.0.0`, §0). Does `v2.0.0-alpha` continue that convention — bumping
every app's `CHANGELOG.md`, including `apps/barrins_scripture` and
`apps/tolaria_news` which have no user-facing deploy this cut — or only
the two apps that actually changed (`barrins_api`, `tamiyo_scroll`)?
Not decided in §1.11; decide explicitly here rather than defaulting
silently either way.

> **Decision:** Bump only the two apps that actually changed (`barrins_api`,
> `tamiyo_scroll`), leaving the other two apps' `CHANGELOG.md` at `[Unreleased]`
> for now. The monorepo's root `CHANGELOG.md` will still be bumped to
> `[2.0.0-alpha]` to reflect the overall release.

## UAT (manual)

- [ ] Full test suite green on `proj/v2.0.0-bump` post-merge (backend,
      frontend, ops lint, docs build).

## Non-regression tests

- Whatever cumulative coverage threshold this release adopts (v1.0.0
  used ≥60% across `barrins_api`/`tamiyo_scroll`) — confirm it still
  holds after the merge.
