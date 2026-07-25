# T1. Barrin's Scripture — repo location & migration

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | New: `apps/barrins_scripture` (monorepo) or a renamed standalone repo | Depends on §1.1 |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — cannot start until §1.1 is decided | / |
| **Source** | Request item 1; `v2.0.0-bump/index.md` §1.1 | / |
| **Dependency** | None (this is the first domino) | Blocks T2, T3 |

---

## Context

`mtg_scraper` (`barrins-project/mtg_scraper`, public) is a real, working
Python 3.13 scraper, its own repo with its own CI, versioning
(`CHANGELOG.md` at `0.2.0`), and a `scraped/` git submodule
(`mtg_decklist_cache`). The request asks for it to live "under
`apps/barrins_scripture`" — inside this monorepo, the same pattern
`apps/tolaria_news` already follows. Three migration shapes are laid out
as alternatives in `v2.0.0-bump/index.md` §1.1 (merge with history,
rename-in-place and reference externally, or a from-scratch rewrite) —
**not decided**.

## Done statement (once §1.1 is decided)

- Barrin's Scripture's code lives at the location §1.1 settles on.
- If merged into the monorepo: git history preserved (no `git init`
  from a zip of the old repo), CI adapted to this monorepo's
  `.github/workflows/CI.yml` `changes`/path-filter pattern (a new
  `scripture` filter + job, mirroring `back`/`front`).
- If kept external: a documented reference from this repo (README link,
  `docs/content/back/barrins_scripture/` pointing at it) rather than a
  silent, undocumented split.
- `mtg_scraper`'s existing scheduled scraping (`daily_scraping.yml`,
  `biweekly_check_gaps.yml`) keeps working throughout the migration — no
  gap in scrape coverage.

## Tasks

- [ ] Get §1.1 decided (escalation, not implementation work).
- [ ] If "merge into monorepo" is chosen: `git subtree add` (or
      `git filter-repo` + merge) preserving `mtg_scraper`'s commit
      history under `apps/barrins_scripture/`.
- [ ] Add a `scripture` path filter + CI job to `.github/workflows/CI.yml`
      (mirrors the existing `back`/`front` jobs' shape).
- [ ] Decide `mtg_decklist_cache`'s fate alongside this (kept as an
      external submodule either way, per §1.3 — not itself blocked by
      §1.1's outcome).
- [ ] Archive or repoint `barrins-project/mtg_scraper`'s own README once
      the new location is live, so contributors don't keep opening PRs
      against a retired repo.

## UAT (manual)

- [ ] A scheduled scrape run (daily or manual dispatch) completes
      successfully from the new location, writing to the same
      `mtg_decklist_cache` archive as before the migration.
- [ ] `git log` on the migrated path (if merged) shows the original
      `mtg_scraper` history, not a single "initial import" commit.

## Non-regression tests

- Existing `mtg_scraper` test/lint tooling (whatever exists today —
  `pyproject.toml`'s configured checks) still passes from the new
  location before this is considered done.
