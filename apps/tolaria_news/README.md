# Tolaria News: Duel Commander tournament aggregator

Public, read-only React frontend over `barrins_api`'s Tolaria News BFF
(`/bff/tolaria-news/*`, see
`docs/content/back/barrins_api/bff/tolaria_news.md`) — browse scraped Duel
Commander tournament results, standings, brackets and decklists. No
accounts, no login: every route is public and requires no `Authorization`
header (T4, I7 Option 4).

React 19 + Vite + TypeScript, mirroring `apps/tamiyo_scroll`'s toolchain.

## Prerequisites

- Node.js 20+
- `barrins_api` running locally (defaults to `http://localhost:8000`)

## Setup

```bash
npm install
cp .env.example .env   # adjust VITE_API_BASE_URL if the backend runs elsewhere
```

## Using the app

```bash
npm run dev        # Vite dev server, http://localhost:5173
```

- `/` — tournament list (filters: source, date range — format is fixed to
  Duel Commander, this app's only scope)
- `/tournaments/:id` — tournament detail (Decks / Standings / Bracket tabs)
- `/decks/:id` — decklist detail (mainboard + derived commander(s))
- `/decklists` — global, cross-tournament decklist index (filters: pilot,
  source, commander, color identity, date range; cursor pagination). Color
  identity is exact-match (click pips to select/unselect, multi-select) —
  a deck's combined commander color identity must equal the selected set
  exactly, not "contains". No `commander:X color:UW` text search DSL —
  the dropdown/pip filters cover the same ground without one
- `/methodology` — stub page (placeholder copy, no data), linked from the
  landing page's secondary CTA

### Metagame / Archetypes / Trends (`VITE_FEATURE_KARN_TABLETS`)

`/metagame`, `/archetypes` and `/trends` are prepared ahead of their
backend (T4 iteration 2 / T6 "Karn Tablets", ADR-13 — not started as of
this writing) and stay entirely hidden — no nav links, routes redirect to
`/` — unless `VITE_FEATURE_KARN_TABLETS=true` is set. Their API layer
(`src/api/karnTablets.ts`, `src/schemas/karnTablets.ts`) targets
`/bff/tolaria-news/{metagame,archetypes,trends}`, which don't exist yet
and will 404 until that backend ships; the schemas are explicitly marked
provisional and need reconciling against the real response shape once it
lands. Flip the flag on once it does.

## CLI commands for writing code

```bash
npm run dev           # dev server with hot reload
npm run build         # typecheck (tsc -b) + prod build into dist/
npm run preview       # serves the prod build locally

npm run test          # Vitest suite (single run)
npm run test:watch    # Vitest in watch mode

npm run lint          # oxlint
npm run format        # prettier --write on the whole repo
npm run format:check  # checks formatting without writing
```

Before committing: `npm run format`, `npm run lint`, `npm run test`, `npm run build`.

## Quick structure

```text
src/
  api/          typed fetch + Zod validation, one file per resource (tournaments, decks, karnTablets)
  hooks/        React Query wrappers on top of src/api
  schemas/      Zod schemas (contract with barrins_api's Tolaria News BFF)
  pages/        one file per route
  components/
    ui/         shadcn-style primitives (Radix + cva + tailwind-merge)
    layout/     AppShell (Nav + BottomRail), FeatureGate (Karn Tablets flag)
    karnTablets/  shared bits for the flag-gated pages (WindowModeSelect)
  lib/          cn() helper, queryClient, featureFlags
```

## Design system

Visual language (Midnight palette, EB Garamond/Geist/JetBrains Mono type
stack, teal accent, icon/sigil, Eyebrow/StatBlock components) is adapted
from the design handoff at
`docs/project/v2.0.0-bump/t5-tolaria-news-frontend/handoff/design_handoff_tolaria_news/`
(`DESIGN_SYSTEM.md`, `PAGES.md`). Restyle only, by explicit decision — the
handoff's speculative `/bff/v1/*` contract and most of its larger page set
(landing hero, node-graph viz, forecasts, `⌘K` search, sign-in) are **not**
implemented here; this app stays wired to the real, shipped
`/bff/tolaria-news/*` contract only. `/decklists` was added later as its
own item (see the app's CHANGELOG) — a real global index with commander
and color-identity filters, but without the handoff's `commander:X
color:UW` text search bar (a dropdown + clickable pips instead).

## Notes

- Dark theme only (Midnight palette in `src/index.css`), no light mode.
- Every computed value (commander derivation, freshness, pagination)
  comes from the backend, never recalculated client-side (Constitution
  §4.1/§4.2).
