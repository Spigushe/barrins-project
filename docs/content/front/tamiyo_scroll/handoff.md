# Handoff: Competitive MTG Tracker

## Overview

Competitive Magic: The Gathering tracking application — a player (or a
team) documents the expected metagame, logs BO3 test games, collects
feedback on cards under consideration, and versions their own decklist.
Simple multi-account support (login/password) with the option to share
data read-only with other accounts.

## About the design files

The file `Suivi Competitif MTG.dc.html` is a **design reference built in
HTML** — a prototype showing the intended look and behavior, **not
production code to copy as-is**. It runs on a small internal prototyping
framework (the "DC" components) with no equivalent in a real codebase.

**The task is to recreate this design in the target environment** (React,
Vue, real backend, etc.) using its existing patterns and libraries — or,
if no environment exists yet, choosing whichever framework best fits the
project.

In the prototype, all persistence goes through the browser's
`localStorage` (see the State section), and auth is a local mock with no
real backend. The app's text mentions a future "barrins_api" backend —
treat this as a product intention to discuss with the client, not an
existing integration to replicate.

## Fidelity

**High fidelity (hifi)**: colors, typography, spacing, and interactions
are final. The developer must recreate the UI pixel-perfect using the
target codebase's libraries/design system.

## Screens / Views

### 1. Login (Login / Signup)

**Purpose**: authenticate the user or create an account.
**Layout**: full screen, centered (`display:flex; align-items:center;
justify-content:center`), card at `max-width:400px`, background
`oklch(0.21 0.014 260)`, border `1px solid oklch(0.32 0.014 260)`,
`border-radius:16px`, padding `32px`.
**Components**:

- Title "Competitive MTG Tracker" — 20px / 800 / centered.
- Dynamic subtitle: "Log in to your tracker" or "Create an account" —
  13px, color `oklch(0.62 0.012 260)`.
- Username field (text) + password field (`type=password`) — background
  `oklch(0.24 0.014 260)`, border `oklch(0.32 0.014 260)`,
  `border-radius:8px`, padding `11px 12px`, `font-size:14px`.
- Conditional error message (e.g. "Email and password required.") —
  color `oklch(0.65 0.15 25)`, 12.5px.
- Full-width primary button — accent background `oklch(0.75 0.14 85)`,
  text `oklch(0.18 0.02 85)`, `border-radius:8px`, padding `12px`,
  `font-weight:700`. Label "Log in" / "Create account".
- Login/signup toggle link at the bottom, text + accent link.
- Discreet footer: "Account managed by barrins_api." — 11.5px,
  `oklch(0.5 0.012 260)`, separated by a top border.

### 2. Application shell (header, once logged in)

**Layout**: container `max-width:1400px`, auto margin, padding
`28px 32px 80px`.
**Header**: `display:flex; justify-content:space-between; flex-wrap:wrap`.

- Left: title "Competitive MTG Tracker" (22px/800) + subtitle "Metagame ·
  BO3 Tracking · My decklist" (13px, grey).
- Right (flex, gap 12px):
  - Badge "Viewing: {user} · read-only" if viewing another account's
    shared data.
  - Select "My account (…)" / "View: {other user}" to switch to another
    user's shared data.
  - Checkbox "Share my data".
  - "Log out" button (red/orange outline `oklch(0.65 0.15 55)`).
- Info banner under the header: accent-tinted background at 12% opacity,
  accent border at 35%, 12.5px text explaining that data goes through
  "barrins_api" and that a BFF extension is in progress to automate
  metagame import and Moxfield scraping.
- "My personal deck" block: active-deck select + "Syncing with
  barrins_api…" label during the simulated loading state + "New personal
  deck name" field and "Create" button aligned to the right
  (`margin-left:auto`).
- **Tabs**: "Metagame", "BO3 Tracking", "My decklist" — 2px accent-colored
  underline when active, background `oklch(0.24 0.014 260)` when active /
  transparent when inactive, `border-radius:8px 8px 0 0`.

### 3. Metagame tab

Stacked sections (`gap:28px`), each in a card
`oklch(0.21 0.014 260)` / border `oklch(0.32 0.014 260)` /
`border-radius:12px` / padding `20px`:

- **Personal decklist**: two blocks side by side (grid 1fr 1fr) —
  Moxfield import (URL + "Import (scrape API)" button) and raw text
  (textarea + "Save this version" button). Disabled/hidden if no
  personal deck is active.
- **Deck roster (MUR)**: editable table — columns Tier (select 0 to 3 by
  0.5), Deck (name), Archetype (select Aggro/Midrange/Control/Combo,
  colored by category), Decklist/notes (free text), delete (✕). Add row
  at the bottom with a "+" button.
- **Expected metagame**: table — Deck, Top 8 (number), Presence (number),
  Conversion (computed = Top8/Presence as %, in `JetBrains Mono`),
  Expected (select: As expected/More expected/Less expected), Tests
  (free-text status).
- **Breakdown by archetype**: auto-fit card grid (min 260px), one per
  archetype, border colored by category, average winrate shown at the
  top, list of the group's decks with their individual winrate.
- **Matchup summary**: table computed automatically from the match log —
  Vs. deck, Global winrate, OTP winrate, OTD winrate, OTP W/L ratio, OTD
  W/L ratio, number of games. Color-band legend (Very positive 80-100%,
  Positive 60-79%, Balanced 40-59%, Negative 20-39%, Very negative
  0-19%). "Average winrate" total row in the table footer.

### 4. BO3 Tracking tab

- **Tested cards — individual feedback**: add form (Nickname, Card name,
  Matchup, Rating (Poor→Excellent, colored 1-5 scale), Notes) + feedback
  table with inline editing ("Edit" button switches the row into form
  mode) and delete.
- **New game (BO3)**: form — My deck / Opponent (selects), On the
  Play/On the Draw, result per game (Win/Loss/Draw per game), 3
  textareas (Opening hand, Turning point, Final turn). "Save the game"
  button.
- **Match log**: list of cards (4px colored left border by result:
  Win/green, Loss/red, Draw/orange), showing personal deck vs opponent,
  result badge, OTP/OTD, per-game summary, date, Edit/Delete actions.
  Inline editing reuses the same form as "New game".

### 5. My decklist tab

- **Current decklist**: "VERSION N" banner + date + color legend (orange
  = in test, green = validated, red = rejected). List content shown in
  `JetBrains Mono`, one card per line, row color derived automatically
  from tested-card feedback (validated = rating ≥4 majority, rejected =
  rating ≤2 majority, otherwise "in test" if tested, neutral otherwise).
- **Version history**: list of versions (number, date, "Moxfield import"
  / "Manual entry" note) with delete.

## Interactions & Behavior

- Login/signup: simple validation (required fields, unique username on
  creation, matching password confirmation). Session persisted
  (`localStorage`), auto-reconnect on load.
- "View shared data" toggle: loads another account's data read-only, for
  an account that has sharing enabled; every editing control is
  disabled/hidden in this mode
  (`canEdit = isLoggedIn && !isReadOnly`).
- Moxfield import: simulated with a 700ms delay ("Importing…") then
  creates a new decklist version with placeholder content mentioning the
  provided link.
- Selecting a personal deck: triggers a simulated loading state
  ("Syncing with barrins_api…") for 550ms.
- Every table (roster, expected metagame, tested cards, match log) is
  editable row by row, with a dedicated add row at the bottom and delete
  via a ✕ icon.
- Match-log and tested-card rows have an inline edit mode (replaces the
  display row with a form, Save/Cancel buttons).
- Winrate calculations (by matchup, by archetype, overall average) are
  derived automatically from the match log and recomputed on every
  change — no manual winrate entry.
- No elaborate animation/transitions: state changes are instant, aside
  from the 2 simulated delays above.
- No dedicated responsive handling observed beyond `flex-wrap:wrap` on
  the header's control groups — tables use fixed-px-column grids, to be
  addressed for mobile if needed.

## State management

All state lives in the root component (the prototype's `state`):

- `view` ('login' | 'app'), `isSignup`, login form fields, `authError`.
- `currentUser`, `viewingUser` (account being viewed read-only),
  `sharedFlag` (sharing enabled).
- `activeTab` ('metagame' | 'suivi' | 'decklists').
- `decks[]` — opponent roster: `{id, name, tier, category, decklist,
  top8, presence, expected, tests}`.
- `matches[]` — BO3 log: `{id, date, myDeckId, deckId, otpOtd, g1, g2,
  g3, openingHand, turningPoint, finalTurn}`.
- `cardTests[]` — card feedback: `{id, tester, card, deckId, rating(1-5),
  notes}`.
- `myDecks[]` — personal decks: `{id, name}`. `activeMyDeckId` selects
  the current deck.
- `decklistVersions[]` — decklist versions per personal deck: `{id,
  deckId, version, content, notes, createdAt}`.
- Transient form state: `newDeck`, `newMatch`, `newCardTest`,
  `editDraft` (+ `editingMatchId`), `editCardTestDraft` (+
  `editingCardTestId`), `moxfieldUrl`, `rawDecklistText`.

**Persistence (prototype only)**: `localStorage` under the keys
`mtgSession` (current user), `mtgUsers` (registry of {password, shared}
per user), `mtgData_{username}` (full payload of
decks/matches/cardTests/decklistVersions/myDecks/activeMyDeckId). In the
real implementation, replace with a real backend/API and secure
authentication (passwords are stored here **in plain text** — do not
reproduce that).

**Derived calculations** (to be reimplemented client- or server-side):

- Conversion per deck = `top8 / presence` (%), shown as "—" if presence =
  0.
- Matchup summary = aggregation of games (`g1/g2/g3`) from matches
  filtered by opponent deck (and by the active personal deck if one is
  selected): global winrate, OTP winrate, OTD winrate, W/L ratios.
- Average winrate per archetype = average of the winrates of decks
  classified in that category (ignoring decks with no data).
- Decklist row color = find the longest matching card name in the row's
  text, look at the associated test feedback (validated if ≥4 majority
  rating, rejected if ≤2 majority rating, otherwise "in test").

## Design tokens

**Colors** (oklch format, neutral dark background):

- Page background: `oklch(0.16 0.012 260)`
- Card/section background: `oklch(0.21 0.014 260)`
- Input/select background: `oklch(0.24 0.014 260)` (or `0.2` for fields
  in inline-edit mode)
- Standard border: `oklch(0.32 0.014 260)`; dashed border ("new" fields):
  `oklch(0.4 0.014 260)`
- Primary text: `oklch(0.93 0.006 260)`; secondary text:
  `oklch(0.62 0.012 260)`; tertiary/disabled text:
  `oklch(0.5–0.55 0.012 260)`
- Accent (CTA, active, links): `oklch(0.75 0.14 85)` (amber) — text on
  accent: `oklch(0.18 0.02 85)`
- Error / delete: `oklch(0.6–0.65 0.15–0.18 25)` (red)
- Warning / read-only: `oklch(0.65 0.15 55)` (orange)
- Success / validated / win: `oklch(0.62 0.15 145)` (green)
- Archetype categories: Aggro `oklch(0.62 0.16 25)`, Midrange
  `oklch(0.65 0.14 140)`, Control `oklch(0.65 0.13 250)`, Combo
  `oklch(0.62 0.15 310)`
- Winrate bands: ≥80% `oklch(0.62 0.15 145)`, ≥60% `oklch(0.68 0.14
  105)`, ≥40% `oklch(0.75 0.1 85)`, ≥20% `oklch(0.65 0.15 55)`, <20%
  `oklch(0.6 0.18 25)`

**Typography**:

- Primary typeface: Inter (400/500/600/700/800), Google Fonts.
- Monospace typeface (numbers, decklist): JetBrains Mono (500/600).
- Sizes: section titles 16px/700; page title 22px/800; body 13–13.5px;
  uppercase labels 11.5px letter-spacing 0.04em; helper text 12–12.5px.

**Radius & spacing**:

- `border-radius`: 6px (inputs), 8px (buttons/small blocks), 10–12px
  (cards/blocks), 16px (login card).
- Section padding: 20px. Gap between sections: 20–28px. Gap between form
  fields: 8–16px.

**Shadows**: none — the design relies entirely on tinted
backgrounds/borders, no `box-shadow`.

## Assets

No images. No graphical icons (only the "✕" character used as text for
delete). Two Google Fonts (see above), loaded via `<link>` in the
prototype.
