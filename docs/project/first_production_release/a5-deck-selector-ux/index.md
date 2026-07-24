# A5. Tamiyo Scroll: deck-selector rewrite

[← Back to project index](../index.md)

## Context

Today, in `apps/tamiyo_scroll/src/components/layout/AppShell.tsx`
(lines ~149–193): "My personal deck" is a dropdown of existing decks,
"New personal deck name" is a separate text input + Create button, the
three tabs (`Metagame`, `BO3 Tracking`, `My decklist`) always render
regardless of deck selection, and creating a deck does **not**
auto-select it (the mutation's return value is discarded in
`handleCreateDeck`).

## Design

Replace both controls with a **single combined combobox** (shadcn
`Combobox`, built from `Popover` + `Command`) — type to search existing
decks or type a new name to create one, in one control.

**Dependency decision confirmed**: the standard shadcn Combobox needs
`@radix-ui/react-popover` + `cmdk`, neither previously installed. User
approved adding both over hand-rolling a custom dropdown (§22 dependency
policy) — small, well-maintained, matches how Select/Dialog/Checkbox are
already built in this project.

- New `src/components/ui/popover.tsx`, `src/components/ui/command.tsx` —
  thin Radix/cmdk wrappers, matching the existing `ui/` component style
  (function components, `cn()`, no forwardRef).
- New `src/components/layout/PersonalDeckSelector.tsx`: owns the search
  text, filters `usePersonalDecks()` results client-side
  (`Command shouldFilter={false}`, since cmdk's built-in fuzzy filter
  doesn't compose cleanly with a synthetic "Create" item), and offers a
  "Create "{search}"" item whenever the typed text doesn't exactly match
  an existing deck name. Selecting an existing deck or creating a new one
  both call `updateSettings.mutateAsync({active_personal_deck_id})`
  directly — creating immediately auto-selects, since it's the same code
  path.
- `AppShell.tsx`: the old select+input+button block replaced with
  `<PersonalDeckSelector />`; the `TABS` nav block wrapped in
  `activeDeckId !== null`, hidden entirely (not just disabled) until a
  personal deck is selected.
- Because A2 already disabled the sharing UI, `canEdit` in `AppShell` is
  a constant `true` — no viewing-mode branching needed in the new
  selector for this release.
- New jsdom test-setup gap found: `cmdk` needs `ResizeObserver`, which
  jsdom doesn't implement either (same category as A2's
  `hasPointerCapture`/`scrollIntoView` gap) — stubbed in
  `src/test/setup.ts`.

**Also discovered while wiring this up**: the "Import from Moxfield" UI
field was already fully built (`PersonalDecklistImportSection.tsx`,
`useImportMoxfield`) — A3's doc had incorrectly assumed it still needed
building and deferred it here. It already calls the same backend route
A3 upgraded, so it started returning real decklists automatically, no
frontend change required. Only cleanup done: renamed the stale
`importMoxfieldPlaceholder` function (in `api/personalDecks.ts`,
`hooks/useDecklistVersions.ts`) to `importMoxfield`, since it's no longer
a placeholder. **User confirmed the real import working end-to-end
locally.**

**Extra step added mid-flight**: match log — add a "View" button before
"Edit"/"Delete" in `MatchJournalSection.tsx`. Real gap found: matches
carry `opening_hand`/`turning_point`/`final_turn` notes that were only
ever visible while editing (never in the collapsed row, and editing
overwrites the read view rather than being read-only) — added a
read-only `Dialog` (reusing the existing `ui/dialog.tsx`, no new
dependency) showing those three fields. "View" is shown regardless of
`canEdit` (viewing is non-destructive); "Edit"/"Delete" stay gated.

**BO3 opponent-deck quick-create, built after all**: initially deferred
(see reasoning below), but the user asked to reconsider after seeing the
"New game (BO3)" form has no way to add an opponent deck at all. Found
that `MetaDecksSections.tsx`'s existing Roster "add deck" mini-form
already establishes the precedent of collecting only `name`/`tier`/
`category` and silently defaulting `top8: 0, presence: 0,
expected: 'as_expected'` for a brand-new deck — those defaults are
already-accepted practice in this codebase, not something new being
invented. Built `OpponentDeckField` in `MatchForm.tsx` (same
Popover+Command pattern as `PersonalDeckSelector`): search existing meta
decks, or type a name and "Create" it via a small `Dialog` collecting
exactly the same 3 fields as the Roster form (name pre-filled, tier,
category — **no `expected` field**, per explicit user request to match
the Roster form exactly), calling `useCreateMetaDeck()` then
auto-selecting the result. Used in both `NewMatchSection.tsx` and
`MatchJournalSection.tsx`'s inline edit (both go through the shared
`MatchFormFields`).

*(Original, since-superseded reasoning for deferring: `category` (an
enum: aggro/midrange/control/combo) and `expected` have no field-level
"unspecified" value, so silently defaulting them looked like the
frontend fabricating a real analytical claim — until the existing Roster
form's precedent showed this exact default is already how the project
handles brand-new meta decks.)*

**Also added**: `MetaDecksRosterSection`'s deck list now sorts by tier
ascending, then name ascending within a tier (previously unsorted/
creation-order) — a one-line `Array.sort`, requested alongside the
opponent-deck work.

## Tasks

- [x] Add `@radix-ui/react-popover` + `cmdk` dependencies.
- [x] Build `ui/popover.tsx` + `ui/command.tsx`.
- [x] Build `PersonalDeckSelector.tsx` (select-existing / create-new /
      auto-select).
- [x] Wrap the tabs block in an `activeDeckId != null` condition.
- [x] Remove the old select + input + Create-button markup from
      `AppShell.tsx`.
- [x] Rename `importMoxfieldPlaceholder` → `importMoxfield`.
- [x] Add a "View" button + read-only dialog to `MatchJournalSection.tsx`.
- [x] Build `OpponentDeckField` (search/create) in `MatchForm.tsx`, used
      by both `NewMatchSection.tsx` and `MatchJournalSection.tsx`.
- [x] Sort `MetaDecksRosterSection` by tier asc, then name asc.
- [x] Full frontend suite green: 54/54 tests, lint/format/build clean.
- [x] Fix: `AppShell.tsx` only hid the tab *nav links* behind
      `activeDeckId !== null` — the routed page content (`{children}`)
      always rendered regardless, so a fresh account landing directly on
      e.g. `/app/metagame` still saw full Metagame content with no
      personal deck selected. Found via UAT below. `{children}` is now
      gated the same way, with a "Create or select a personal deck
      above to get started." placeholder otherwise.
- [x] Fix: `NewMatchSection.tsx`'s "My Deck" field only synced to the
      active personal deck on mount (its `useEffect` only filled in an
      empty `personalDeckId`, never re-synced afterwards) — switching
      the active deck via the header combobox left "My Deck" stuck on
      whichever deck was active when the New Game form first mounted.
      Found via UAT below. The effect now always follows
      `activeDeckId`.
- [x] Fix: `GET /matches` and `GET /archetype-summary` had no
      `personal_deck_id` filter at all — the match log and "Breakdown
      by archetype" always showed every match across *all* of the
      owner's personal decks mixed together, unlike `/matchup-summary`
      which was already correctly scoped. Found via manual testing
      (switching personal decks left old matches/opponent stats
      visible). Both endpoints now accept an optional
      `personal_deck_id` query param, mirroring `/card-tests`'s
      existing pattern; `MatchJournalSection.tsx`/`StatsSections.tsx`
      now pass `activeDeckId`.
- [x] `PersonalDeckSelector.tsx`'s deck list now sorts alphabetically
      (`localeCompare`) instead of creation order — requested
      alongside the above, same spirit as the Roster's tier+name sort.

## Done statement

Combobox replaces both old controls; creating a deck auto-selects it;
the three tabs are hidden until a personal deck is selected; the match
log has a working "View" button; the BO3 form can create an opponent
deck without leaving the page; the Roster sorts predictably; Moxfield
import confirmed working end-to-end by the user locally.

## UAT (manual)

- [x] Moxfield import confirmed working end-to-end locally (user).
- [X] On `staging` with a fresh account (no personal decks yet), confirm
      the three tabs (Metagame, BO3 Tracking, My decklist) are not
      visible at all. *(Bug found on first attempt: nav links were
      hidden but the routed page content rendered anyway — see Tasks
      above. Fixed and confirmed on retest.)*
- [X] Create a new deck via the combobox; confirm it's auto-selected and
      the three tabs appear immediately, with no manual reselect needed.
- [X] Search for and select an existing deck via the combobox; confirm it
      switches the active deck correctly.
- [X] Click "View" on a match log entry; confirm the opening
      hand/turning point/final turn notes display correctly and the
      dialog is read-only (no accidental edit path).
- [X] On the "New game (BO3)" form, type a new opponent name, confirm
      "Create" appears, fill tier/category, submit; confirm the new deck
      is created, appears on the Metagame Roster page, and is
      auto-selected as the opponent for the game being logged.
- [X] On the Metagame Roster page, confirm decks are listed lowest-tier
      first, alphabetically within the same tier.

## Non-regression tests

- Automated: `PersonalDeckSelector.test.tsx` (8 tests: shows active deck,
  sorted-alphabetically, select-existing, create-and-auto-select, no
  duplicate-create-offer, archive-with-confirmation, cancel-archive,
  clears-active-deck-on-archive).
- Automated: `AppShell.test.tsx` (4 tests: tabs hidden/shown by
  `activeDeckId`, plus page-content hidden/shown by the same) —
  distinct from A2's `SharingControls.test.tsx`.
- Automated: `MatchJournalSection.test.tsx` (3 tests: notes hidden in
  collapsed row, dialog shows them, button order) — net-new file/feature.
- Automated: `NewMatchSection.test.tsx` (1 test, net-new: "My Deck"
  follows the header's active personal deck when it changes).
- Automated: `MatchFormFields.test.tsx` (2 tests: select-existing
  opponent, create-new-with-honest-defaults) — distinct from
  `PersonalDeckSelector`'s tests despite the similar UI pattern.
- Automated: `MetaDecksSections.test.tsx` (1 test: tier-then-name sort
  order) — net-new.
- Automated (backend): `test_matches.py::test_filters_by_personal_deck_id`,
  `test_stats_routes.py::TestArchetypeSummary::test_filters_by_personal_deck_id`
  (both net-new) — cf. `test_stats_routes.py::TestMatchupSummary`'s
  existing equivalent.
- Manual: the Metagame/BO3 Tracking/My decklist pages still load correct
  data for whichever deck is selected — the selector rewrite doesn't
  change their content, only how a deck gets chosen.
