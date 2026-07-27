# T3. Scrape → JSON archive → ingest pipeline

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_scripture` + `apps/barrins_api` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on T1 and T2 | / |
| **Source** | Request item 1; `v2.0.0-bump/index.md` §1.2, §1.3 | / |
| **Dependency** | T1, T2 | Blocks T4 |

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

## Done statement (once T1/T2 land)

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
