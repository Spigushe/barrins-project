# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [Unreleased]

### Added

- `/decklists` — a global, cross-tournament decklist index (filters:
  pilot, source, date range; cursor pagination), backed by a new
  `GET /bff/tolaria-news/decks` BFF route. Each row links to its deck
  detail and its tournament. Restricted server-side to Duel Commander
  tournaments, same as the tournament list.
- `/decklists` gained a commander dropdown and a clickable, multi-select
  color-identity pip filter (exact match — a deck's combined commander
  color identity must equal the selected set exactly). Backed by
  `GET /bff/tolaria-news/decks/commanders` and new `commander`/`colors`
  filters on `GET /bff/tolaria-news/decks`, both plain SQL against
  already-canonicalized card names — no new indexed columns needed.
- `/methodology` — a real stub page (placeholder copy, no data), linked
  from a new secondary "Read the methodology" CTA on the landing page.
- Flag-gated Karn Tablets pages (`VITE_FEATURE_KARN_TABLETS`, still off)
  wired to the real `barrins_api` BFF routes and `src/schemas/
  karnTablets.ts` reconciled against the live response shape. All three
  pages default to the **banlist-period** window; every archetype name
  and every card name is hoverable for Scryfall art (reusing the shared
  `CardNameCell` / `CardFacesPreview`).
  - `/metagame` — the archetype table is now a horizontal bar chart
    (top 20, largest first), each row tagged with a rising / falling /
    stable / new chip from the backend's `momentum` field (share change
    vs the previous period, ±10%-relative band — classified server-side,
    not in the client). A prev/next period stepper (`WindowStepper`)
    steps through the windows of the current kind via `?at=`.
  - `/trends` — keeps the shared-axis line chart and adds a provisional
    second block: a per-archetype small-multiples sparkline grid, two
    rows of five, kept until one display method is chosen.
  - `/archetypes` — the detail table alone (representative-list size as
    distinct/total, plus the top "signature" cards from the backend's
    `is_signature` flag, which drops basic lands and metagame-wide
    staple lands). Same prev/next period stepper as `/metagame`, plus
    cursor pagination (Previous / Next, page size 20); pagination resets
    when the window (kind or period) changes.

### Notes

- `VITE_FEATURE_KARN_TABLETS` stays unset in every environment — the
  pages above are wired but not yet reachable. Flipping the flag is a
  separate call (pending T7 docs / T8 playbook).
- Trends "zoom into one period, split into 8 sub-points" was requested
  but deferred: `kt_*` holds per-run aggregates only, so it needs a
  pipeline or schema change first — tracked in the T6 doc.

## [2.0.0-alpha] - 2026-08-14

### Added

- Real React 19 + Vite + TypeScript app (T5), replacing the placeholder.
  Public, read-only, no auth — calls only `barrins_api`'s Tolaria News BFF
  (`/bff/tolaria-news/*`, T4): tournament list/detail (Decks/Standings/
  Bracket tabs) and decklist detail with derived commander(s).
- `/metagame`, `/archetypes`, `/trends` prepared ahead of their backend
  (T4 iteration 2 / T6 "Karn Tablets", not started), hidden behind
  `VITE_FEATURE_KARN_TABLETS` (default off).
- Visual design adapted from the design handoff (Midnight palette, EB
  Garamond/Geist/JetBrains Mono, teal accent, icon/sigil, Nav + BottomRail
  shell, Eyebrow component) — restyle only, not the handoff's larger
  speculative page set.
- Deployable through the existing `ops/my-server/tolaria_news.yml`
  playbook with no playbook changes.
- `DeckDetailPage` rebuilt around the backend's new grouped/sorted
  `mainboard` (S4): a Commander table (when the deck has one) plus one
  table per card-type section, each row showing qty, name, mana-cost
  pips, and an info popover with oracle text/keywords. Hovering a card
  name previews its front/back-face art via the backend's new Scryfall
  image proxy — shares the `card-faces-preview`/`mana-pips`/
  `mana-symbols`/`hover-card`/`popover` components with `tamiyo_scroll`'s
  own decklist redesign rather than each app building its own.

## [1.0.0] "WorldWake" - 2026-07-24

Nothing yet.
