# F10. Metagame tab is not scoped to the active personal deck

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` (FastAPI), `apps/tamiyo_scroll` (React/Vite) | / |
| **Initial date** | 2026-08-17 | Investigated 2026-08-17 |
| **Status** | 🟢 Implemented 2026-08-18 (backend + frontend + migrations + tests, see "Proposed tasks" below). Not yet exercised against staging/production data — the migration's backfill (item 1 below) still needs a real run against a database with pre-F10 `ts_meta_decks` rows, per its own UAT item | / |
| **Source** | User report, 2026-08-17 conversation: "when selecting/creating a personal deck for a different game, the metagame section is not cleared although it should be linked to a specific card game" | / |
| **Dependency** | Builds on **S10** (`game` flag on `TSPersonalDeck`/`TSMetaDeck`, see `../s10-personal-deck-game-flag/index.md`) — S10 added the column but explicitly scoped its use to ML-export filtering only, never to UI scoping (see Root cause below). Touches the same sharing-merge logic as **S1** (`../s1-global-sharing-reenable/index.md`), and extends the existing `_sync_opponent_deck_games` helper in `api/tamiyo_scroll/personal_decks.py` | / |

---

## What happened

Reported by the user: selecting or creating a personal deck for a
different card game (e.g. switching the active deck from a Magic deck to
a Pokémon deck via `PersonalDeckSelector`) does not clear or refilter the
**Metagame** tab. The opponent-deck roster and expected-metagame data
from the previous deck stay visible and editable against the newly
active, unrelated deck.

## Investigation

`MetagameTab.tsx` renders three sections:

- `ArchetypeSummarySection` / `MatchupSummarySection`
  (`pages/metagame/StatsSections.tsx`) — call `useArchetypeSummary(activeDeckId)`
  / `useMatchupSummary(activeDeckId)`. These **are** scoped to the active
  personal deck (matches are always tied to one `personal_deck_id`), so
  they are not part of this bug.
- `MetaDecksRosterSection` ("Deck roster (MUR)") and
  `ExpectedMetagameSection` (`pages/metagame/MetaDecksSections.tsx`) both
  call `useMetaDecks()` (`hooks/useMetaDecks.ts`) with **no argument** —
  not the active deck id, not its game.

`useMetaDecks()` calls `GET /bff/tamiyo-scroll/meta-decks`
(`app/api/tamiyo_scroll/meta_decks.py:list_meta_decks`), which returns
**every** `TSMetaDeck` row owned by the user (plus any sharer's
name-matched rows via `build_merged_view`), with no query parameter and
no filtering at all — neither by game nor by which personal deck it was
created against.

`TSMetaDeck.game` (`app/models/tamiyo_scroll.py:234`) does exist, but:

- it is nullable, with **no default and no backfill**;
- per its own code comment, it is "a soft data tag for ML export
  filtering, not an enforced constraint" — explicitly never meant to
  gate what the UI shows;
- it is only ever populated when a meta deck is created with a
  `personal_deck_id` in the payload (`meta_decks.py:77-88`, inherited
  from that personal deck's `game`) — and the **only UI path that
  creates roster entries**, `MetaDecksRosterSection.handleAdd`, never
  sends `personal_deck_id`. So in practice, every roster entry created
  through the app today has `game = NULL` and no deck association at
  all.

There is one existing mechanism this builds on: `_sync_opponent_deck_games`
(`api/tamiyo_scroll/personal_decks.py:66`), called when a personal deck's
`game` is PATCHed. It looks up every distinct `TSMatch.opponent_deck_id`
logged against that personal deck and overwrites `game` on those
`TSMetaDeck` rows. It's the right derivation mechanism (personal deck →
its logged opponents) but today it unconditionally overwrites in place —
it has no notion of "this opponent deck was also fought by a *different*
personal deck," which the model below needs it to handle.

This traces back to **S10** (`docs/project/v2.0.0-bump/s10-personal-deck-game-flag/index.md`),
which added the `game` column specifically to let ML training data be
filtered to Magic decks, explicitly scoped as an ML-export concern, not
a UI-scoping one. The Metagame tab's cross-deck leak was never in that
item's done statement — it's a gap between two features that were never
reconciled, not a regression from a specific change.

`build_merged_view` (`services/tamiyo_scroll/sharing_merge.py`) already
accepts an optional `personal_deck_id` filter for **matches** (used
elsewhere, e.g. `GET /matches`), but nothing equivalent exists for meta
decks — the hook point exists, it's just unused for this endpoint.
`sharing_merge.py` also already establishes two conventions this item
reuses rather than reinventing: `_norm()` (trim + lowercase) as the name-match
rule, and "the viewer's own data always wins over a sharer's" as the
conflict rule.

## Root cause (summary)

1. `GET /meta-decks` has no filter of any kind — every roster entry the
   user owns comes back regardless of which deck (or game) is active.
2. `useMetaDecks()` ignores the active deck entirely.
3. The one UI flow that creates roster entries never records which deck
   it was created against, so almost all existing roster data has no
   deck (or game) association today.

## Decision: track per-deck, filter by a user-configurable scope (default: game)

Every `TSMetaDeck` row gets a required `personal_deck_id` FK (the
precise association). `GET /meta-decks` filters using either that exact
id or the active deck's `game` (a join), depending on a per-user setting
— `metagame_roster_scope: "game" | "personal_deck"`, stored alongside
the existing `active_personal_deck_id` on `TSUserSettings`. **Default:
`"game"`**, matching the bug report exactly (one roster per game); users
who want a roster dedicated to a single deck can switch the setting.
Because the data always carries the exact deck, switching the setting
later needs no migration — only the `WHERE` clause changes.

Client-side-only filtering (leave the API untouched) was considered and
rejected: it conflicts with Constitution §4.1/§4.2 (the backend owns
domain rules; "which roster entries belong to this view" is a domain
rule, not presentation), and it would still ship the full cross-deck
roster over the wire regardless of what the UI hides.

## Cross-deck consistency model (decided)

Five behaviors, decided together, that make the required-per-deck FK
above coexist with the default game-scoped view without either losing
data or silently bleeding data across unrelated games:

1. **Backfill from match history.** For every existing (legacy)
   `TSMetaDeck` row, derive its owning personal deck(s) the same way
   `_sync_opponent_deck_games` already derives `game`: group
   `TSMatch.opponent_deck_id` by `TSMatch.personal_deck_id` for that
   user. `_sync_opponent_deck_games` itself needs to change from
   "overwrite `game` in place" to the duplicate-and-allocate rule in
   item 2, since it's the mechanism both this backfill and future
   corrections share.
2. **Duplicate when a roster deck maps to more than one personal deck.**
   If a legacy `TSMetaDeck` row was fought by more than one of the
   user's personal decks (per item 1's grouping), duplicate the row —
   one copy per `personal_deck_id` — instead of arbitrarily picking one
   owner. This is what lets the required FK be exact per deck without
   losing the "I fought this deck with two of my decks" history.
3. **Orphan rows (no match history at all).** Roster entries added to
   "Expected metagame" but never actually played against have no
   `TSMatch` row to derive a personal deck from. **Decided**: assign
   these to the user's `active_personal_deck_id` at migration time.
   Known limitation, accepted rather than solved here: this is wrong
   for a user who has since switched decks or owns several — those
   users may need to manually move a handful of entries afterward. Not
   worth a migration-time prompt flow for what should be a small,
   edge-case set of rows.
4. **Default (`game`) scope view merges by name.** Same-name,
   non-archived rows that share the same `game` collapse into a single
   line client-side. **Decided: same-game only** — a Magic "Aggro" and
   a Pokémon "Aggro" never merge just because they share a name, even
   though they're both the user's own rows. Crossing game boundaries on
   a generic archetype name would reintroduce the same category of bug
   this ticket reports, just via name collision instead of via a
   missing filter. Reuse `sharing_merge._norm()` for the match rule
   rather than a second implementation of trim/lowercase matching, per
   Constitution §4.2 (no duplicated business rules). This merge only
   applies while the user's `metagame_roster_scope` is `"game"` — under
   `"personal_deck"` scope, only the exact deck's own row shows, so
   there's nothing to merge.
5. **Edits propagate across same-name, same-game rows the user owns.**
   Changing tier/archetype on one roster row atomically updates every
   other row the user owns with the same (normalized) name and the same
   `game` — one `UPDATE ... WHERE owner_id=? AND name=? AND game=? AND
   archived_at IS NULL`, not sequential per-row writes, to avoid a
   partially-propagated state. **Decided: propagates regardless of the
   viewer's `metagame_roster_scope` setting** — including while viewing
   under `"personal_deck"` scope. This is a deliberate behavior worth
   calling out explicitly rather than leaving implicit: `metagame_roster_scope`
   only controls what's *displayed* (merged vs. per-deck), it does not
   make a deck's roster data independently editable. A user under
   `"personal_deck"` scope editing one deck's row will see it change for
   every other deck sharing that name too, even though only one deck's
   row is currently visible to them. **New same-named roster entries pre-fill
   tier/archetype from the most recently updated existing same-name/same-game
   row** (item 4's create-time convenience — this is the same conflict
   rule as backfill conflicts, see item 6). Never touches shared
   (`is_readonly`) rows — propagation and pre-fill both stay within the
   user's own owned rows, consistent with `sharing_merge.py`'s existing
   "own data wins over a sharer's" rule.
6. **Conflict tie-break.** Wherever two same-name/same-game rows
   disagree on tier/archetype (pre-existing divergence hit during
   backfill, or the source picked for item 5's create-time pre-fill),
   **the most recently updated row wins.**

## Proposed tasks

- [x] Add `personal_deck_id: Mapped[uuid.UUID]` (FK to
      `ts_personal_decks.id`, `ondelete="CASCADE"`, **not nullable**) to
      `TSMetaDeck`. `game` stays as a column but becomes always derivable
      via the FK join. **Also added `updated_at`** (not in the original
      task list) — items 5/6's "most recently updated row wins" needs a
      real timestamp to compare, and no `TSMetaDeck` column tracked edits
      before this; set explicitly by every write path (never an ORM/DB
      `onupdate` trigger, since the propagation write below is a raw
      multi-row `UPDATE`, not a per-instance ORM assignment).
- [x] Migration: add the column nullable first, run the backfill
      (items 1-3 above — grouping by `TSMatch.opponent_deck_id` /
      `personal_deck_id`, duplicating rows that map to >1 personal deck,
      assigning orphan rows to `active_personal_deck_id`), then make the
      column non-nullable. Orphan fallback when `active_personal_deck_id`
      is itself unset: the owner's oldest personal deck (confirmed with
      the user — owning roster rows implies owning at least one personal
      deck). Implemented inline in the Alembic revision
      (`e91a4c7f2b56_add_personal_deck_id_to_ts_meta_decks.py`) via
      locally-declared `sa.table()` mirrors, never importing the live ORM
      models, per Alembic's own recommended pattern.
- [x] Rework `_sync_opponent_deck_games` from overwrite-in-place to the
      duplicate-and-allocate rule (item 2), so it stays correct for
      future corrections (e.g. a personal deck's `game` PATCHed after
      today), not just the one-time migration.
- [x] Add `metagame_roster_scope` (`"game" | "personal_deck"`, default
      `"game"`) to `TSUserSettings` + settings response/PATCH schema,
      alongside the existing `active_personal_deck_id`
      (`f4b6d3a8c17e_add_metagame_roster_scope_to_ts_user_.py`).
- [x] `MetaDeckWrite`/create schema: make `personal_deck_id`
      **required**.
- [x] `MetaDecksRosterSection.handleAdd` passes the active deck's id on
      `createDeck.mutateAsync(...)`; pre-fills tier/archetype per item 5
      when an existing same-name/same-game row is found (client-side
      convenience, still validated/settable server-side).
- [x] `list_meta_decks` resolves the caller's `metagame_roster_scope`
      and `active_personal_deck_id` server-side, filters `view.meta_decks`
      either by exact `personal_deck_id` or by
      `d.game == active_deck.game`, and — under `"game"` scope —
      collapses same-name rows into one for the response (item 4), via a
      new `sharing_merge.collapse_by_name_and_game()` that reuses
      `norm_name()` (renamed from the module-private `_norm()`, promoted
      to public so both `meta_decks.py`'s propagation and this function
      can reuse the exact same match rule instead of a second
      trim/lowercase implementation in SQL).
- [x] `update_meta_deck` performs the atomic same-name/same-game
      propagation (item 5) as part of the write, excluding
      `is_readonly` rows.
- [x] Extend `build_merged_view` to also scope meta decks —
      **implemented as a separate opt-in parameter**
      (`filter_meta_decks_by_personal_deck: bool = False`), not by
      overloading the existing `personal_deck_id` parameter as originally
      described here: `stats.py` (archetype/matchup summaries) and the
      personal-deck PDF report route already call `build_merged_view`
      with `personal_deck_id` set, expecting the **full** roster back
      (only `matches` narrowed) — reusing that same parameter to also
      filter `meta_decks` would have silently narrowed what those
      unrelated endpoints return. Caught by their own existing tests
      failing during implementation, not by design up front.
- [x] `useMetaDecks()` includes the active deck id and the scope setting
      in its query key so switching either refetches correctly.
- [x] Add the scope toggle to account settings (same "Display"-section
      visual pattern already used for the S12 display-preference toggles
      in `AccountSettingsDialog`, but server-persisted via
      `useUpdateMySettings` like `active_personal_deck_id`, not a
      `localStorage` flag).
- [x] Update `MetaDecksRosterSection.test.tsx` / `useMetaDecks` tests /
      `meta_decks.py`, `personal_decks.py` (`_sync_opponent_deck_games`),
      and `sharing_merge.py` backend tests for the new model, including
      the duplicate-and-allocate and propagation behaviors. Every
      existing test across the Tamiyo Scroll suite that created a
      `TSMetaDeck` via `POST /meta-decks` (nine files) needed
      `personal_deck_id` added to its payload, and several needed an
      active personal deck selected before calling `GET /meta-decks`,
      once that endpoint's default behavior became "no active deck ->
      `[]`". Full suite: 582 passed, 97.40% coverage.

## UAT (manual, once implemented)

- [X] Default setting (`game`): with deck A (Magic) active, add roster
      entries. Create/switch to deck B (a second Magic deck) — same
      roster still shows, merged. Switch to a Pokémon deck — roster is
      empty / Pokémon-only.
- [X] Edit a roster entry's tier while deck A is active; switch to deck
      B (same game) — the edit is visible there too.
- [X] Switch the setting to `personal_deck`: deck A and deck B (both
      Magic) now show independent rows for the same-named entry. Edit
      the entry while deck A is active — switch to deck B, confirm the
      edit propagated even though it wasn't visible from B's own view
      while editing.
- [X] Switch the setting back to `game`: deck A and B's rows merge back
      into one shared view without data loss or a stale value winning
      over the more recent edit.
- [X] With a receive-shared-data user: confirm a sharer's roster entry
      folds in read-only within the correct scope, and editing the
      viewer's own row never touches the sharer's underlying row.
- [X] Confirm a Magic deck and a Pokémon deck with a coincidentally
      identical roster-entry name never merge or propagate into each
      other.
- [X] Confirm legacy pre-migration roster entries land on the expected
      personal deck(s) per the backfill rules (single match history →
      that deck; multiple → duplicated; no history → the deck that was
      active at migration time).

## Non-regression tests

- `ArchetypeSummarySection`/`MatchupSummarySection` behavior (already
  correctly scoped by deck) stays unchanged.
- Existing single-deck-per-user flows (the common case) see the roster
  they already had, unchanged, once backfill runs, under the default
  `game` scope.
- Match-list filtering by `personal_deck_id` (existing, unrelated
  `build_merged_view` use) is unaffected by extending the parameter to
  also cover meta decks.
- `_sync_opponent_deck_games`'s existing single-personal-deck case
  (today's only tested path) keeps working unchanged after it's
  reworked to also handle the multi-deck duplicate-and-allocate case.
