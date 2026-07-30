# S12. UI/UX polish bundle — four small `tamiyo_scroll` fixes

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tamiyo_scroll` (React/Vite) only | No `barrins_api` change in any of the four |
| **Initial date** | 2026-07-30 | Drafted 2026-07-30 |
| **Status** | 🔲 Not started — unblocked, can start immediately | / |
| **Source** | User request, 2026-07-30 — pulled in from the "v2.0.0 candidates" section of `docs/content/front/tamiyo_scroll/roadmap.md` | / |
| **Dependency** | None. Four independent frontend fixes, bundled under one item ID because each is individually too small to warrant its own S-number | / |

---

## Context

Four small, unrelated Tamiyo Scroll polish items were evaluated on the
feature-roadmap backlog page and judged cheap enough (no schema, no new
endpoint, no design pass) to fold into v2.0.0 without competing
meaningfully with S1–S11 for engineering time. Bundled here as one
item so they're tracked, not because they're related to each other —
each of the four tasks below can be implemented, reviewed, and shipped
independently.

**Verified against the code (2026-07-30, `proj/v2.0.0-bump`):**

1. **Personal-deck creation isn't clearly signaled.**
   `PersonalDeckSelector.tsx` — the "create" affordance is a plain
   `CommandItem` (`Create "{trimmedSearch}"`, ~L145-154) that only
   appears once the user types a non-matching search string, with no
   icon and the same visual weight as an ordinary deck-selection item
   (~L117-144) above it — nothing distinguishes "this row creates a new
   deck" from "this row selects an existing one."
2. **Tested-cards select vs. BO3 opponent select are structurally
   different**, not just visually:
   - Tested cards: `pages/suivi-bo3/CardTestsSection.tsx` (~L150-168
     create form, ~L240-257 edit row) — a plain shadcn `<Select>`/
     `<SelectItem>`, options from `deckOptions = metaDecks ?? []`
     (~L94), rendering only `{deck.name}`. No search, no create-inline,
     no shared-deck indicator.
   - BO3 opponent: `pages/suivi-bo3/MatchForm.tsx`, `OpponentDeckField`
     (~L149) — a `Popover`+`Command` combobox (~L222-290), same pattern
     as `PersonalDeckSelector`. Supports live search, shows a
     "shared — tap to add to your roster" sub-label for
     `deck.is_readonly` decks (~L268-272), and an inline "Create "…""
     item (~L277-284) opening a create dialog with Tier/Category
     selects.
   - Both pull from the same `metaDecks` data — the inconsistency is
     genuinely combobox-with-search-and-create vs. plain native select,
     not a cosmetic mismatch.
3. **"Final turn" is a free-text notes field, not a turn number.**
   Display: `pages/suivi-bo3/MatchJournalSection.tsx` (~L240-245,
   `<Label>Final turn</Label>`, renders `viewingMatch.final_turn`).
   Entry: `pages/suivi-bo3/MatchForm.tsx` (~L516-526, a `Textarea` bound
   to `draft.finalTurn`, alongside "Opening hand" and "Turning point").
   Schema: `schemas/tamiyoScroll.ts` — `final_turn: z.string().nullable()`
   (~L83, and ~L172 for the write schema). This is purely a display-label
   change; the field name (`final_turn`/`finalTurn`) stays as-is on both
   ends — no API/schema rename, no migration.
4. **The "Games" column already counts matches — only the label is
   wrong.** `pages/metagame/StatsSections.tsx`, `MatchupSummarySection`
   (~L97): header `<TableHead>Games</TableHead>` (~L113), populated by
   `row.match_count` (~L141) from `useMatchupSummary` — i.e. it's already
   counting completed BO3 matches. Pure label fix, no data-layer change.

## Design decisions

- **Item 1 resolved without an icon dependency: a `[new]` text label,
  not an icon.** A small colored badge/text (`[new]`, styled e.g.
  `text-emerald-600 dark:text-emerald-400`) rendered next to the
  `Create "{trimmedSearch}"` row while the user is typing a
  non-matching search string is plain Tailwind — no icon library, no
  new dependency, no §4.7/§22 approval step needed. This replaces the
  icon approach from the initial draft; the icon-dependency gap noted
  below is no longer a blocker for item 1. It only needs to appear
  while actively typing a non-matching value, i.e. exactly when the
  create row itself is shown — no separate "is typing" state to track,
  it's the same condition already gating the row's existence.
- **Items 3 and 4 are label-only.** No underlying field/column is
  renamed at the data layer, consistent with Constitution §4.4
  (backward compatibility) — only the user-facing string changes.
- **Item 2 reuses an existing pattern, doesn't invent one.** The target
  shape (search + shared-badge + inline create) already exists and is
  tested in `OpponentDeckField`/`PersonalDeckSelector` — this is a
  rebuild-on-the-same-pattern task, not new UX design.

## Done statement

- Personal-deck creation's `CommandItem` visually signals "this creates
  a new deck" via a green `[new]` text label rendered next to it while
  the search doesn't match an existing deck — no icon, no new
  dependency.
- The tested-cards matchup select in `CardTestsSection.tsx` (both the
  create form and the edit row) is rebuilt on the same
  `Popover`+`Command` combobox pattern as `OpponentDeckField`, including
  search and the shared-deck sub-label; behavior parity confirmed
  against `MatchForm.tsx`'s existing implementation.
- "Final turn" is relabelled ("Winning/losing turns", pending final
  copy confirmation — see Open questions) in both
  `MatchJournalSection.tsx`'s display and `MatchForm.tsx`'s entry field
  (`Label` + any placeholder text). `final_turn`/`finalTurn` identifiers
  are unchanged.
- `StatsSections.tsx`'s matchup-summary column header reads "Matches"
  instead of "Games". `match_count`/its query are unchanged.

## Tasks

### 1. Personal-deck creation — `[new]` label

- [ ] Add a `[new]` badge/text span next to `Create "{trimmedSearch}"`
      in `PersonalDeckSelector.tsx`'s `CommandItem` (~L145-154), styled
      distinctly (e.g. `text-emerald-600 dark:text-emerald-400`, small/
      uppercase to read as a tag, not body text).
- [ ] Confirm it reads clearly against both the row's existing text and
      the popover's light/dark background (Tailwind dark-mode variant
      needed, not just one fixed color).
- [ ] Update `PersonalDeckSelector.test.tsx` if it asserts on the create
      row's rendered content.

### 2. Tested-cards select ↔ BO3 opponent select parity

- [ ] Rebuild the tested-cards deck select in `CardTestsSection.tsx`
      (create form ~L150-168, edit row ~L240-257) on the
      `Popover`+`Command` combobox pattern used by `OpponentDeckField`
      in `MatchForm.tsx` (~L149-290).
- [ ] Carry over the "shared — tap to add to your roster" sub-label for
      `deck.is_readonly` decks (mirroring ~L268-272).
- [ ] Decide (see Open questions) whether the inline "Create "…""
      affordance also belongs on the tested-cards select, or whether
      that select should stay selection-only.
- [ ] Update/add tests covering the new combobox behavior for
      `CardTestsSection`.

### 3. "Final turn" label rename

- [ ] Update the `<Label>` text in `MatchJournalSection.tsx` (~L242).
- [ ] Update the `Label`/placeholder text in `MatchForm.tsx` (~L516-526).
- [ ] Confirm final copy (see Open questions) before implementing —
      "Winning/losing turns" was the suggested alternative, not decided.
- [ ] No change to `final_turn`/`finalTurn` in
      `schemas/tamiyoScroll.ts` or anywhere in `barrins_api`.

### 4. Matchup-summary "Games" → "Matches"

- [ ] Update the `<TableHead>` text in `StatsSections.tsx` (~L113).
- [ ] Confirm no other page reuses the same "Games" header text for a
      column that's genuinely counting individual games (would make the
      same string a mismatch fix in one place and correct in another).

## Open questions (flagged, not guessed)

1. **Exact wording for the `[new]` label (item 1).** `[new]` is the
   working text; a plain "New" badge (no brackets) is an equally
   reasonable alternative. Not a blocker, just unconfirmed copy — pick
   either during implementation unless the user has a preference.
2. **Exact copy for the "Final turn" rename.** The roadmap backlog
   suggested "winning/losing turns" as an alternative, not a final
   decision. Given the field is free text (not a turn number — see
   Context), "Final turn" may already be a reasonable-enough label;
   confirm the replacement wording, and whether it should stay a single
   field or imply splitting winning/losing into two inputs (**out of
   scope here** if so — that would be a schema change, not a label fix,
   and would need its own item).
3. **Does the tested-cards select also get inline "create new meta
   deck"?** `OpponentDeckField` has it; whether the tested-cards
   context wants the same affordance (creating a meta-deck from within
   a card-test row) isn't specified by the original request. Default
   assumption unless corrected: match the combobox/search/shared-badge
   behavior, leave inline-create out for now (out of scope) since the
   request was about select *consistency*, not adding a new creation
   path.

## UAT (manual)

- [ ] Type a non-matching deck name into the personal-deck selector →
      the create row shows a `[new]` label, readable in both light and
      dark mode, visually distinguishing it from a normal deck row.
- [ ] Open the tested-cards deck select on both the create form and an
      existing row's edit state → search works, shared decks show the
      sub-label, behavior matches the BO3 opponent select side by side.
- [ ] View an existing match's journal entry with a "Final turn" value
      set → the relabelled text displays, value unchanged.
- [ ] View the matchup summary table → column reads "Matches", value
      unchanged from before (still `match_count`).

## Non-regression tests

- Frontend: existing `PersonalDeckSelector.test.tsx` still passes with
  the new `[new]` label added to the create row.
- Frontend: `CardTestsSection` tests (if any) still pass against the
  rebuilt select; add coverage for search/shared-badge behavior if none
  exists today.
- Frontend: no `final_turn`/`finalTurn` reference anywhere breaks —
  confirm via existing `MatchForm`/`MatchJournalSection` tests, which
  should only need label-string assertions updated, not logic changes.
- Frontend: `StatsSections`/matchup-summary tests, if any assert on the
  literal header text "Games", updated to "Matches".

## See also

- `docs/content/front/tamiyo_scroll/roadmap.md` — the backlog page these
  four items were pulled from ("v2.0.0 candidates" section).
