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
`Combobox`, built from `Popover` + `Command` — already-mandated stack,
§14.2) — type to search existing decks or type a new name to create one,
in one control.

- Build on `usePersonalDecks`/`useCreatePersonalDeck` (unchanged) and
  `createPersonalDeck` (`src/api/personalDecks.ts`, already returns the
  created deck via `personalDeckSchema`, including `id` — currently
  unused by the caller).
- On create: capture the returned deck and immediately select it (via
  `updateSettings.mutateAsync({active_personal_deck_id})`), satisfying
  auto-select directly.
- Wrap the `TABS` nav block in a condition on `activeDeckId` (from
  `useActiveDeck()`) being non-null — hidden entirely, not just disabled,
  until a personal deck is selected.
- Because A2 disables the sharing UI for this release, the
  `canEdit`/viewing-mode branching that today complicates this block
  doesn't need to be handled in the new combobox for v1.0.0. Re-enabling
  sharing later will require re-adding a read-only/viewing-mode rendering
  path.
- Where the A3 "Import from Moxfield" field lives relative to this
  combobox is an implementation-time layout detail.

## Tasks

- [ ] Build the combobox component (select-existing / create-new).
- [ ] Wire create-new to auto-select the returned deck.
- [ ] Wrap the tabs block in an `activeDeckId != null` condition.
- [ ] Remove the old select + input + Create-button markup from
      `AppShell.tsx`.

## Done statement

Combobox replaces both old controls; creating a deck auto-selects it;
the three tabs are hidden until a personal deck is selected.

## UAT (manual)

- [ ] On `staging` with a fresh account (no personal decks yet), confirm
      the three tabs (Metagame, BO3 Tracking, My decklist) are not
      visible at all.
- [ ] Create a new deck via the combobox; confirm it's auto-selected and
      the three tabs appear immediately, with no manual reselect needed.
- [ ] Search for and select an existing deck via the combobox; confirm it
      switches the active deck correctly.

## Non-regression tests

- Automated: new component tests for the combobox (select-existing,
  create-new-and-auto-select, tab-visibility) — distinct from A2's
  `SharingControls` test.
- Manual: the Metagame/BO3 Tracking/My decklist pages still load correct
  data for whichever deck is selected — the selector rewrite doesn't
  change their content, only how a deck gets chosen.
