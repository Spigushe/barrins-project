# S11. Macrotype (archetype category) on `TSPersonalDeck`, required to log results

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` (FastAPI), `apps/tamiyo_scroll` (React/Vite) | / |
| **Initial date** | 2026-07-28 | Drafted 2026-07-28 |
| **Status** | 🔲 Not started — unblocked, can start immediately (enum, model pattern, and color identity all already exist) | / |
| **Source** | User request, 2026-07-28 conversation | / |
| **Dependency** | None (technical). Coordinates with **S3** — both edit the match-creation path (`_validate_match_refs` / `create_match`) | / |

---

## Context

Tag every personal deck with its **macro-archetype**, and require it
before any match can be logged or edited on that deck. Two purposes,
both stated by the user: a **functional gate now** (you can't record
results on an unclassified deck) and a **labelled feature for future
ML** (Karn Tablets, v3.0.0).

**Verified against the code (2026-07-28, `proj/v2.0.0-bump`):**

- The macrotype list already exists as `ArchetypeCategory`
  ([`models/tamiyo_scroll.py:37`](../../../../apps/barrins_api/app/models/tamiyo_scroll.py#L37)):
  `aggro`, `midrange`, `control`, `combo`, docstring *"determines the
  display color on the frontend."* It is the **same enum the roster
  uses** (`TSMetaDeck.category`,
  [`:185`](../../../../apps/barrins_api/app/models/tamiyo_scroll.py#L185)).
  "Same list as the roster" = this enum, reused as-is.
- The Postgres type `ts_archetype_category` already exists, created by
  [`ef2a570b4f4f_add_tamiyo_scroll_tracker_tables.py:42`](../../../../apps/barrins_api/alembic/versions/ef2a570b4f4f_add_tamiyo_scroll_tracker_tables.py#L42)
  for the roster. The migration here **reuses** it — it must not
  `CREATE TYPE` again.
- `TSPersonalDeck`
  ([`:212`](../../../../apps/barrins_api/app/models/tamiyo_scroll.py#L212))
  currently carries only `id`, `owner_id`, `name`, `archived_at`,
  `created_at` — **no category**.
- The full color identity is already wired to `ArchetypeCategory` on the
  frontend: `ARCHETYPE_LABELS` / `ARCHETYPE_TEXT_CLASS` /
  `ARCHETYPE_BORDER_CLASS` in `lib/mtg-format.ts`, **consumed by the
  stats block** (`pages/metagame/StatsSections.tsx:46-56`). The select
  pattern to copy already exists in
  `pages/metagame/MetaDecksSections.tsx:159`. "Same color identity as
  the stats block" is satisfied by reusing these tokens — no new colors.
- **No `PATCH` route exists on personal decks today**
  (`api/tamiyo_scroll/personal_decks.py` — create / list / archive
  only). The migration path this whole item depends on is genuinely new
  backend scope.

**Distinct from S10 (why this is v2, not deferred).** S10 (a `game`
flag on the same model) is deferred to v3.0.0 for want of a consumer —
personal-deck data isn't read by any ML pipeline in v2. Macrotype has a
**live in-app consumer in v2**: the logging gate. That is what scopes it
into v2.0.0 while S10 stays deferred. (S10 has since been given the same
gate requirement — see its page; that reopens S10's deferral, flagged
there.)

## Design decisions (frozen 2026-07-28)

- **Reuse `ArchetypeCategory`**, no new enum.
- **Nullable column, no backfill** (Option A). Existing decks read
  `NULL`; no guessed value — consistent with S3's "no retroactive
  guessing" and Constitution §4.1 (the backend never fabricates a
  business value the user didn't supply).
- **Required at creation for new decks** — added to `PersonalDeckCreate`
  with **no default**; a new deck must declare its macrotype.
- **Gate blocks both create and edit of a match.** The check lives in
  the shared `_validate_match_refs`
  (`api/tamiyo_scroll/matches.py`), which **both** `create_match`
  (`:99`) and `update_match` (`:118`) call. A deck with `category IS
  NULL` cannot have a new match logged **nor** an existing match
  re-saved against it. This is deliberate ("block create and modify").
- **Gate error = 422** Unprocessable Entity with a stable machine
  `detail` code `personal_deck_macrotype_required`, which the frontend
  intercepts to show an inline "set macrotype" affordance. Not 404 — the
  deck exists and is owned; this is an invalid-state, not a not-found.
  (409 Conflict is the only alternative considered; 422 chosen because
  the payload targets a resource in an invalid state, not a concurrent-
  write conflict. See open question below.)
- **Historical decks are unblocked by a new `PATCH /personal-decks/{id}`
  route** (none exists today). Setting the macrotype clears the gate.
- **UI color identity**: the creation select and the deck badge reuse
  the exact `ARCHETYPE_*_CLASS` tokens the stats block uses.

## Done statement

- `ts_personal_decks` gains a **nullable** `category` column
  (`ArchetypeCategory`, via `Enum(ArchetypeCategory,
  name="ts_archetype_category")`, reusing the existing type).
- New-deck creation **requires** `category`, enforced server-side
  (Constitution §4.1 — not a frontend-only requirement).
- Logging **or editing** a match on a deck whose `category IS NULL` is
  rejected with `422 personal_deck_macrotype_required`.
- Existing decks read `NULL` after migration — no backfill, no guess.
- `PATCH /personal-decks/{id}` lets the user set/correct the macrotype;
  setting it unblocks logging.
- The deck UI shows the macrotype as a colored badge (stats-block
  tokens) and, when `NULL`, a "macrotype required before logging"
  affordance with an inline fix.

## Tasks

### Enum + model + migration

- [ ] **No new enum** — reuse `ArchetypeCategory`
      (`models/tamiyo_scroll.py:37`).
- [ ] Add `category: Mapped[ArchetypeCategory | None]` to
      `TSPersonalDeck` (`:212`) via `Enum(ArchetypeCategory,
      name="ts_archetype_category")`, **nullable, no `server_default`**.
- [ ] Alembic migration: add the nullable column, **reusing** the
      existing `ts_archetype_category` type (pass a pre-built
      `postgresql.ENUM(..., name="ts_archetype_category",
      create_type=False)` so it isn't recreated). Reminder: production
      Alembic is **manual** (`alembic upgrade head` over SSH — the
      `post_task` in `ops/my-server/barrins_api.yml` states the playbook
      never runs Alembic). Follow `ef2a570b4f4f` as the model.

### Backend schemas

- [ ] Add `category: ArchetypeCategory` to `PersonalDeckCreate`
      (`schemas/tamiyo_scroll.py:19`), **required** (no default). Note
      the schema already sets `extra="forbid"`.
- [ ] Add `category: ArchetypeCategory | None` to `ResponsePersonalDeck`
      (`responses_tamiyo_scroll.py:31`) so the frontend can detect
      `NULL` decks.
- [ ] Add a `PersonalDeckPatch` schema (`category: ArchetypeCategory`)
      for the new route. **Added 2026-07-30**: also add an optional
      `name` field (renaming) to this same shared schema/route — see
      `../s10-personal-deck-game-flag/index.md`'s "Added requirement"
      section for why deck renaming now matters (S1's sharing merge is
      name-keyed) and what the frontend needs.

### Routes

- [ ] In `create_personal_deck` (`personal_decks.py:99`), pass
      `category=payload.category` alongside `name`.
- [ ] Add `PATCH /personal-decks/{deck_id}` — reuse
      `_get_owned_personal_deck` (404-not-403 on cross-owner, the house
      pattern), set `category`, return `ResponsePersonalDeck`. **This
      route does not exist today.**
- [ ] Extend `_validate_match_refs` (`matches.py`) to also read the
      deck's `category`; if `NULL`, raise `HTTPException(422,
      detail="personal_deck_macrotype_required")`. It is called by both
      `create_match` (`:99`) and `update_match` (`:118`) — the gate
      covers both, as intended. **Coordinate with S3**: S3 widens the
      same resolution query (to stamp the current decklist version);
      write the two so neither PR clobbers the other's `SELECT` shape.

### Frontend, data layer

- [ ] Add `category` to `personalDeckSchema` (zod,
      `schemas/tamiyoScroll.ts:40`).
- [ ] `createPersonalDeck` (`api/personalDecks.ts`) sends
      `{ name, category }` instead of `{ name }`.
- [ ] Add `updatePersonalDeck` (PATCH) + a `useUpdatePersonalDeck` hook,
      sibling of `useCreatePersonalDeck` (`hooks/usePersonalDecks.ts`).
- [ ] Treat `422 personal_deck_macrotype_required` from the match-write
      path as a **typed** error the UI branches on — not a generic toast.

### Frontend, UI

- [ ] Add a macrotype `<Select>` to the deck-creation gesture
      (`components/layout/PersonalDeckSelector.tsx`), **required**,
      options from `ARCHETYPE_LABELS`, each rendered with
      `ARCHETYPE_TEXT_CLASS` — same identity as the stats block. Copy the
      pattern from `MetaDecksSections.tsx:159`.
- [ ] Show the deck's macrotype as a colored badge (same tokens)
      wherever the deck is displayed or selected.
- [ ] For `NULL`-macrotype decks: a "macrotype required before logging
      results" affordance (badge + inline set-macrotype control calling
      the new PATCH), surfaced in the deck view and at the point the user
      tries to log a match (`pages/suivi-bo3/MatchForm.tsx`).
- [ ] One-time, dismissible migration notice explaining v2 introduces
      the macrotype and existing decks must set it before new results.
- [ ] Update `PersonalDeckSelector.test.tsx`.

## Open questions (flagged, not guessed)

1. **Error code**: 422 (recommended above, with rationale) vs 409. The
   only soft sub-choice left. Confirm if 409 is preferred.
2. **Stats dimension?** Should macrotype become a filter/grouping axis
   for personal-deck stats in v2, or stay informational + a logging gate
   only for now? The request didn't ask for it; **not** scoped as a task
   here. Confirm before adding.
3. **ADR?** The "reuse roster enum + nullable + no backfill + gate on
   both create and update" shape is the kind of decision this project
   usually records (Constitution §16.2). Confirm whether an ADR is
   wanted.

## UAT (manual)

- [ ] Create a new personal deck **without** picking a macrotype →
      creation refused (client and server).
- [ ] Create a new personal deck **with** a macrotype → saved; the badge
      shows the stats-block color for that archetype.
- [ ] On a pre-migration deck (`category` NULL): attempt to log a match →
      refused with the inline "set macrotype" prompt; set it via the
      inline control; retry → succeeds.
- [ ] Attempt to **edit** an existing match on a still-NULL deck → also
      refused (confirms the gate covers update, per "block create and
      modify").
- [ ] Confirm the migration adds the column `NULL` for every existing
      deck, with no backfilled value.

## Non-regression tests

- Backend: `_validate_match_refs` rejects NULL-macrotype decks on **both**
  create and update with `422 personal_deck_macrotype_required`; accepts
  once the macrotype is set.
- Backend: `PersonalDeckCreate` rejects a payload missing `category`; the
  `PATCH` route sets it; 404-not-403 on cross-owner PATCH (same pattern
  as `tests/tamiyo_scroll/test_ownership.py`).
- Backend: the migration adds a nullable column **reusing**
  `ts_archetype_category` without recreating the type; existing rows read
  `NULL`.
- Frontend: existing `PersonalDeckSelector.test.tsx` and personal-deck
  create/list tests still pass with the new required field; the 422
  branch renders the inline fix, not a generic error.
- Confirm S3's match tests and the existing win-rate/coloring
  calculations are unaffected by the shared `create_match` path.

## See also

- [`../s3-match-decklist-version/index.md`](../s3-match-decklist-version/index.md)
  — shares the match-creation path; coordinate the `_validate_match_refs`
  / `create_match` edits.
- [`../s10-personal-deck-game-flag/index.md`](../s10-personal-deck-game-flag/index.md)
  — sibling field on `TSPersonalDeck`, carrying the same "must be set
  before logging results" gate. Brought into v2.0.0 on 2026-07-28 and
  built as a parallel of this item; the two **share** the new
  `PATCH /personal-decks/{id}` route and `PersonalDeckPatch` schema
  (one endpoint sets both `category` and `game`).
