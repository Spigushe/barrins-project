# T1. Barrin's Scripture — repo location & migration

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | New: `apps/barrins_scripture` (monorepo, rewrite per §1.1 Option 3) | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — §1.1 decided (Option 3) | / |
| **Source** | Request item 1; `v2.0.0-bump/index.md` §1.1 | / |
| **Dependency** | None (this is the first domino) | Blocks T2, T3 |

---

## Context

`mtg_scraper` (`barrins-project/mtg_scraper`, public) is a real, working
Python 3.13 scraper, its own repo with its own CI, versioning
(`CHANGELOG.md` at `0.2.0`), and a `scraped/` git submodule
(`mtg_decklist_cache`). §1.1 decided (2026-07-25) that
`apps/barrins_scripture` is a **new** implementation superseding
`mtg_scraper` (Option 3), archiving `mtg_scraper` once feature parity is
reached.

**Related, clarified by the user (2026-07-26): not a deadline, a given.**
The `barrins-project` GitHub org hosting both `mtg_scraper` and
`mtg_decklist_cache` will eventually be deleted — but only by the user's
own deliberate action, once this release has shipped and the org is no
longer needed. There's no race and no data-loss risk to mitigate: the
user won't delete it until the transfer below is done and confirmed.
**What this does mean for this item**: don't conclude
`mtg_decklist_cache` (or `mtg_scraper`) stays at its current
`barrins-project` name/location — both get transferred (full history
preserved, e.g. `git clone --mirror` + push) to a durable location (a
different org, or under the `Spigushe` account — **not yet specified**)
as a normal part of this item's own migration work, whenever there's
confidence to do so.

## Done statement

- Barrin's Scripture's new code lives at `apps/barrins_scripture` in
  this monorepo.
- `mtg_scraper` and `mtg_decklist_cache` are both transferred, full
  history intact, to a durable location outside `barrins-project`.
- CI adapted to this monorepo's `.github/workflows/CI.yml`
  `changes`/path-filter pattern (a new `scripture` filter + job,
  mirroring `back`/`front`).
- `mtg_scraper` is archived (pointing at its new, non-`barrins-project`
  location) once parity is confirmed: MTGO + MTGTop8 scraping, the same
  daily/biweekly-gap-check scheduling, same JSON-archive output (§1.3).
- No gap in scrape coverage throughout — the old scraper keeps running
  on its existing schedule until the new one is proven equivalent.

## Tasks

- [ ] Confirm the new durable location for `mtg_scraper`/
      `mtg_decklist_cache` with the user (a different GitHub org, or
      under `Spigushe`) — whenever this item reaches the point of doing
      the transfer, not on any particular deadline.
- [ ] Transfer both repos there (full history intact).
- [ ] Write `apps/barrins_scripture` from scratch (rewrite, per §1.1
      Option 3 — not a `git subtree`/history-preserving merge): MTGO +
      MTGTop8 scraping, same daily/biweekly-gap-check scheduling.
- [ ] Add a `scripture` path filter + CI job to `.github/workflows/CI.yml`
      (mirrors the existing `back`/`front` jobs' shape).
- [ ] Point the new implementation at `mtg_decklist_cache`'s new,
      durable location as the dump sub-repo per §1.3.
- [ ] Once feature parity is confirmed, archive `mtg_scraper` (at its
      new, non-`barrins-project` location), redirecting its README to
      `apps/barrins_scripture`, so contributors don't keep opening PRs
      against a retired repo.

## UAT (manual)

- [ ] Both repos exist at their new location with full history intact.
- [ ] A scheduled scrape run (daily or manual dispatch) completes
      successfully from `apps/barrins_scripture`, writing to the same
      (relocated) `mtg_decklist_cache` archive.

## Non-regression tests

- Existing `mtg_scraper` test/lint tooling (whatever exists today —
  `pyproject.toml`'s configured checks) is re-established for
  `apps/barrins_scripture`'s rewrite before this is considered done.
