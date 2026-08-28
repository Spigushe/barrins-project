# T6. Karn Tablets — basic modeling: metagame clustering & deck-type aggregation

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/karn_tablets` (new, real basic ML/aggregation component) | / |
| **Initial date** | 2026-08-27 | Backend + pipeline landed |
| **Status** | 🟡 In progress — pipeline (`apps/karn_tablets`) + `barrins_api` ingest/read/admin half done 2026-08-27; T7 docs and T8 playbook + Tolaria News frontend wiring outstanding | / |
| **Source** | Request item 1; `v2.0.0-bump/index.md` §1.4; [ADR-13](../../../content/ops/architecture/decisions.md#adr-13-karn-tablets-output-data-flow-scope-and-consumption-surface) | / |
| **Dependency** | I4 (resolved), T2, T3 (real scraped-tournament data to cluster) | Blocks T8 (its playbook) |

---

## Reference material

- [`Karn Tablets Readout (standalone).html`](<./Karn Tablets Readout (standalone).html>)
  — self-contained verification view of a dev-database clustering run
  (2026-08-27, `pipeline_version` 0.1.0, k-means). Renders the `kt_*`
  data read back through the `/bff/tolaria-news/{metagame,archetypes,
  trends}` routes: "metagame now" for both window modes, per-archetype
  share across every Duel Commander banlist period since mid-2024, a
  rolling-30-day cross-check, and the full latest-run cluster table
  (auto-derived name, representative decklist size, signature cards).
  Not a published metagame report — kept here as a snapshot of what the
  pipeline actually computed. Exported from Claude artifact
  `f83f45b7-9e53-48d4-a7fb-f426f130adbb`.

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

## Open sub-decisions — resolved by ADR-13 (2026-08-11) and follow-ups

1. **Windowing strategy** → **both** modes ship, selectable: rolling
   30-day *and* banlist-period (last Tuesday of an odd-numbered month →
   last Monday of the following odd-numbered month). The boundary math
   lives in the standalone, independently tested `apps/dc_calendar`
   package (`dc_calendar.windowing`), imported by both the pipeline and
   `barrins_api`.
2. **Consumption surface** → **Tolaria News BFF *and* the S6 admin
   dashboard, both**, reading the same `kt_*` tables through the same
   `app/services/karn/read.py` service so they can't drift.
3. **Data flow** → **push-based** (ADR-13): the pipeline holds a
   read-only `bs_*`/`mj_cards` credential and pushes results to
   `POST /internal/karn/ingest`; `barrins_api` owns the `kt_*` schema.
   The pipeline is a plain scheduled job with no inbound API.
4. **Clustering library** → scikit-learn (already a dependency of
   `apps/karn_tablets`; KMeans/DBSCAN/GMM selectable via `--algorithm`).
5. **`format` param** → the read routes take an optional `format` query
   param from v1 (default `"Duel Commander"`), per ADR-13's 2026-08-27
   amendment — storage and reads are `(format, window_kind)`-scoped even
   though the pipeline only produces Duel Commander today.

## Implementation status (2026-08-27)

**Done:**

- `apps/karn_tablets` — the clustering CLI pipeline (`extract → cluster →
  aggregate → push`), unit-tested. Pushes to `POST /internal/karn/ingest`.
- `barrins_api` — `POST /internal/karn/ingest` (`X-Karn-Token` /
  `KARN_INGEST_TOKEN`), new `kt_*` tables (migration `a1f4c7e9b230`), the
  ingester with stable cross-run archetype identity
  (`app/services/karn/ingester.py`, Jaccard match on representative
  decklists), the shared read layer (`app/services/karn/read.py`), the
  public Tolaria News routes `GET /bff/tolaria-news/{metagame,archetypes,
  trends}`, and the S6 admin route
  `GET /bff/tamiyo-scroll/admin/metrics/karn-tablets`. 27 tests under
  `tests/karn/`, `ruff`/`ty`/`pytest` green.

**Outstanding:**

- T7 — per-app docs pages under `docs/content/` for `apps/karn_tablets`.
- T8 — the deployment playbook (`ops/my-server/karn_tablets.yml` + a
  scheduled-job role mirroring `scripture_scraper`, a `karn_ingest_token`
  role, `secrets/karn_tablets/*`, CI paths-filter, nginx rate-limit
  entries for the three new public BFF paths).
- Tolaria News frontend — the flag-gated `/metagame`/`/archetypes`/
  `/trends` pages are wired to the real routes and `src/schemas/
  karnTablets.ts` is reconciled against the live `WindowOut`/response
  shape (2026-08-27). All three default to the **banlist-period**
  window; archetype names and card names hover for Scryfall art.
  `/metagame` is a top-20 bar chart with a backend-classified
  rising/falling/stable/new chip per archetype; `/archetypes` is the
  detail table alone (rep-list size + `is_signature` cards),
  cursor-paginated; both carry a prev/next period stepper (`?at=`).
  `/trends` keeps its line chart and adds a provisional per-archetype
  sparkline grid, two rows of five.
  Additive BFF fields: `commanders` + `momentum` + `deck_share_delta`
  (all rows); `previous_window`/`next_window` + `at` param on
  `/metagame` and `/archetypes` (the latter's `data` is now an object,
  not a bare list); `scryfall_id` + `is_land` + `is_signature` on
  `/archetypes` `representative_mainboard`; `/archetypes` `limit`/
  `cursor` + `page`. `is_signature` excludes basic lands always and
  lands in ≥33% of the run's archetypes. Momentum now compares to the
  preceding window (works at any stepper position). See
  `docs/content/back/barrins_api/bff/tolaria_news.md`. Still to do: flip
  `VITE_FEATURE_KARN_TABLETS` (gated on T7 docs / T8 playbook).
- **Trends per-period zoom (deferred, needs a data-model decision).**
  Requested 2026-08-27: on the Trends page, zoom into a single
  banlist/rolling period and split it into ~8 sub-points for a
  finer-grained recent trend. `kt_*` stores one aggregate row per run —
  no per-deck cluster membership and no sub-period runs — so this is not
  a read-layer change. Options, to be decided before building:
  1. **Pipeline emits sub-period runs** — `apps/karn_tablets` runs the
     clustering on N evenly-split sub-windows of the target period and
     pushes each as its own run. Faithful (real clustering per bucket),
     heaviest.
  2. **Store per-deck cluster membership** — add a `kt_run_decks`
     (`run_id`, `deck_id`, `archetype_id`) table so any date bucketing
     can be recomputed on read. One schema addition, one ingest change;
     read layer then buckets by `bs_decks.date`.
  3. **Approximate on read from `bs_*`** — bucket the period's decks by
     date and, per bucket, score each against the run's representative
     card sets (a similarity heuristic, not the clustering). No schema
     change; least faithful.

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

- [x] Confirm the windowing default → both (ADR-13).
- [x] Confirm the consumption surface → Tolaria News + S6 (ADR-13).
- [x] Choose a clustering approach/library → scikit-learn.
- [x] Implement the banlist-period boundary calculation as a standalone,
      tested utility — `apps/dc_calendar` (`dc_calendar.windowing`).
- [x] Build the clustering pipeline reading from `bs_*` (T2/T3) —
      `apps/karn_tablets`.
- [x] Build the deck-type aggregation step.
- [x] Attach §45.2's required metadata (source data range, pipeline
      version, algorithm info) to every computed result —
      `kt_clustering_runs` carries `window_*`, `pipeline_version`,
      `algorithm`, `generated_at`.
- [x] `barrins_api` ingest route + `kt_*` schema + ingester (stable
      archetype identity) + shared read layer + Tolaria News BFF routes +
      S6 admin route + `tests/karn/`.
- [x] Write real `README.md`/`CHANGELOG.md` content.
- [ ] T7 — `docs/content/` per-app docs pages.
- [ ] T8 — deployment playbook + secrets + CI + nginx rate limits.
- [x] Tolaria News frontend wiring + `karnTablets.ts` reconciliation
      (2026-08-27) — `/metagame` bar chart + momentum chip, `/trends`
      sparkline grid, `/archetypes` paginated detail table, banlist-period
      default, card/commander image hovers. Flag flip still pending
      (T7/T8).
- [ ] Trends per-period zoom (~8 sub-points) — deferred pending a
      data-model decision (see **Outstanding** above for the three
      options).

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
