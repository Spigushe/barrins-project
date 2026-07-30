# S10. Card-game flag on `TSPersonalDeck`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` (FastAPI), `apps/tamiyo_scroll` (React/Vite) | / |
| **Initial date** | 2026-07-27 | Drafted 2026-07-27 |
| **Status** | 🔲 Not started — **in scope for v2.0.0 (2026-07-28)**, built as a parallel of S11 | Un-deferred from v3.0.0 on 2026-07-28: the logging gate gives it a live v2 consumer. Added to the Group S table in `../index.md` |
| **Source** | User request, 2026-07-27 conversation (scope confirmed for v2.0.0 on 2026-07-28) | / |
| **Dependency** | None (technical). Coordinates with **S3** and **S11** — all edit the match-creation path (`_validate_match_refs`), and S10/S11 share the new `PATCH /personal-decks/{id}` route | / |

---

**Deferred (2026-07-27) — superseded 2026-07-28: now in v2.0.0** (see
"Added requirement" below). The original deferral reasoning is kept for
the record: postponed to v3.0.0, to land alongside the
release where Karn Tablets/ML actually starts consuming Tamiyo Scroll
data. In v2.0.0's confirmed scope (§1.4 of `../index.md`), Karn Tablets
clusters **scraped-tournament** results (Group T), not personal decks —
`TSPersonalDeck`/`TSCardTest` aren't read by any ML pipeline yet, so this
flag would have no consumer until that changes. Revisit when a v3.0.0
plan exists and Tamiyo data is actually on Karn Tablets' input list; the
design work below is kept as-is so it doesn't need re-deriving then.

## Added requirement (2026-07-28): game gated on logging results

Per the 2026-07-28 conversation, the same gate designed for **S11**
(macrotype) applies here: **a personal deck's `game` must be set before
any match can be logged or edited on it.** The check would live in the
shared `_validate_match_refs`
([`api/tamiyo_scroll/matches.py`](../../../../apps/barrins_api/app/api/tamiyo_scroll/matches.py)),
which both `create_match` (`:99`) and `update_match` (`:118`) call,
rejecting a deck with no game with `422 personal_deck_game_required`
(mirrors S11's `personal_deck_macrotype_required`).

This changes two things previously settled on this page. Neither is
silently resolved — both are flagged for the user, per this project's
"surface the decision, don't guess" convention.

1. **It conflicts with the `magic` default/backfill above.** As designed
   today, `game` defaults to `magic` (`default=CardGame.magic`,
   `server_default="magic"`) and the migration back-fills every existing
   deck to `magic`. If `game` is never `NULL`, a "must be set before
   logging" gate **never triggers** — it is dead code. For the gate to
   have teeth, `game` must be **nullable with no default/backfill** (an
   explicit choice at creation, exactly like S11's macrotype), which
   reintroduces the same historical-deck friction S11 has: existing decks
   read `NULL` and need a `PATCH` before logging. This reverses the
   "Design decision" (recommended `server_default` magic) and the
   "migration back-fills existing rows to `magic`" non-regression test
   below. **Decided 2026-07-28**: drop the `magic` backfill. `game` is
   **nullable with no default** (`game par défaut = none`), an explicit
   required choice at creation, exactly like S11's macrotype — the gate
   has teeth, and historical decks read `NULL` until PATCHed. The "Design
   decision", "Done statement", tasks, and non-regression tests below are
   updated to match.

2. **It removes this item's deferral rationale.** S10 was deferred to
   v3.0.0 because personal-deck data has "no consumer until v3". A gate
   on logging is a **live, in-app v2 consumer** — the exact argument that
   keeps S11 in v2. And the gate cannot physically ship before the `game`
   field exists, so it can't ride into v2 on S11's back while S10 itself
   stays in v3. **Decided 2026-07-28**: S10 moves into **v2.0.0 scope**
   alongside S11 — the architecture (field + gate + PATCH) has to exist
   to ship the feature in v2. Status, dependency, and the Group S table
   are updated accordingly.

See [`../s11-personal-deck-macrotype/index.md`](../s11-personal-deck-macrotype/index.md)
for the fully-specified twin (nullable column, no backfill, gate on
create **and** update, new `PATCH /personal-decks/{id}` route,
stats-block color identity). If S10 moves into v2, it should be built as
a parallel of S11 — same shape, `CardGame` in place of
`ArchetypeCategory`.

## Context

Tag every personal deck with the card game it belongs to, so Magic decks
can be isolated from everything else when exporting data for
machine-learning training. Non-Magic decks stay in the database (they're
worth keeping) but are excluded from the training set.

The tag lives on the **deck** (`TSPersonalDeck`), not on the user or on
the individual test. `TSCardTest` already carries a `personal_deck_id`,
so the ML filter is a join (test → deck → game), with nothing duplicated.
Deck-level tagging is assumed here rather than per-test — push back if a
per-test tag is actually what's wanted.

`TSPersonalDeck`
([`apps/barrins_api/app/models/tamiyo_scroll.py:212`](../../../../apps/barrins_api/app/models/tamiyo_scroll.py#L212))
currently carries only: `id`, `owner_id`, `name`, `archived_at`,
`created_at`. No game field.

Existing hooks, all directly reusable:

- The "`StrEnum` mapped to a named PostgreSQL type" pattern already
  appears four times in the same file: `GameResult` (line 29),
  `ArchetypeCategory` (line 37), `ExpectedLevel` (line 46),
  `DecklistVersionSource` (line 54) — each exposed via
  `Enum(SomeEnum, name="ts_...")`.
- Response schema: `ResponsePersonalDeck`
  (`schemas/responses_tamiyo_scroll.py:31`).
- Input schema: `PersonalDeckCreate` (`schemas/tamiyo_scroll.py:19`),
  `extra="forbid"`.
- Creation route: `create_personal_deck`
  (`api/tamiyo_scroll/personal_decks.py:99`), which builds
  `TSPersonalDeck(owner_id=..., name=payload.name)`. Only create / list /
  archive routes exist today — **no `PATCH`**.
- Frontend: `personalDeckSchema` (zod, `schemas/tamiyoScroll.ts:40`),
  `createPersonalDeck` (`api/personalDecks.ts`, sends `{ name }` only),
  hook `useCreatePersonalDeck` (`hooks/usePersonalDecks.ts:13`).
- Creation UI: `components/layout/PersonalDeckSelector.tsx` — a
  `CommandInput` where typing a name and hitting "Create" calls
  `createDeck.mutateAsync(trimmedSearch)` with the bare string.

## Design decision: enum or boolean

**Context.** The spoken request was "Magic vs. not Magic" (a boolean
would do); the written request says "track the card game" (implying more
than one game, i.e. an enum).

**Alternatives.**

1. **`CardGame` `StrEnum`** (renamed from the originally proposed
   `TSCardGame` to match this file's existing convention — enum classes
   are unprefixed, e.g. `GameResult`, `ArchetypeCategory`; the `TS`
   prefix is reserved for model classes and the Postgres type name, e.g.
   `ts_card_game`), with values `magic`, `flesh_and_blood`, `lorcana`,
   `pokemon`, `yugioh`, `other` (to confirm — whichever games testers
   actually use).
2. **Boolean `is_magic`.**

**Trade-offs.** Same amount of work either way. Option 1 keeps the
granularity for ML filtering (`game == magic`) while preserving
fine-grained info for everything else instead of collapsing it into "not
Magic" — if a second non-Magic game ever needs distinguishing, there's no
migration to redo. Option 2 is marginally simpler but throws away that
granularity for no current benefit.

**Recommendation: option 1** (`CardGame` enum). **Decided 2026-07-28: no
default** — the column is nullable with no `server_default` and no
backfill (`game par défaut = none`); the user picks a game explicitly at
creation, mirroring S11's macrotype, and historical decks read `NULL`
until PATCHed. (The earlier `server_default="magic"` backfill is
dropped — it would have made the logging gate inert.) The enum-vs-boolean
call still stands at the enum recommendation; with the build now scoped
for v2, confirm enum-vs-boolean and the exact game list before
implementation (open question 1).

## Done statement

- `TSPersonalDeck` gains a **nullable** `game` field (`CardGame` enum,
  recommended — see design decision above), **no default, no backfill**;
  existing decks read `NULL`.
- New-deck creation **requires** `game`, enforced server-side
  (Constitution §4.1 — not a frontend-only requirement).
- Logging **or editing** a match on a deck whose `game IS NULL` is
  rejected with `422 personal_deck_game_required`.
- `PATCH /personal-decks/{id}` lets the user set/correct the game;
  setting it unblocks logging. (Shared route with S11, which sets
  `category` on the same endpoint.)
- The ML training export filters on `game == magic` via a join from
  `TSCardTest` through `personal_deck_id`, with no duplicated data
  (`NULL`-game decks are excluded until set).

## Tasks

Each item is modeled on code that already exists and is already tested.

### Enum + model + migration

- [ ] Add `class CardGame(enum.StrEnum)` in `models/tamiyo_scroll.py`
      (copy of `ArchetypeCategory`, line 37) — pending the design
      decision above.
- [ ] Add the field to `TSPersonalDeck`:
      `game: Mapped[CardGame | None]` via
      `Enum(CardGame, name="ts_card_game")`, **nullable, no
      `default`/`server_default`** (`game par défaut = none`).
- [ ] Generate the Alembic migration — add the column **nullable with no
      backfill** (existing decks stay `NULL`). Reminder: in production
      this is **manual** (`alembic upgrade head` over SSH — see the
      `post_task` in `ops/my-server/barrins_api.yml`, which explicitly
      states "This playbook never runs Alembic"). Existing migration
      `a3f8c1d9e2b7` (referenced in `card_tests.py`) is a good model to
      follow.

### Backend schemas

- [ ] Add `game` to `ResponsePersonalDeck`
      (`responses_tamiyo_scroll.py:31`) so the frontend can detect
      `NULL`-game decks.
- [ ] Add `game` to `PersonalDeckCreate` (`tamiyo_scroll.py:19`),
      **required** (no default) — a new deck must declare its game.
- [ ] Add a `PersonalDeckPatch` schema (`game: CardGame`) for the PATCH
      route — coordinate with S11's `PersonalDeckPatch` (`category`): one
      shared patch schema/route setting both fields, not two.

### Route(s)

- [ ] In `create_personal_deck` (`personal_decks.py:99`), pass
      `game=payload.game` alongside `name`.
- [ ] Add `PATCH /personal-decks/{deck_id}` — **required** (no longer
      optional): it's how historical `NULL`-game decks get unblocked.
      Reuse `_get_owned_personal_deck` (404-not-403 on cross-owner).
      **Shared with S11** (which sets `category` on the same route) —
      build once, set both fields.
- [ ] Extend `_validate_match_refs` (`matches.py`): if the deck's
      `game IS NULL`, raise `HTTPException(422,
      detail="personal_deck_game_required")`. Called by both
      `create_match` (`:99`) and `update_match` (`:118`) — covers create
      and edit. **Coordinate with S3 and S11**, which touch the same
      helper/query — don't let one PR clobber another's `SELECT` shape.

### Frontend, data layer

- [ ] Add `game` to `personalDeckSchema`
      (zod, `schemas/tamiyoScroll.ts:40`), **required**.
- [ ] `createPersonalDeck` (`api/personalDecks.ts`) sends `{ name, game }`
      instead of `{ name }`.
- [ ] Add `updatePersonalDeck` (PATCH) + a `useUpdatePersonalDeck` hook —
      shared with S11.
- [ ] Treat `422 personal_deck_game_required` from the match-write path
      as a typed error the UI branches on — not a generic toast.

### Frontend, creation UI

The one item that isn't purely mechanical. Today, creation happens in a
single gesture in `PersonalDeckSelector.tsx`: type a name, "Create" sends
the bare string.

- [ ] Add a **required** game selector (Radix `Select`, **no default** —
      the user must pick) next to the Create button.
- [ ] Pass the chosen value into `createDeck.mutateAsync(...)`, which now
      takes name + game instead of a plain string.
- [ ] For `NULL`-game decks: a "game required before logging results"
      affordance (inline set-game control calling the PATCH), in the deck
      view and at the match-logging entry point
      (`pages/suivi-bo3/MatchForm.tsx`).
- [ ] One-time, dismissible migration notice: v2 introduces the game
      field; existing decks must set it before new results.
- [ ] Update the associated tests (`PersonalDeckSelector.test.tsx`).

## Open questions

### 1. Enum vs. boolean, and enum values at launch

See "Design decision" above. Also needs confirming: which games to
include from day one — the draft list is `magic`, `flesh_and_blood`,
`lorcana`, `pokemon`, `yugioh`, `other`.

### 2. Editable after creation? — Resolved 2026-07-28

Yes: the `PATCH` route is **required**, both to correct a mistaken game
and — mainly — to let historical `NULL`-game decks be set so they can log
again. No longer optional.

### 3. ML export path

Does the ML export read the database directly, or does it go through a
dedicated API route that would need to be planned for here? Not yet
confirmed.

### 4. Does this need an ADR?

The enum-vs-boolean call is the kind of decision this project usually
tracks as an ADR (Constitution §16.2). Not yet confirmed whether one is
wanted for this item specifically.

## UAT (manual)

- [ ] Create a personal deck **without** picking a game → creation
      refused (client and server).
- [ ] Create a personal deck with a game → saved and displayed correctly.
- [ ] On a pre-migration deck (`game` NULL): attempt to log a match →
      refused with the inline "set game" prompt; set it via the inline
      control; retry → succeeds.
- [ ] Attempt to **edit** an existing match on a still-NULL deck → also
      refused (gate covers update).
- [ ] Confirm the migration adds the column `NULL` for every existing
      deck, with no backfill.

## Non-regression tests

- Backend: `_validate_match_refs` rejects `NULL`-game decks on **both**
  create and update with `422 personal_deck_game_required`; accepts once
  the game is set.
- Backend: `PersonalDeckCreate` rejects a payload missing `game`; the
  `PATCH` route sets it; 404-not-403 on cross-owner PATCH.
- Backend: the migration adds a **nullable** column with **no backfill**;
  existing rows read `NULL`.
- ML export join: a query filtered on `game == magic` excludes non-Magic
  decks' tests and includes Magic decks' tests (`NULL`-game decks
  excluded until set).
- Confirm existing `PersonalDeckSelector.test.tsx` and personal-deck
  create/list tests still pass with the new required field.

## See also

- [`../s9-tournament-session/index.md`](../s9-tournament-session/index.md)
  — another item raised in conversation on 2026-07-27, not part of the
  original v2.0.0-bump request items.
