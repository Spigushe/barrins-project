# T6. Karn Tablets — basic modeling: metagame clustering & deck-type aggregation

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/karn_tablets` (new, real basic ML/aggregation component) | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — §1.4 resolved 2026-07-26, real scope confirmed | / |
| **Source** | Request item 1; `v2.0.0-bump/index.md` §1.4 | / |
| **Dependency** | I4 (resolved), T2, T3 (real scraped-tournament data to cluster) | Blocks T8 (its playbook) |

---

## Context

§1.4 originally recommended scoping Karn Tablets to a placeholder for
v2.0.0 — that recommendation is **superseded**: the user confirmed
(2026-07-26) that Karn Tablets ships real, if deliberately basic,
functionality this release. This item's slug (`t6-karn-tablets-scaffold`)
predates that decision and is kept for link stability; it no longer
describes a placeholder-only scope.

Decided scope, restated from `../index.md` §1.4:

- **Clustering** the metagame (deck archetypes seen in scraped tournament
  results) over a defined time window.
- **Aggregation** of that clustering output to visualize **deck-type**
  distribution.
- "Predictions" was named but not further specified — treated as
  follow-on work once deck-type clusters exist, not a v2.0.0 deliverable
  in itself.

This depends on **real data**, not just the schema: T2 designs the
`bs_*` scraped-tournament schema (Barrin's Scripture naming, decided
2026-07-26), but Karn Tablets needs T3's ingestion
pipeline to have actually populated it before clustering can run against
anything real (fixture/synthetic data can unblock early development, but
not the UAT step below).

## Two open sub-decisions, not yet narrowed (flagged, not guessed)

1. **Windowing strategy.** The user named two candidate approaches
   without picking a single default:
   - Rolling 30-day window (always the most recent 30 days as of the
     run date).
   - Banlist-period window: non-overlapping periods from the **last
     Tuesday of an odd-numbered month** to the **last Monday of the
     following odd-numbered month** (e.g. last Tuesday of March → last
     Monday of May), aligned to Magic's Banned & Restricted announcement
     rhythm.
   Whether v2.0.0 ships one (and which) or both needs confirming before
   implementation.
2. **Consumption surface.** Where the deck-type aggregation is actually
   shown (a new admin-only view, folded into S6's metrics dashboard, a
   Tolaria News page, or an internal-only report) is not specified by
   the request. Not guessed here — needs confirmation before the
   frontend/exposure side of this item is designed.

## Done statement

- `apps/karn_tablets` exists with a real pipeline (shape — scheduled job
  vs. small service with a results API — is T8/D1's call, informed by
  the consumption-surface decision above) that:
  - Reads deck/tournament data from the `bs_*` schema (T2) once T3 has
    populated it.
  - Clusters decks into archetypes over the confirmed window(s).
  - Aggregates cluster output into a deck-type distribution.
- Follows Constitution §45.1 (Karn Tablets stays isolated from frontend/
  auth/reports/core domain — no direct coupling) and §45.2 (validated
  data, a reproducible pipeline, a documented dataset; every result
  records its source data range, pipeline version, and model/algorithm
  info).
- Any new dependency this needs (a clustering library, etc.) is chosen
  through the standard §4.7/§22 approval process (problem, alternatives,
  maintenance impact) — not pre-selected here, per the user's own note
  that tooling changes get documented to match the constitution rather
  than assumed.
- `apps/karn_tablets/README.md`/`CHANGELOG.md` describe the real scope
  above, replacing any placeholder-only wording.

## Tasks

- [ ] Confirm the windowing default (rolling 30-day, banlist-period, or
      both) with the user.
- [ ] Confirm the consumption surface (where deck-type aggregation is
      shown) with the user.
- [ ] Choose a clustering approach/library via §4.7/§22's
      dependency-approval process.
- [ ] Implement the banlist-period boundary calculation (last Tuesday of
      an odd month → last Monday of the following odd month) as a
      standalone, tested utility — this is the part most likely to have
      off-by-one/edge-case bugs (year rollover, month-length edge cases).
- [ ] Build the clustering pipeline reading from `bs_*` (T2/T3).
- [ ] Build the deck-type aggregation step.
- [ ] Attach §45.2's required metadata (source data range, pipeline
      version, model/algorithm info) to every computed result.
- [ ] Write real `README.md`/`CHANGELOG.md` content.

## UAT (manual)

- [ ] Trigger a clustering run against real (or staging) scraped-
      tournament data; confirm the resulting deck-type aggregation
      roughly matches a manual sanity check against known meta decks for
      that window.
- [ ] If both windowing modes are built, confirm switching modes changes
      which matches are included in the clustering input.

## Non-regression tests

- Unit tests for the banlist-period boundary calculation, covering
  month/year-rollover edge cases (e.g. the last odd month of the year,
  December → January rollover).
- Pipeline tests against fixture tournament data with a known expected
  archetype grouping, asserting the aggregation output matches.
- A test asserting every clustering result carries the §45.2 metadata
  (source data range, pipeline version, model info) — a regression
  guard, not just a one-time check.
