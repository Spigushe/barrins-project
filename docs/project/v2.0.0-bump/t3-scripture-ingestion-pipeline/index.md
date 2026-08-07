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

**Groundwork recorded during this scoping pass, not yet implemented:**

- **Maintenance gate behavior**: reject (not queue) via `HTTP 503` when
  `scripture_ingest_maintenance` is set, checked before any DB write starts
  — the JSON archive already makes a rejected scrape safely replayable, so
  the client (Barrin's Scripture) retries with backoff rather than the
  route building real queue infrastructure.
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
- A second step reads that archive (new scrapes, or a bulk historical
  replay) and calls the ingestion path into `barrins_api`'s `bs_*`
  tables, idempotently (re-ingesting an already-ingested tournament is a
  no-op, not a duplicate row).
- If the DB is ever dropped, the full `bs_*` contents can be rebuilt from
  the JSON archive alone, with no scraping required.
- The ingestion route rejects or queues writes during a declared
  maintenance window (§1.2's additional requirement) via a narrow,
  route-scoped maintenance flag — not a blanket API-wide maintenance
  page.

## Tasks

- [ ] Implement `POST /internal/scripture/ingest`: request/response
      schema, and its service-to-service credential (ties into D3).
- [ ] Add the maintenance-mode gate to this route specifically (§1.2):
      check a settings-backed or narrowly-scoped flag before writing,
      reject/queue if set.
- [ ] Wire the daily/biweekly scheduled jobs (or their post-migration
      equivalent) to call the ingestion step after each scrape, retrying
      against the same endpoint if a maintenance window was active.
- [ ] Write a standalone "bulk replay" script/command for rebuilding
      `bs_*` from the full existing `mtg_decklist_cache` archive
      (the actual disaster-recovery answer to the original "why keep
      JSON" question).

## UAT (manual)

- [ ] Run the bulk-replay path against the real `mtg_decklist_cache`
      archive on staging; confirm row counts match the number of
      archived JSON files (accounting for any intentionally-skipped
      malformed ones).
- [ ] Trigger a fresh scrape; confirm it lands in both the JSON archive
      and the `bs_*` tables.
- [ ] With the maintenance flag set, confirm the ingestion route rejects
      or queues the write instead of erroring opaquely, and that a retry
      after clearing the flag succeeds.

## Non-regression tests

- Idempotency test: ingesting the same tournament file twice produces
  no duplicate rows.
- A test asserting the archive write happens even if the DB ingestion
  step fails afterward (JSON-first ordering must not regress).
