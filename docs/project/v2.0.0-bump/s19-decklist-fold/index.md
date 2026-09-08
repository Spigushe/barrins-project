# S19. Fold the "Current decklist" section

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tamiyo_scroll` (React/Vite) only | No `barrins_api` change |
| **Initial date** | 2026-09-08 | Drafted 2026-09-08 |
| **Status** | 🔲 Phase 1 in progress — Phase 2 (default flip) deferred | / |
| **Source** | User request, 2026-09-08 (chat, not a GitHub issue) | / |
| **Dependency** | S4 (`CurrentDecklistSection` / `DecklistViewContent`, the thing being folded) | / |

---

## Context

On the Decklist tab, `pages/decklist/CurrentDecklistSection.tsx` always
renders the full type-grouped card tables of the deck's latest version
(`DecklistViewContent`). For a ~100-card Commander list that is a lot of
vertical scroll between the tab header and everything below it
(`VersionHistorySection`, the card-tests block, the import form). The
user wants to be able to fold that list away, and — as a **second
phase** — make folded the default state, so the list is hidden on
arrival and a reader deliberately unfolds it.

Purely local UI state: no business rule, no API, no schema, no backend
(Constitution §14.1). The server-computed row coloring in
`DecklistViewContent` is untouched — folding just stops rendering it.

## Decision

- **Persistence: `localStorage`, per browser.** Reuse `useLocalStorageFlag`
  + the `lib/displayPrefs.ts` key registry
  (`DISPLAY_PREF_CURRENT_DECKLIST_COLLAPSED = 'ts-current-decklist-collapsed'`),
  the same mechanism as S12's four "purely visual" display prefs —
  deliberately **not** synced to `TSUserSettings` (a migration for
  something that never needs cross-account visibility; same rationale as
  `s12-uiux-polish`).
- **Control lives in the section header**, not `AccountSettingsDialog`: a
  ghost chevron `Button` (inline `ChevronDownIcon` added to
  `components/icons.tsx`, no icon-library dependency), `aria-expanded` /
  `aria-controls` / `aria-label` wired. Mirrors the inline-dismiss pattern
  in `PersonalDeckSelector.tsx`, not the dialog-driven S12 toggles.
- **Fold scope: keep the header row.** Only the `DecklistViewContent`
  block (and its bordered wrapper, now `id="current-decklist-body"`)
  collapses. Title, `VERSION` badge + date, status legend, "Download
  report (PDF)", and the optional "Card change being considered" block
  all stay visible — the header is the anchor you unfold from.
- **One global flag, not per-deck.** Switching the active deck keeps the
  fold state; this pairs with the Phase 2 "folded by default" framing.
- **Two-phase rollout:**
  - **Phase 1 (this item):** add the control, default = **expanded**
    (`useLocalStorageFlag(KEY, false)`). No behaviour change for anyone
    who ignores the new button.
  - **Phase 2 (follow-up, separate commit):** flip the default to
    **collapsed** (`useLocalStorageFlag(KEY, true)`). Anyone who has
    already toggled keeps their stored choice; anyone who hasn't now
    gets a folded section on load. Also: check
    `src/demo/tourSteps.ts` / `DemoTour.tsx` for any guided-tour step
    that targets the decklist body and assumes it is visible on load.

## Consequences

- `apps/tamiyo_scroll` only. Files: `lib/displayPrefs.ts` (+1 key),
  `components/icons.tsx` (+`ChevronDownIcon`),
  `pages/decklist/CurrentDecklistSection.tsx` (state + header toggle +
  gate), `CurrentDecklistSection.test.tsx` (new `describe` block +
  `localStorage` cleanup), `CHANGELOG.md`.
- No new dependency. No `barrins_api`, schema, or API impact.
- Phase 2 is a one-argument change plus a test/changelog/demo-tour pass.
