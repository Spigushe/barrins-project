# T3. Scrape → JSON archive → ingest pipeline

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_scripture` + `apps/barrins_api` | / |
| **Initial date** | / | Not started |
| **Status** | 🟡 **Unblocked 2026-08-05** — S8's `Card`/`MTGSet` pipeline now exists (`GET /cards/by-name/{name}` returns real MTG data), so this item's own work (the ingestion route itself, its service credential, maintenance gate, and bulk-replay script — none of that built yet) can start. T1/T2 were already functionally ready | / |
| **Source** | Request item 1; `v2.0.0-bump/index.md` §1.2, §1.3, §1.10 | / |
| **Dependency** | T1 (done), T2 (done), S8 (core pipeline done 2026-08-05, scheduled refresh still open — not a blocker for this item) | Blocks T4 |

---

## Context

The JSON-archive-first pipeline already exists and works
(`mtg_scraper` → `mtg_decklist_cache`, scheduled via GitHub Actions) —
this item keeps that behavior and adds the missing second half: getting
the archived JSON into the `bs_*` schema T2 defines (`bs_` naming
decided 2026-07-26, see T2). Per §1.2 (**decided, Option 2**), this
happens through a private, backend-only route on `barrins_api`
(`POST /internal/scripture/ingest`) rather than Barrin's Scripture
holding its own `DATABASE_URL`.

**Blocked on S8, added 2026-07-30 (§1.10 in the project index).** Scoping
this item's ingestion route surfaced that `bs_deck_cards.card_name` has no
authoritative MTG card list to validate against — S8 (the MTGJSON pipeline)
doesn't exist in code yet. Decided: this item now validates every scraped
card name against S8's data before storing it, rather than ingesting
unvalidated strings. This item is on hold until S8 lands.

**Decided (2026-08-07, definitive) — pull/sweep model replaces push +
maintenance-gate + backoff.** Originally scoped as: the scraper calls
`POST /internal/scripture/ingest` immediately after each scrape, the route
rejects with `HTTP 503` during a declared maintenance window, and the
client retries with backoff. Superseded: the JSON archive is the sole
handoff point (already true per §1.3), and a periodic, idempotent **sweep**
— the same mechanism as the bulk-replay script below, just scoped to
recent files instead of the full archive — is what drives ingestion,
rather than an immediate call from the scraper. If `barrins_api` is down or
in maintenance, the sweep simply fails that tick; the next scheduled sweep
picks up whatever wasn't ingested, because `ON CONFLICT DO UPDATE` upserts
by natural key make re-submission a no-op. This also gets the MTGO
3-day-mutability requirement (below) for free — re-sweeping recent files on
every tick re-applies any edits, not just fills gaps. Consequence: no
scraper-side retry/backoff logic, no maintenance-flag special-casing in the
route — a plain 5xx during a sweep is indistinguishable from "try again
next tick." The route itself is unchanged (§1.2's private,
backend-only-route decision stands; only who calls it and when changes).

**Groundwork recorded during this scoping pass, not yet implemented:**

- **`bs_deck_cards` needs delete-and-reinsert per deck on each ingest, not
  row-level upsert.** Originally assumed decklists were immutable once
  published — wrong: MTGO decklists are mutable for about 3 days after
  publication. A naive per-card upsert would leave stale rows for any card
  removed during that window; deleting and reinserting a deck's card lines
  in the same transaction as its own upsert avoids that.
- **Service-to-service credential**: a static token sent as an
  `X-Scripture-Token` header, compared with `hmac.compare_digest` (matching
  the constant-time-comparison style already used in
  `app/core/security.py::verify_verification_code`). No existing
  service-to-service auth dependency exists in `barrins_api` today — this
  would be new code, a sibling to `CurrentUser` in `app/dependencies/`.
- **Upsert mechanism** for the other five tables (tournament/rounds/
  round_matches/standings): PostgreSQL `INSERT ... ON CONFLICT DO UPDATE
  ... RETURNING id`, one statement per row, in FK order — every table's
  natural-key unique constraint (T2) makes this idempotent with no prior
  `SELECT`.
- **Scheduled-job wiring**: `scrape_mtgo`/`scrape_mtgtop8` already return
  each written file's `Path` from `save_tournament_scrape` — capturing that
  list (currently discarded by the consumer threads) is enough to know
  exactly what to ingest after a run, no timestamp/checkpoint heuristic
  needed.

## Done statement (once T1/T2/S8 land)

- Every scrape still produces a JSON file in the archive first (§1.3 —
  unchanged behavior, this is the existing replay-safety net), living at
  its new, durable location (T1's urgent relocation task).
- A periodic sweep reads that archive (recent files on a routine tick, or
  the full archive for a historical replay — same mechanism, different
  scope) and calls the ingestion path into `barrins_api`'s `bs_*` tables,
  idempotently (re-ingesting an already-ingested tournament is a no-op,
  not a duplicate row).
- If the DB is ever dropped, the full `bs_*` contents can be rebuilt from
  the JSON archive alone, with no scraping required.
- No scraper-side retry/backoff and no maintenance-flag gate on the route
  (2026-08-07 decision, above): a failed sweep tick is resolved by the
  next scheduled tick, not by special-casing the failure.

## Tasks

- [ ] Implement `POST /internal/scripture/ingest`: request/response
      schema, and its service-to-service credential (ties into D3).
- [ ] Write the sweep mechanism (recent-files mode and full-archive mode
      share the same code path — the latter is the "bulk replay"/
      disaster-recovery case): list archive files, call the ingestion
      route per file, idempotent by construction. Schedule the
      recent-files mode on its own tick, independent of the scrape
      schedule, so an `barrins_api` outage during a scrape doesn't need
      to be handled at scrape time at all.

## UAT (manual)

- [ ] Run the sweep in full-archive mode against the real
      `mtg_decklist_cache` archive on staging; confirm row counts match
      the number of archived JSON files (accounting for any
      intentionally-skipped malformed ones).
- [ ] Trigger a fresh scrape; confirm it lands in the JSON archive, then
      confirm the next sweep tick lands it in the `bs_*` tables.
- [ ] Take `barrins_api` down (or set it to a state that 5xxs the
      ingestion route) during a sweep tick; confirm the sweep fails that
      tick without side effects, and the next tick ingests successfully
      with no duplicate/missing rows.

## Non-regression tests

- Idempotency test: ingesting the same tournament file twice produces
  no duplicate rows.
- A test asserting the archive write happens even if the DB ingestion
  step fails afterward (JSON-first ordering must not regress).
