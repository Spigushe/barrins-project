# S12. UI/UX polish bundle — twelve small `tamiyo_scroll` fixes

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tamiyo_scroll` (React/Vite) only | No `barrins_api` change in any of the four |
| **Initial date** | 2026-07-30 | Drafted 2026-07-30 |
| **Status** | 🔲 Not started — unblocked, can start immediately | / |
| **Source** | Items 1-4: User request, 2026-07-30 — pulled in from the "v2.0.0 candidates" section of `docs/content/front/tamiyo_scroll/roadmap.md`. Items 5-12: User request, 2026-07-31 | / |
| **Dependency** | None. Twelve independent frontend fixes, bundled under one item ID because each is individually too small to warrant its own S-number | / |

---

## Context

Twelve small, unrelated Tamiyo Scroll polish items were evaluated on
the feature-roadmap backlog page and judged cheap enough (no schema,
no new endpoint, no design pass) to fold into v2.0.0 without competing
meaningfully with S1–S11 for engineering time. Bundled here as one
item so they're tracked, not because they're related to each other —
each of the twelve tasks below can be implemented, reviewed, and
shipped independently.

Items 5-9 target `MatchupSummarySection` (the "Match-up summary" table
on the Metagame tab — the results synthesis). Items 10-12 target
`MetaDecksRosterSection` (the "Deck roster (MUR)" table, same tab).

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
5. **Match-up summary columns are all unweighted (~L106-114).** `Vs.
   deck` (~L107) has no width class and gets whatever space is left;
   the other six headers (`Winrate global`, `Winrate OTP`, `Winrate
   OTD`, `W/L OTP`, `W/L OTD`, `Games`, ~L108-113) also have no width
   class, so on a wide viewport they end up sharing space roughly
   evenly with the deck-name column instead of staying compact.
6. **The winrate-band legend renders below the table, not above it.**
   `MatchupSummarySection`'s `<Table>` (~L104-163) comes first, and the
   `WINRATE_BANDS` legend (~L23-29 for the data, ~L165-172 for the
   render) is the last thing in the `Card` — a reader hits the colored
   cells before knowing what the colors mean.
7. **W/L OTP and W/L OTD are already not bold, but render in the
   default foreground color, not grey.** `TableCell` (`components/ui/
   table.tsx` ~L49-51) applies no color/weight class of its own, and
   the two cells (~L139-140) only add `font-mono` — no `font-bold` is
   present today, so "not bold" is already true; "grey" is not — they
   read in the same color as every other data cell instead of a muted
   tone.
8. **No existing mechanism ties a row's background to its winrate
   band.** `winrateTextClass` (`lib/mtg-format.ts` ~L60-67) only
   returns a *text* color class per band and is applied per-cell
   (~L129-137), not per-row; there is no row-level background variant
   today, opt-out or otherwise.
9. **`ratio_otp`/`ratio_otd` arrive from the backend as a single
   pre-formatted `"wins-losses"` string, not separate numbers.**
   `apps/barrins_api/app/services/tamiyo_scroll/stats.py`, `_ratio()`
   (~L106-107): `f"{wins}-{losses}"`. The schema
   (`app/schemas/responses_tamiyo_scroll.py` ~L69-70) types both fields
   as `str`. The frontend never sees raw win/loss counts for these two
   columns — only the formatted string rendered as-is (~L139-140).
10. **The archetype cell in the deck roster is a plain, uncolored
    `<Select>`.** `pages/metagame/MetaDecksSections.tsx`, `RosterRow`
    (~L237-256) — a `Select`/`SelectTrigger` bound to `deck.category`
    with no color class. Elsewhere in the same file
    (`ArchetypeSummarySection`, `StatsSections.tsx` ~L45-57) archetype
    is already color-coded via `ARCHETYPE_TEXT_CLASS`/
    `ARCHETYPE_BORDER_CLASS` (`lib/mtg-format.ts` ~L28-40) — the roster
    doesn't reuse that mapping yet.
11. **There is no existing tier → color mapping.** `TIERS` in
    `MetaDecksSections.tsx` (~L36) is just `[0, 0.5, 1, 1.5, 2, 2.5,
    3]`; the Tier `<Select>` cell (~L193-212) has no color/background
    class. Unlike the archetype colors (item 10) or the five-band
    winrate scale (`WINRATE_BANDS`, ~L23-29), no 3-color tier scale
    exists anywhere in the codebase to reuse — this needs a new
    mapping, not a reuse of an existing one.
12. **Deck deletion in the roster has no confirmation step.**
    `MetaDecksSections.tsx`, `RosterRow`'s delete button (~L274-276):
    `<Button ... onClick={onDelete}>✕</Button>` calls
    `archiveDeck.mutateAsync(deck.id)` (~L110-112) directly on click —
    a single misclick removes the deck with no prompt.

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
- **Items 8, 9, 10, 11 are display *preferences*, stored client-side
  (`localStorage`), not new fields on the backend `UserSettings`
  model.** The only existing settings mechanism
  (`useMySettings`/`useUpdateMySettings`, `hooks/useSettings.ts`) is a
  full API round-trip backed by a DB column per setting
  (`data_shared`, `receive_shared_data` — see
  `app/api/tamiyo_scroll/settings.py`) and exists to control
  cross-account data sharing, not per-user display cosmetics. Adding
  four purely-visual toggles there would mean a migration and new
  schema fields for something that never needs to be visible to
  another account or synced server-side — out of scope for a bundle
  explicitly framed as frontend-only (see **Target** above). They still
  live in the same `AccountSettingsDialog.tsx` UI, in a new "Display"
  section, just backed by `localStorage` instead of a mutation.
  Trade-off: these four prefs won't follow the user across browsers/
  devices, unlike `data_shared`. Flagged as Open question 4 in case
  that trade-off isn't acceptable.
- **Item 8's row-background coloring reuses the existing five
  `WINRATE_BANDS` thresholds, not new ones**, and keys off
  `row.winrate_global` (the same value already driving that row's
  "Winrate global" cell color via `winrateTextClass`) — consistent
  with how the legend already describes "Very negative"/"Very
  positive" for this table.
- **Item 9 parses the existing `"wins-losses"` string client-side
  instead of requesting a backend change.** `_ratio()`
  (`stats.py` ~L106-107) always emits `f"{wins}-{losses}"`, so
  `"2-0".split('-')` reliably recovers both numbers without touching
  `barrins_api` — consistent with this bundle's frontend-only framing.
  (Draws are not possible in a BO3 game count, so a two-part split is
  safe; if that assumption is ever wrong, this needs revisiting.)
- **Item 10 reuses `ARCHETYPE_TEXT_CLASS`/`ARCHETYPE_BORDER_CLASS`
  from `lib/mtg-format.ts` as-is** — the same constants already used
  by `ArchetypeSummarySection`, not a new color set.

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
- The match-up summary table's non-name columns are visibly narrower
  than "Vs. deck", the winrate-band legend renders above the table
  instead of below, and the W/L OTP/OTD cells render in a muted grey
  (still not bold).
- A "Display" section in `AccountSettingsDialog.tsx` exposes four new
  `localStorage`-backed toggles: row background tint by winrate band
  (default **on**), "2W / 0L"-style result display (default **off**),
  colored archetype cell in the roster (default **off**), and a
  3-color tier background scale in the roster (default **off**).
- With the row-tint toggle on (default), match-up rows whose
  `winrate_global` falls in the "Very negative"/"Very positive" bands
  get a red/green-tinted background; all other rows are unaffected.
- With the result-format toggle on, `ratio_otp`/`ratio_otd` render as
  "2W / 0L" instead of "2-0"; off (default), the original "2-0" format
  is unchanged.
- With the archetype-color toggle on, the roster's archetype `Select`
  cell is colored per `ARCHETYPE_TEXT_CLASS`/`ARCHETYPE_BORDER_CLASS`,
  matching `ArchetypeSummarySection`'s existing colors.
- With the tier-color toggle on, the roster's Tier cell background
  reflects a 3-way grouping of the `TIERS` scale (exact grouping — see
  Open questions).
- Clicking the roster's delete (✕) button opens a `window.confirm`
  before `archiveDeck.mutateAsync` fires; cancelling leaves the deck
  untouched.

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

### 5. Match-up summary — narrower non-name columns

- [ ] Add width classes to the six non-"Vs. deck" headers in
      `MatchupSummarySection` (~L108-113), e.g. matching the `w-20`/
      `w-24`/`w-44` pattern already used elsewhere in this file
      (`MetaDecksSections.tsx` ~L94/96 uses the same Tailwind `w-*`
      convention on `TableHead`).
- [ ] Leave "Vs. deck" (~L107) unconstrained so it absorbs the freed
      space.
- [ ] Check the table's horizontal scroll behavior at narrow widths
      still works (`Table`'s wrapper already has `overflow-x-auto`,
      `components/ui/table.tsx` ~L6) — narrower columns shouldn't
      trigger unwanted wrapping inside a cell.

### 6. Match-up summary — legend above the table

- [ ] Move the `WINRATE_BANDS` legend block (~L165-172) to render
      before the `<Table>` (~L104), directly under `CardTitle`
      (~L103).
- [ ] No change to `WINRATE_BANDS` itself (~L23-29) or the per-cell
      `winrateTextClass` coloring — layout-only move.

### 7. Match-up summary — W/L OTP/OTD grey, not bold

- [ ] Add a muted-grey text class (e.g. `text-muted-foreground`,
      already used elsewhere in this file for empty states ~L87/147)
      to the two `ratio_otp`/`ratio_otd` cells (~L139-140), alongside
      the existing `font-mono`.
- [ ] Confirm no `font-bold`/`font-semibold` is introduced — the task
      is "stay non-bold, become grey," not a new weight.

### 8. Match-up summary — opt-out row tint by winrate band

- [ ] Add a `localStorage`-backed display preference (default **on** —
      opt-out) to `AccountSettingsDialog.tsx`'s new "Display" section.
- [ ] In `MatchupSummarySection`, when enabled, apply a red-tinted
      `TableRow` background when `row.winrate_global` is in the "Very
      negative" band (0-19%) and a green-tinted background when in the
      "Very positive" band (80-100%) — same thresholds as
      `WINRATE_BANDS`/`winrateTextClass` (~L23-29, ~L60-67), applied at
      the row level instead of the cell level.
- [ ] Confirm per-cell winrate text coloring (~L129-137) still reads
      clearly against the new row background in both light and dark
      mode — may need a lower-opacity tint rather than a solid fill.
- [ ] Rows with `winrate_global === null` (no data yet) get no tint,
      consistent with `winrateTextClass`'s existing null handling.

### 9. Match-up summary — opt-in "2W / 0L" result format

- [ ] Add a `localStorage`-backed display preference (default **off**
      — opt-in) to the same "Display" section.
- [ ] When enabled, render `ratio_otp`/`ratio_otd` (~L139-140) as
      "{wins}W / {losses}L" by splitting the existing `"wins-losses"`
      string on `-`, instead of the raw string.
- [ ] When disabled (default), behavior is unchanged — the string
      passes through as-is.
- [ ] No change to `_ratio()` (`stats.py` ~L106-107) or the
      `ratio_otp`/`ratio_otd` schema fields — parsing happens
      entirely in the frontend.

### 10. Deck roster — opt-in colored archetype cell

- [ ] Add a `localStorage`-backed display preference (default **off**
      — opt-in) to the "Display" section.
- [ ] When enabled, apply `ARCHETYPE_TEXT_CLASS[deck.category]` (and/or
      `ARCHETYPE_BORDER_CLASS`) to the archetype `SelectTrigger`/cell
      in `RosterRow` (~L237-256), matching how
      `ArchetypeSummarySection` (`StatsSections.tsx` ~L45-57) already
      colors archetype.
- [ ] When disabled (default), the cell stays as today — an uncolored
      `Select`.

### 11. Deck roster — opt-in 3-color tier background

- [ ] Add a `localStorage`-backed display preference (default **off**
      — opt-in) to the "Display" section.
- [ ] Define a new 3-way grouping over `TIERS` (~L36 — `[0, 0.5, 1,
      1.5, 2, 2.5, 3]`) and matching background classes — no existing
      constant to reuse (see Context item 11); exact grouping and
      colors are an open question, not a guessed default.
- [ ] When enabled, apply the resulting background class to the Tier
      cell in `RosterRow` (~L193-212).
- [ ] When disabled (default), the cell stays as today.

### 12. Deck roster — confirm before delete

- [ ] Wrap the delete button's action in `RosterRow` (~L274-276) with
      a `window.confirm(...)` prompt naming the deck (e.g.
      `` `Delete "${deck.name}"?` ``); only call `onDelete()` if
      confirmed.
- [ ] Matches the plain-`window.confirm` pattern already implied as
      acceptable by this task's own source request — no custom dialog
      component needed for this one.

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
4. **`localStorage` vs. account-level settings for items 8, 9, 10, 11
   (see Design decisions).** Default assumption: `localStorage`,
   keeping this bundle frontend-only and avoiding a migration for
   four cosmetic toggles. If these preferences should follow the user
   across devices/browsers the way `data_shared` does, that's a
   backend schema change and arguably its own item, not part of this
   bundle.
5. **Exact grouping and colors for the tier 3-color scale (item 11).**
   No existing convention to anchor to (unlike item 8, which reuses
   `WINRATE_BANDS`, or item 10, which reuses the archetype colors). A
   reasonable default — tiers 0/0.5/1 green, 1.5/2 amber, 2.5/3 red,
   loosely mirroring the winrate palette's "good/mid/bad" framing — is
   proposed but not confirmed; pick during implementation unless the
   user has a preference.
6. **Row-tint opacity/contrast for item 8.** A solid red/green fill
   could wash out the existing per-cell winrate text colors
   (`winrateTextClass`, ~L60-67) and any `shared`/`w/ shared` badges
   (~L122-125) sitting on top of it. Needs a low-opacity tint (e.g.
   `bg-destructive/10`, `bg-success/10`) confirmed readable in both
   light and dark mode before implementation, not guessed at review
   time.
7. **Confirmation copy for item 12.** `` `Delete "${deck.name}"?` `` is
   the working text; exact wording (e.g. whether to mention that
   shared/multi-share decks behave differently) is unconfirmed — pick
   reasonable copy during implementation unless the user has a
   preference.

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
- [ ] Open the match-up summary table → non-"Vs. deck" columns are
      visibly narrower, the winrate-band legend appears above the
      table, and W/L OTP/OTD render grey and non-bold.
- [ ] With the row-tint display setting on (default) → a row with a
      "Very negative" or "Very positive" global winrate shows a
      red/green-tinted background; other rows don't; toggling it off
      in Account settings removes all tints.
- [ ] Toggle the "2W / 0L" display setting on → W/L OTP/OTD cells show
      "XW / YL"; off (default) → cells show "X-Y" as before.
- [ ] Toggle the archetype-color display setting on → the roster's
      archetype cell is colored per archetype, matching the colors in
      "Breakdown by archetype"; off (default) → uncolored, as today.
- [ ] Toggle the tier-color display setting on → the roster's Tier
      cell background reflects the 3-color grouping; off (default) →
      no background, as today.
- [ ] Click delete (✕) on a roster deck → a confirm prompt appears;
      Cancel leaves the deck in place, Confirm removes it as before.

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
- Frontend: `MatchupSummarySection`/`StatsSections` tests still pass
  with the legend moved and width classes added — no assertion should
  depend on DOM order between legend and table unless it's updated
  deliberately.
- Frontend: new tests cover both states of each of the four display
  toggles (row tint, result format, archetype color, tier color) —
  default state and toggled state — since none of this existed before.
- Frontend: `MetaDecksSections`/roster tests updated for the
  `window.confirm` gate on delete — existing tests that call the
  delete handler directly likely need a mocked `window.confirm`
  returning `true` to keep passing, plus a new test for the
  cancel-leaves-deck-untouched path.

## See also

- `docs/content/front/tamiyo_scroll/roadmap.md` — the backlog page these
  four items were pulled from ("v2.0.0 candidates" section).
