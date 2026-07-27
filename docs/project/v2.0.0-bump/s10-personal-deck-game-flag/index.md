# S10. Card-game flag on `TSPersonalDeck`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` (FastAPI), `apps/tamiyo_scroll` (React/Vite) | / |
| **Initial date** | 2026-07-27 | Drafted 2026-07-27 |
| **Status** | 🔲 Deferred to v3.0.0 — not part of `proj/v2.0.0-bump` scope | Not added to the Group S table in `../index.md`; kept here as recorded background, same treatment as this document's Playwright note |
| **Source** | User request, 2026-07-27 conversation (not part of the original v2.0.0-bump request items) | / |
| **Dependency** | None | / |

---

**Deferred (2026-07-27).** Postponed to v3.0.0, to land alongside the
release where Karn Tablets/ML actually starts consuming Tamiyo Scroll
data. In v2.0.0's confirmed scope (§1.4 of `../index.md`), Karn Tablets
clusters **scraped-tournament** results (Group T), not personal decks —
`TSPersonalDeck`/`TSCardTest` aren't read by any ML pipeline yet, so this
flag would have no consumer until that changes. Revisit when a v3.0.0
plan exists and Tamiyo data is actually on Karn Tablets' input list; the
design work below is kept as-is so it doesn't need re-deriving then.

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

**Recommendation: option 1** (`CardGame` enum), default value `magic` as
a `server_default`, so the migration back-fills existing decks (all
Magic today) with no manual step. Not yet decided by the user.

## Done statement

- `TSPersonalDeck` gains a `game` field (`CardGame` enum, recommended —
  see design decision above; final type depends on that choice),
  defaulting to `magic` for existing and new decks unless specified
  otherwise.
- Deck creation (backend route and frontend UI) lets the user pick the
  game at creation time, defaulting to Magic.
- The ML training export filters on `game == magic` via a join from
  `TSCardTest` through `personal_deck_id`, with no duplicated data.
- Whether the game is editable after creation depends on open question
  2 below.

## Tasks

Each item is modeled on code that already exists and is already tested.

### Enum + model + migration

- [ ] Add `class CardGame(enum.StrEnum)` in `models/tamiyo_scroll.py`
      (copy of `ArchetypeCategory`, line 37) — pending the design
      decision above.
- [ ] Add the field to `TSPersonalDeck`:
      `game: Mapped[CardGame]` via `Enum(CardGame, name="ts_card_game")`,
      `default=CardGame.magic`, `server_default="magic"`.
- [ ] Generate the Alembic migration. Reminder: in production this is
      **manual** (`alembic upgrade head` over SSH — see the `post_task`
      in `ops/my-server/barrins_api.yml`, which explicitly states "This
      playbook never runs Alembic"). Existing migration `a3f8c1d9e2b7`
      (referenced in `card_tests.py`) is a good model to follow.

### Backend schemas

- [ ] Add `game` to `ResponsePersonalDeck`
      (`responses_tamiyo_scroll.py:31`).
- [ ] Add `game` to `PersonalDeckCreate` (`tamiyo_scroll.py:19`),
      optional with a `magic` default so a caller that only sends `name`
      doesn't break.

### Route(s)

- [ ] In `create_personal_deck` (`personal_decks.py:99`), pass
      `game=payload.game` alongside `name`. One line.
- [ ] Optional: `PATCH /personal-decks/{id}` route to correct the game
      after creation (see open question 2).

### Frontend, data layer

- [ ] Add `game` to `personalDeckSchema`
      (zod, `schemas/tamiyoScroll.ts:40`).
- [ ] `createPersonalDeck` (`api/personalDecks.ts`) sends `{ name, game }`
      instead of `{ name }`.

### Frontend, creation UI

The one item that isn't purely mechanical. Today, creation happens in a
single gesture in `PersonalDeckSelector.tsx`: type a name, "Create" sends
the bare string.

- [ ] Add a game selector (Radix `Select`, default Magic) next to the
      Create button.
- [ ] Pass the chosen value into `createDeck.mutateAsync(...)`, which now
      takes name + game instead of a plain string.
- [ ] Update the associated tests (`PersonalDeckSelector.test.tsx`).

## Open questions

### 1. Enum vs. boolean, and enum values at launch

See "Design decision" above. Also needs confirming: which games to
include from day one — the draft list is `magic`, `flesh_and_blood`,
`lorcana`, `pokemon`, `yugioh`, `other`.

### 2. Editable after creation?

If a tester can pick the wrong game, the `PATCH` route (see Tasks) is
needed. Otherwise it's skipped and the game is fixed at creation time.
Not yet decided.

### 3. ML export path

Does the ML export read the database directly, or does it go through a
dedicated API route that would need to be planned for here? Not yet
confirmed.

### 4. Does this need an ADR?

The enum-vs-boolean call is the kind of decision this project usually
tracks as an ADR (Constitution §16.2). Not yet confirmed whether one is
wanted for this item specifically.

## UAT (manual)

- [ ] Create a personal deck via the UI, pick a non-default game; confirm
      it's saved and displayed correctly.
- [ ] Create a personal deck without touching the game selector; confirm
      it defaults to Magic.
- [ ] Confirm existing (pre-migration) decks read back as `magic` after
      the migration runs.

## Non-regression tests

- New backend test: `PersonalDeckCreate` defaults `game` to `magic` when
  omitted; the migration back-fills existing rows to `magic`.
- New test for the ML export join: a query filtered on `game == magic`
  excludes non-Magic decks' tests and includes Magic decks' tests.
- Confirm existing `PersonalDeckSelector.test.tsx` and personal-deck
  creation/listing tests are unaffected by the new field.

## See also

- [`../s9-tournament-session/index.md`](../s9-tournament-session/index.md)
  — another item raised in conversation on 2026-07-27, not part of the
  original v2.0.0-bump request items.
