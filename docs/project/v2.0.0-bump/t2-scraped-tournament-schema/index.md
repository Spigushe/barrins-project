# T2. Scraped-tournament domain model in `barrins_api`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` | New domain, `bs_`-prefixed (Barrin's Scripture) — decided 2026-07-26 |
| **Initial date** | / | Not started |
| **Status** | 🟡 In progress — `bs_*` models + Alembic migration + model tests written and passing (2026-07-30), not yet applied to any real database; the `docs/decklist_integration/` doc decision is the only open task | / |
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

## Design (2026-07-30)

Designed against real archive data, not just the scraper's Pydantic
schemas: both T1 fixtures (`apps/barrins_scripture/tests/fixtures/`) and
live samples pulled from `mtg_decklist_cache` and mtgtop8.com directly
(via `gh api`/`curl`). Fully relational, six tables, mirroring the `ts_*`
convention exactly (UUID PKs, `StrEnum` → named Postgres `Enum`,
`created_at server_default=now()`) — no JSONB blob, even though
`JSONBCompat`/`jsonb_column` exist as a general utility, because nothing
in this codebase's `ts_*` domain actually uses it and T2's own done
statement calls for mirroring that convention:

- `bs_tournaments` (`source` enum `mtgo`/`mtgtop8`, unique on `url`)
- `bs_decks` (unique on `(tournament_id, anchor_uri)`)
- `bs_deck_cards` — one row per mainboard/sideboard line (unique on
  `(deck_id, board, card_name)`)
- `bs_rounds` (unique on `(tournament_id, round_name)`)
- `bs_round_matches` (unique on `(round_id, player_1, player_2)`)
- `bs_standings` (unique on `(tournament_id, player)`)

Every table has a unique constraint on its natural key from the JSON
shape, so replaying the archive through the ingestion route (T3) is an
idempotent upsert, not a duplicate-insert risk — required for §1.2's
maintenance-window containment (a queued scrape retried after a
maintenance window must not double-insert).

**Real bug found while designing this, fixed as part of this item**:
MTGTop8 reports ties past the top few places as a bracket *range*
("5-8", "9-16", "17-32", ...), confirmed against a real 391-player event
(mtgtop8.com/event?e=87792). `barrins_scripture`'s `Deck.result` (T1,
already merged) was `int | None`, and `get_deck_from_top8` silently kept
only the leading digit of a range — a real data-loss bug, not just a
schema-design gap. Fixed on this same branch: `Deck.result` is now
`str | None` throughout `barrins_scripture`, with a new fixture + a
regression test (`TestMtgtop8TieBracketResults` in
`apps/barrins_scripture/tests/test_parsers.py`) built from the real
event page. `bs_decks.result` (and `bs_round_matches.result`, which was
already a string) are designed against the corrected type. See
`apps/barrins_scripture/tests/fixtures/README.md` for full provenance.

**Not yet applied anywhere**: `apps/barrins_api/.env`'s `DATABASE_URL`
points at the staging server (`146.59.146.57`), not a local instance —
running `alembic upgrade head` against it would migrate staging, so the
migration was validated by review + `alembic history`/`heads` (single
clean head) and a metadata-registration check, not by actually running
it. Applying it is still a manual, deliberate SSH step per T1/§1.2's
existing convention, not something this item does itself.

## Done statement

- ORM models for tournaments/decks/standings exist under
  `app/models/`, `bs_`-prefixed (mirroring the `ts_` convention already
  used for Tamiyo Scroll), with an Alembic migration. **Done.**
- The schema accommodates the JSON archive's existing shape
  (`mtg_decklist_cache`'s per-tournament JSON files) without requiring a
  lossy transform — a replay of the archive should be able to
  reconstruct the table contents. **Done** (see the `Deck.result` fix
  above — the schema now matches the *true* source shape, not the
  previously-lossy int).
- The models are owned and migrated exclusively by `barrins_api`;
  Barrin's Scripture never runs its own migration against this schema
  (§1.2 Option 2). **Done** — no DB credentials or migration tooling
  added to `apps/barrins_scripture`.

## Tasks

- [x] Get §1.2 decided (escalation, not implementation work) — Option 2,
      2026-07-25.
- [x] Design the `bs_*` table set from a real sample of
      `mtg_decklist_cache`'s JSON shape (inspect actual files, don't
      guess the schema from the scraper's Pydantic models alone) — see
      Design above.
- [x] Write the Alembic migration
      (`49c50188ee55_add_barrins_scripture_bs_tables.py`).
- [ ] Write the fictitious `docs/decklist_integration/00_plan_general.md`
      referenced by existing docs, or update those references — ties
      into F7's decision (recreate vs. redirect). Not started.
- [x] Model/migration tests in `apps/barrins_api/tests/scripture/`
      (`test_models.py`): round-trips, nullable/range `result`, unique
      constraints (one per table's natural key), and cascade deletes for
      all six tables. 13 tests, all passing against `barrins_db_test`.

## UAT (manual)

- [ ] Load a real sample of `mtg_decklist_cache` JSON files through
      whatever ingestion path §1.2 chose (T3, not built yet); confirm the
      resulting rows match the source files field-for-field.
- [ ] Confirm `alembic upgrade head` applies cleanly against staging via
      the existing manual SSH process (T1/§1.2's convention), once T3's
      ingestion route exists to actually use these tables.

## Non-regression tests

- `apps/barrins_api/tests/scripture/test_models.py` (13 tests): one
  round-trip + one unique-constraint-violation test per table with a
  natural-key constraint, plus cascade-delete coverage for
  `bs_tournaments → bs_decks` and `bs_decks → bs_deck_cards`, plus a
  dedicated test asserting `bs_decks.result` holds a real tie-bracket
  range ("5-8") intact. Full `barrins_api` suite: 253 passing (240 + 13),
  98.30% coverage.
- `apps/barrins_scripture`'s test suite: 127 tests passing (up from 118
  after T1), including the new `TestMtgtop8TieBracketResults` regression
  coverage for the `Deck.result` fix.
- `ruff`/`ty`/`bandit` clean on both apps.
