# S7. Tutorial + demo interface (combined), no persistence

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tamiyo_scroll` only — no backend changes | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Fully decided, ready to start | / |
| **Source** | Request; `v2.0.0-bump/index.md` §1.8 | / |
| **Dependency** | None | / |

---

## Context

**Fully decided, nothing open**: one combined demo + tutorial
experience, pure frontend mock (no network calls at all — "no
persistence" holds structurally, not by a reset job), fixture data
authored in a single JSON file, guided-tour overlay built with the
existing Radix/shadcn primitives already in `src/components/ui/` (no
new dependency — this also settles the Playwright question raised
during planning: Playwright doesn't fit this item and isn't part of it).

## Done statement

- A new public route (e.g. `/demo`), reachable with no authentication,
  never issuing or requiring a token, never calling `barrins_api`.
- A parallel data-source module mirrors each `src/api/*.ts` file's
  function signatures, backed by `src/demo/fixtures.json` (static
  import), held in local component/context state reset fresh on every
  page load.
- A `DemoModeProvider` (or equivalent context) supplies this module in
  place of the real one; `MetagameTab`, `SuiviBo3Tab`, and
  `DecklistTab` render **unmodified** against whichever source is
  active.
- A guided-tour overlay (tooltips/step markers using existing
  `popover.tsx`/`dialog.tsx`/`card.tsx` primitives) walks through the
  seeded demo screens.
- Entry point: a link from `LoginPage` (near its existing "Account
  managed by `barrins_api`" footer line) and from `RootRedirect` in
  `App.tsx`.
- Anything a demo visitor adds, edits, or deletes during the session
  disappears on reload — verified, not just assumed from the
  architecture.

## Tasks

- [ ] Author `src/demo/fixtures.json`: sample personal decks, meta
      decks/roster, matches, and card-tests across all three tabs —
      invented for this purpose, never real user data.
- [ ] Build the parallel data-source module (one function per
      `src/api/*.ts` file's exported functions, same signatures).
- [ ] Build `DemoModeProvider` and wire it so `MetagameTab`/
      `SuiviBo3Tab`/`DecklistTab` consume it transparently in demo mode.
- [ ] Add the `/demo` route in `App.tsx`, fully public.
- [ ] Build the guided-tour overlay with existing primitives.
- [ ] Add entry-point links from `LoginPage` and `RootRedirect`.

## UAT (manual)

- [ ] Visit `/demo` with no account; confirm every tab renders
      pre-filled data with no login prompt.
- [ ] Add a match/edit a decklist/create a card-test in the demo;
      reload the page; confirm none of it persisted.
- [ ] Confirm the browser's network tab shows zero requests to
      `barrins_api` at any point while in `/demo`.
- [ ] Walk through the guided tour end-to-end; confirm every step
      points at real, visible content on screen (no step pointing at an
      element that isn't rendered).

## Non-regression tests

- New Vitest suite for the demo data-source module (same function
  signatures as the real `src/api/*.ts` modules, verified via a shared
  type/interface both implement).
- A test asserting `MetagameTab`/`SuiviBo3Tab`/`DecklistTab` render
  identically (same component tree) whether fed by the real API client
  or the demo module — the "reuse, don't fork" requirement.
