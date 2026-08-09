# S8. MTGJSON card/set data pipeline

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` (new `Card`/`Set` models, `mtgjson` router/service) | / |
| **Initial date** | 2026-08-05 | / |
| **Status** | 🟡 **Core pipeline done, prices deferred** — `Card`/`MTGSet` models, Alembic migration, `HttpxMTGJSONClient`, the idempotent chunked-upsert importer, `POST /mtgjson/import` (admin-gated), `GET /mtgjson/status`, and the public `GET /sets/*`/`GET /cards/*` read routes are all built and tested (14 tests, real-data fixtures — see `apps/barrins_api/tests/fixtures/README.md`). This **unblocks T3**. Three 2026-08-05 decisions narrowed this pass's scope (see Context): image URLs are not built (only `scryfall_id`/`scryfall_oracle_id` stored), `AllPrices.json`/`GET /cards/{uuid}/prices` deliberately deferred, and the scheduled-refresh mechanism is still open. **2026-08-07**: fixed a ~45-minute import (one DB round-trip per row) by batching into chunked multi-row upserts. **2026-08-09**: fixed an OOM kill on the real full-file import by streaming (`ijson`); added live import progress (`GET /mtgjson/import/status`, admin-gated) via a new `mj_import_runs` table written independently of the main import transaction; renamed `sets`/`cards` to `mj_sets`/`mj_cards` to match this codebase's domain-prefix convention (DB-internal only). **2026-08-09 UAT**: re-triggered `POST /mtgjson/import` against the real, full file on staging — two consecutive runs, ~3.5 minutes each, 868 sets/112,809 cards, no OOM, confirming both the performance and memory fixes at full scale; also found and fixed a follow-on bug where the raw upsert never bumped `updated_at` on conflict, freezing `GET /mtgjson/status`'s `last_imported_at` (see UAT below) | / |
| **Source** | Discovered while scoping S4; corrects a false assumption in S2/§1.6; scope widened while scoping T3 | / |
| **Dependency** | D1 (playbook shape for the scheduled refresh — still open) | Blocks S4, and (added 2026-07-30, §1.10) **T3** (transitively T6) — **unblocked 2026-08-05**: real card data now exists for T3's ingestion route to validate scraped card names against, though T3 still needs its own route/credential/maintenance-gate work built on top (unchanged, not part of this item). No longer blocks S2 — its deck-validation gate deferred to v3.0.0 (2026-07-27) |

---

## Context

`docs/content/back/barrins_api/auth_roles.md` describes a
`POST /mtgjson/import` route, public `sets`/`cards` read routes, and an
`admin`-gated import capability as if already built. **F8 verified this
is false**: zero Python files reference `mtgjson`, no `Card`/`Set` model
exists. This item is the real, from-scratch build that S4 (card images +
sorting) needs before it can start its MTG-data-dependent work. S2's
deck-validation gate originally needed this too, but was deferred to
v3.0.0 (2026-07-27, see `../s2-team-sharing/index.md`), so it no longer
blocks on this item for v2.0.0.

**Not previously scoped as its own item** — it surfaced only once S4 and
S2 were checked against actual code, not against `auth_roles.md`'s
description of them.

**Scope widened 2026-07-30 (§1.10)**: scoping T3's ingestion route
(`POST /internal/scripture/ingest`) surfaced the same missing-data problem
from a second direction — `bs_deck_cards.card_name` (T2's schema) has
nothing to validate scraped card names against. Rather than let T3 ingest
unvalidated strings (the path S2's now-deferred gate would have taken),
T3 is blocked on this item: its ingestion route needs to validate each
scraped card name against this pipeline's card data before storing it.
This item is now a second, real consumer (alongside S4) rather than
S4-only.

**Three sub-decisions made 2026-08-05, before implementation** (escalated
per Constitution §16.2/§16.3 — each was a subjective/dependency-
introducing choice this item's own task list already flagged as needing
its own escalation, not assumed):

1. **Card images**: MTGJSON ships no images at all — only Scryfall
   identifiers (`identifiers.scryfallId`, `scryfallOracleId`) that could
   derive one. Decided: store `scryfall_id`/`scryfall_oracle_id` only:
   no URL construction, no self-hosting. Deriving/serving an actual image
   is deferred to S4, the feature that actually needs to render one.
2. **Price data**: `auth_roles.md` already documented a
   `GET /cards/{uuid}/prices` route (pre-dating this item), which needs
   MTGJSON's separate `AllPrices.json` file — never part of this item's
   own done statement. Decided: defer price import entirely; `auth_roles.md`
   corrected to flag that route as not-yet-built rather than silently
   left describing non-existent behavior (F8's own concern, applied
   narrowly here without taking on F8's full scope).
3. **Large-file parsing**: `AllPrintings.json` is large enough that a
   streaming parser (e.g. `ijson`) might have been needed — which would
   be a new dependency (§4.7/§22). Decided: try a plain `httpx` GET +
   `response.json()` first; only reach for a streaming parser if that
   actually proves too memory-heavy in practice. It worked fine against
   the real per-set files used for testing; the full `AllPrintings.json`
   hasn't been fetched end-to-end against production yet (see UAT).
   **Update 2026-08-09: it did prove too memory-heavy — see the memory
   fix below.** The streaming parser this decision deferred was added.

**2026-08-07 performance fix**: the first real `POST /mtgjson/import` run
took ~45 minutes. Root cause: `import_all_printings` did one
`INSERT ... ON CONFLICT DO UPDATE` per row (~700 sets + 100k+ card
printings = 100k+ sequential DB round-trips). Fixed by batching into
chunked multi-row upserts (`_UPSERT_CHUNK_SIZE = 500` rows/statement) in
`app/services/mtgjson/importer.py` — no schema change, no new dependency,
same idempotent-upsert contract. Cuts round-trips from ~100k to a few
hundred.

**2026-08-09 memory fix**: the first `POST /mtgjson/import` attempt
against the real, full `AllPrintings.json` on staging OOM-killed the
`api-staging` uvicorn worker (~5.5GB RSS, confirmed via `dmesg`) before a
single row committed — `HttpxMTGJSONClient.fetch_all_printings` buffered
the whole response body, `response.json()` built the full parsed tree,
and `import_all_printings` built `set_rows`/`card_rows` as full lists
again on top of that, all simultaneously. Approved per §4.7/§22 (see
decision 3 above): added `ijson` and rewrote both to stream. The client's
`fetch_all_printings() -> dict` became `stream_sets() -> AsyncIterator[
tuple[str, dict]]` (`ijson.from_iter(response.aiter_bytes())` +
`ijson.kvitems(f, "data")`, never buffering the response); the importer's
`_ImportBuffer` consumes it set-by-set and flushes `_UPSERT_CHUNK_SIZE`-row
upserts as it goes (sets flushed before cards, so a buffered card's
`set_code` FK is always visible within the same uncommitted transaction),
instead of collecting `set_rows`/`card_rows` upfront. Still one commit at
the end — the idempotent all-or-nothing contract is unchanged, only how
memory is bounded while getting there. Real full-file run against
staging still needs to be re-attempted post-fix (see UAT).

**2026-08-09 live progress**: `import_all_printings` only commits its
`mj_sets`/`mj_cards` writes once at the end (see the memory fix above), so
Postgres's default isolation hid all progress from any other session —
including a status poll — until the whole import finished. Decided (same
session, informal — no dependency added, so no §4.7/§22 escalation
needed): a separate progress row, over an in-process counter (lost on the
single-worker deployment's restart) or per-chunk commits on the main
transaction (would have reopened the atomicity guarantee the memory fix
was built to protect). Added `mj_import_runs` (new migration, same pass
that renamed `sets`/`cards` to `mj_sets`/`mj_cards` — see below) and
`_ImportRunTracker` (`app/services/mtgjson/importer.py`): writes through
its own session (`AsyncSessionLocal`, independent of the main import's
`session`), committed immediately at the same granularity as
`_UPSERT_CHUNK_SIZE`. `GET /mtgjson/import/status` (admin-gated — a
failed run's `error_message` can include internal exception text) returns
the latest run's `status` (`running`/`succeeded`/`failed`), counts so far,
and `error_message`. A leftover `running` row from a hard crash (e.g. the
OOM incident above) self-heals to `failed` the next time an import
starts, since only one admin-triggered import runs at a time.

**2026-08-09 table rename**: `sets`/`cards` renamed to `mj_sets`/`mj_cards`
in the same migration as `mj_import_runs` above, matching this codebase's
`bs_*`/`ts_*` domain-prefix convention (never applied here when S8 first
shipped these two tables). DB-internal only: API paths (`/sets/*`,
`/cards/*`) and ORM class names (`MTGSet`, `Card`) are unchanged. Safe
because neither table has shipped in a release or held real data yet
(confirmed empty on the dev DB before the migration ran).

## Done statement

- `Card` and `MTGSet` ORM models exist under `app/models/mtgjson.py`,
  populated from MTGJSON's `AllPrintings.json` only (`AllPrices.json`
  deliberately deferred, see decision 2 above). **Done.**
- `POST /mtgjson/import` exists, `admin`-gated (`AdminUser`). No request
  body: `auth_roles.md`'s originally-documented `source`/`force` fields
  are moot now that there's only one source file and the upsert is
  already idempotent, so a per-call "force" flag would be an unused
  parameter (Constitution §39/§48) — dropped rather than built unused.
  **Done.**
- `GET /sets/`, `GET /sets/{code}`, `GET /sets/{code}/cards`,
  `GET /cards/{uuid}`, `GET /cards/by-name/{name}` exist, public
  (anonymous), matching `auth_roles.md`'s security matrix. **Done.**
  `GET /cards/{uuid}/prices` is **not** built (decision 2). A
  `GET /mtgjson/status` route (already documented in `auth_roles.md`,
  not in this item's original done statement) is also **done**.
- Card records carry `scryfall_id`/`scryfall_oracle_id` (decision 1),
  type line, mana value/cost, colors, and color identity. **Done** —
  image URL derivation itself is explicitly not this item's job (S4's).
- Multi-face cards store **per-face** type data (front/"face A" and
  back face separately) — MTGJSON already models multi-face cards as
  one row per face (`faceName`/`side`/`otherFaceIds`), so storing one
  row per MTGJSON `uuid` gets this for free, no extra modeling needed.
  **Done**, verified against a real MDFC (`Emeria's Call // Emeria,
  Shattered Skyclave`, ZNR) — see `TestMultiFaceRoundTrip` in
  `tests/test_mtgjson.py`.
- A **scheduled refresh** exists (not just the admin-triggered manual
  route). **Still open** — not built in this pass; needs its own T8-style
  playbook following D1's template, and MTGJSON's own release cadence
  hasn't been researched yet.
- Live import progress: `GET /mtgjson/import/status` (admin-gated) exists,
  backed by `mj_import_runs`. **Done** (2026-08-09) — see the live-progress
  note above; `tests/test_mtgjson_import_status.py` covers the gate,
  success/failure outcomes, multi-call progress updates, and the
  stale-`running`-row self-heal.

## Tasks

- [x] Confirm MTGJSON's exact source file(s) and per-face schema shape
      against real MTGJSON data — done 2026-08-05 via `mtgjson.com`'s own
      data-model docs plus real downloaded set files (`P30A.json`,
      `ZNR.json`), not memory. See `tests/fixtures/README.md` for
      provenance.
- [x] Design `Card`/`Set` models, including per-face type storage — done,
      see `app/models/mtgjson.py`'s module docstring for the PK-design
      rationale (natural keys, not generated surrogates, unlike `bs_*`).
- [x] Implement `POST /mtgjson/import` — done, no request body (see Done
      statement above for why `source`/`force` were dropped).
- [x] Implement `GET /sets/*`, `GET /cards/*` public read routes — done.
- [x] Decide the card-image source — escalated and decided 2026-08-05
      (decision 1 above): store identifiers only, defer URL/hosting to S4.
- [ ] Design and build the scheduled-refresh mechanism, coordinating
      with D1's playbook template. **Still open** — next concrete step
      for this item.
- [x] Update `auth_roles.md` — done narrowly (the security-matrix rows
      this item's routes touch); F8's broader doc-accuracy pass across
      the rest of that file is unchanged, still F8's own scope.

## UAT (manual)

- [x] Trigger `POST /mtgjson/import` against the **real, full**
      `AllPrintings.json` on staging (tests so far only exercise trimmed
      per-set fixtures — see decision 3 above); confirm `sets`/`cards`
      tables populate, memory usage stays reasonable, and
      `GET /cards/by-name/{name}` returns real data. **Done 2026-08-09**,
      re-attempted post streaming-fix directly against `api-staging`
      (127.0.0.1:8511, bypassing nginx's default `proxy_read_timeout`):
      two consecutive full-file runs both succeeded in ~3.5 minutes
      (17:49:30–17:53:00 for the confirmed one, via
      `GET /mtgjson/import/status`), 868 sets / 112,809 cards upserted
      each time (idempotent), `sudo dmesg -T` showed no new OOM kill past
      the runs (the three entries present all predate them, 13:46–14:47 —
      the last of which, `uvicorn`/~5.5GB anon-rss, is the original
      pre-fix incident this UAT item is about). `GET /cards/by-name/Lightning
      Bolt` returned real data. Confirms both the 2026-08-07 performance
      fix (~45min → ~3.5min) and the 2026-08-09 memory fix at full scale.
      **Found and fixed a second bug during this UAT pass**: the chunked
      upsert's raw `INSERT ... ON CONFLICT DO UPDATE` bypassed the ORM's
      `onupdate=func.now()`, so `GET /mtgjson/status`'s `last_imported_at`
      stayed frozen at each row's original insert time on every re-import
      instead of reflecting the run that just happened (staging showed
      `16:58:13`, over 50 minutes stale, right after a confirmed-successful
      17:53:00 run). Fixed in `_upsert_sets`/`_upsert_cards`
      (`app/services/mtgjson/importer.py`) by setting `updated_at` in
      `update_cols` explicitly; regression test added
      (`TestImportBumpsUpdatedAt` in `tests/test_mtgjson.py`).
- [x] Confirm a multi-face card stores both faces' types separately,
      retrievable independently — done against a real MDFC in
      `tests/test_mtgjson.py` (see Done statement above).
- [ ] Confirm the scheduled refresh runs without manual intervention and
      updates existing records (not just inserting new ones). **Blocked
      on the scheduled-refresh task above.**

## Non-regression tests

- New `tests/test_mtgjson.py`: import idempotency (re-running doesn't
  duplicate rows), public-route reachability without auth, admin-gating
  on the import route (403 for non-admin), and (2026-08-07) an import
  forced across multiple upsert chunks (`_UPSERT_CHUNK_SIZE` monkeypatched
  down) to prove no rows are dropped or duplicated at a chunk boundary.
  (2026-08-09) `TestImportBumpsUpdatedAt`: seeds a stale `updated_at`
  sentinel onto already-imported rows, re-imports, and confirms it moves
  off that sentinel — doesn't compare timestamps across the two imports
  directly, since Postgres's `now()` is transaction-start time and the
  test fixture keeps a whole test inside one outer transaction, so a naive
  `>` comparison could pass or fail independent of whether the underlying
  fix works.
- New `tests/test_mtgjson_import_status.py` (2026-08-09): admin-gating on
  `GET /mtgjson/import/status` (401/403/404), a successful run's final
  status/counts, a mid-stream failure marking the run `failed` with
  `error_message` set while leaving `mj_sets`/`mj_cards` untouched, the
  same tracked row updating across multiple `_ImportRunTracker.progress()`
  calls (not just once at the end), and the stale-`running`-row self-heal
  on the next run's `start()`. Relies on a new `mtgjson_tracker_uses_test_db`
  fixture (`tests/conftest.py`) that redirects the tracker's independent
  session factory onto the test's own transactional connection — without
  it, the tracker's writes would hit the real per-environment database
  instead of the isolated test one (`AsyncSessionLocal` is a module-level
  binding, invisible to FastAPI's `Depends(get_db)` override).
- A test asserting a known multi-face fixture card's per-face type data
  round-trips correctly — this is the data S4's "face A Land" rule
  depends on, so it needs its own explicit regression coverage.
