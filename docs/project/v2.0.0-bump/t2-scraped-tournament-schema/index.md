# T2. Scraped-tournament domain model in `barrins_api`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` | New domain, `bs_`-prefixed (Barrin's Scripture) — decided 2026-07-26 |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — unblocked, §1.2/I3 decided 2026-07-25 (Option 2 + maintenance-mode gate) | / |
| **Source** | Request item 1; `v2.0.0-bump/index.md` §0, §1.2 | / |
| **Dependency** | I3 (§1.2) | Blocks T3, T4 |

---

## Context

`docs/content/back/barrins_api/bff/tamiyo_scroll.md` and several code
comments reference a `dl_decks`/`dl_tournaments` domain and a
`docs/decklist_integration/` design doc as if they already existed —
**verified during this planning process that neither exists anywhere in
the repository** (see `v2.0.0-bump/index.md` §0 and item F7). This
domain is genuinely new work, not a resurrection of hidden code, and its
final shape depends on §1.2's outcome (does Barrin's Scripture write
directly, or through an ingestion route owned by `barrins_api`?).

**Naming, decided 2026-07-26**: this domain is `bs_`-prefixed (Barrin's
Scripture), not `dl_` — `dl_` was only ever the name used by the dead
`docs/decklist_integration/` reference (F7), never an established
convention, and `bs_` matches the project's existing per-app two-letter
prefix pattern (`ts_` for Tamiyo Scroll).

## Done statement (once §1.2 is decided)

- ORM models for tournaments/decks/standings exist under
  `app/models/`, `bs_`-prefixed (mirroring the `ts_` convention already
  used for Tamiyo Scroll), with an Alembic migration.
- The schema accommodates the JSON archive's existing shape
  (`mtg_decklist_cache`'s per-tournament JSON files) without requiring a
  lossy transform — a replay of the archive should be able to
  reconstruct the table contents.
- If §1.2 chose the ingestion-route option: the models are owned and
  migrated exclusively by `barrins_api`; Barrin's Scripture never runs
  its own migration against this schema.

## Tasks

- [ ] Get §1.2 decided (escalation, not implementation work).
- [ ] Design the `bs_*` table set from a real sample of
      `mtg_decklist_cache`'s JSON shape (inspect actual files, don't
      guess the schema from the scraper's Pydantic models alone —
      `scraper/schemas/{tournament,deck,standing,player,round}.py` in
      `mtg_scraper` are the closest existing reference).
- [ ] Write the Alembic migration.
- [ ] Write the fictitious `docs/decklist_integration/00_plan_general.md`
      referenced by existing docs, or update those references — ties
      into F7's decision (recreate vs. redirect).

## UAT (manual)

- [ ] Load a real sample of `mtg_decklist_cache` JSON files through
      whatever ingestion path §1.2 chose; confirm the resulting rows
      match the source files field-for-field.

## Non-regression tests

- New model/migration tests, following the existing
  `tests/tamiyo_scroll/` structure as precedent (one test module per
  domain concern).
