# T6. Karn Tablets — basic modeling: metagame clustering & deck-type aggregation

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/karn_tablets` (new, real basic ML/aggregation component) | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — §1.4 resolved 2026-07-26, real scope confirmed. Consumption surface, windowing, format scope, and data-flow shape resolved 2026-08-11 (ADR-13) | / |
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

## Sub-decisions, resolved 2026-08-11 (ADR-13)

Both items below were previously open, flagged as needing the user's
confirmation before implementation. Resolved together while planning the
full Tolaria News BFF (`docs/project/v2.0.0-bump/t4-tolaria-news-bff/`
iteration 2) — see
[ADR-13](../../../content/ops/architecture/decisions.md#adr-13-karn-tablets-output--data-flow-scope-and-consumption-surface)
for the full alternatives/trade-offs writeup.

1. **Windowing strategy — both, selectable.** v1 implements both
   candidates, not a single default:
   - Rolling 30-day window (always the most recent 30 days as of the
     run date).
   - Banlist-period window: non-overlapping periods from the **last
     Tuesday of an odd-numbered month** to the **last Monday of the
     following odd-numbered month** (e.g. last Tuesday of March → last
     Monday of May), aligned to Magic's Banned & Restricted announcement
     rhythm.
2. **Consumption surface — Tolaria News + S6, both.** Previously
   defaulted to the S6 admin dashboard only; amended so the public
   Tolaria News BFF (`/metagame`, `/archetypes`, `/trends`) and S6's
   existing admin view both read the same computed output — no drift
   between the two, since both read the same `barrins_api`-owned tables
   (see item 3 below).

Two further decisions made the same day, not previously flagged as open
questions on this page but discovered while planning the exposure side:

1. **Data flow — push-based, not a live API.** Karn Tablets
   self-schedules its own retraining internally (a systemd timer, like
   `scripture_scraper` — see T8's page), then **pushes** its results to a
   new `POST /internal/karn/ingest` route on `barrins_api` after each run,
   the same pattern already proven for Barrin's Scripture
   (`POST /internal/scripture/ingest`). `barrins_api` owns and stores the
   pushed results; Tolaria News and S6 both read those tables directly —
   Karn Tablets is never called live on the public read path, and needs no
   inbound network exposure at all (only outbound, to Postgres and to
   `barrins_api`).
2. **Format scope — Duel Commander only, for v1.** `apps/tolaria_news`
   is named a "Duel Commander tournament aggregator"
   (`apps/tolaria_news/README.md`); Karn Tablets' v1 clustering input is
   `bs_decks` joined through `bs_tournaments.format == "Duel Commander"`
   only, matching the same check `services/tolaria_news/decks.py` already
   uses for commander derivation. No format dimension is exposed yet —
   there is exactly one consumer and it only wants one format.

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
