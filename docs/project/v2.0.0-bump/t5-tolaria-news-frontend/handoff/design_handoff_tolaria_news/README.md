# Handoff: tolaria_news (Barrin's Project — frontend)

## Overview

`tolaria_news` is the React frontend for **Barrin's Project**, a personal initiative analyzing competitive Magic: the Gathering tournament data with a focus on **Duel Commander**. The app collects, structures, analyzes and visualizes tournament data to extract trends, build archetypes, and suggest decklist refinements — surfacing all of this through a public-facing news/dashboard site.

The backend lives in a separate repo (`barrins_api`); `tolaria_news` consumes it through a **BFF** (backend-for-frontend) that shapes domain data into screen-shaped payloads. The full API contract is in `BFF.md`, with TypeScript types in `API_TYPES.ts`.

## About the Design Files

The files in `design_files/` are **design references created in HTML/JSX with React-via-Babel** — a prototype showing the intended look, motion, and information architecture. **They are not production code to copy directly.**

Your task is to recreate this design in a real React project using modern tooling and the codebase's eventual patterns. The prototype loads React/Babel from CDN and inlines styles for rapid iteration; the real app should use proper bundling (Vite recommended), CSS Modules or styled-components or Tailwind (your call), and a real routing solution.

## Fidelity

**High-fidelity** for the landing banner — pixel-perfect colors, typography, spacing, layout, and motion. Recreate it faithfully.

**Medium-fidelity / spec-only** for the five inner pages (Metagame, Archetypes, Decklists, Tournaments, Trends). The prototype only contains the landing banner; the inner pages are documented in `PAGES.md` with content requirements, layout intent, and data shapes — implement them using the design system established by the banner (see `DESIGN_SYSTEM.md`).

## Stack recommendation

- **Vite** + React 18 + TypeScript
- **React Router v6** for routing
- **TanStack Query** for data fetching/caching (config in `BFF.md` › *Caching*)
- **Fastify** or **Hono** (Node) or **FastAPI** (Python) for the BFF — see `BFF.md`
- **zod** or **typebox** for runtime validation of BFF responses against `API_TYPES.ts`
- **msw** for local development against fixtures when `barrins_api` is unavailable
- **CSS Modules** or **Tailwind** for styling — both work; the design tokens are simple enough that vanilla CSS is also fine
- **Recharts** or **visx** for any chart work on Metagame/Trends
- **D3-force** for the node-graph viz on the landing page (the prototype's `graph.jsx` does it by hand with raw SVG — that's also viable; use whichever you prefer)

## Routes

| Path | Component | Purpose |
|---|---|---|
| `/` | `LandingPage` | The full-bleed banner — hero, nav, abstract embedding viz. Recreate from `design_files/`. |
| `/metagame` | `MetagamePage` | Current Duel Commander metagame snapshot — share by archetype, deltas, top commanders. |
| `/archetypes` | `ArchetypesPage` | Browse and drill into archetypes (cluster summaries, representative decklists, winrate over time). |
| `/decklists` | `DecklistsPage` | Searchable index of indexed decklists with tournament context. |
| `/tournaments` | `TournamentsPage` | Recent and upcoming tournaments; per-tournament results pages. |
| `/trends` | `TrendsPage` | Time-series views — meta share over time, card-inclusion trends, emerging archetypes. |

See `PAGES.md` for the detailed brief on each route.

## Design references

- `design_files/index.html` — entry point; loads React, Babel, fonts, and the three JSX files
- `design_files/app.jsx` — main `<App>` with Nav, Hero, Stats, BackgroundField, BottomRail, and the Tweaks panel
- `design_files/graph.jsx` — `<NodeGraph>` abstract embedding visualization
- `design_files/tweaks-panel.jsx` — design-time tweaks panel (NOT shipped; reference only)
- `design_files/architecture.html` — **site map + mockups of all 5 inner routes** in one scrollable page
- `design_files/pages.jsx` — JSX source for the inner-page mockups (note: in `architecture.html` it's loaded as `pages-final.jsx` due to cache-bust gymnastics during design; rename to whatever you like)

## Screenshots

Reference thumbnails captured at ~924px viewport in `screenshots/`:

| File | What it shows |
|---|---|
| `00-landing-banner.png` | The full landing page (`/`) with hero, viz, and stats |
| `01-architecture-hero.png` | Cover + site map showing all routes and their relationships |
| `02-page-metagame.png` | `/metagame` — snapshot view, filter pills, hero stats |
| `03-page-archetypes.png` | `/archetypes` — search, filter rail, archetype cards |
| `04-page-decklists.png` | `/decklists` — search-as-DSL, filter chips, decklists table |
| `05-page-tournaments.png` | `/tournaments` — tabs, featured event card, event grid |
| `06-page-trends.png` | `/trends` — time-window controls, stacked-area chart |

The screenshots are reference only — open `design_files/architecture.html` in a browser to see all five pages at full design width with live interactivity.

To run the prototypes locally:
```bash
cd design_files/
npx serve .   # or any static server; the HTML files must be served, not opened via file://
# then open http://localhost:3000/index.html   for the landing banner
# and    http://localhost:3000/architecture.html for the five inner-page mockups
```

## Companion docs

- **`DESIGN_SYSTEM.md`** — all colors, type stack, spacing, radii, motion specs, components
- **`PAGES.md`** — per-route briefs: purpose, layout, components, data dependencies, states
- **`BFF.md`** — the API contract: envelope, errors, caching, auth, and every endpoint with request/response shapes
- **`API_TYPES.ts`** — TypeScript types for every BFF response; drop into `src/api/types.ts`
- **`ANIMATING_STARS.md`** — spec for the animated node-graph "stars" on the landing page: pulse rules, rotation, reduced-motion, perf budget

## What to do first

1. Read `DESIGN_SYSTEM.md` to internalize the visual language.
2. Recreate the landing banner (`/`) pixel-perfectly — get fonts loaded, palette dialed, the node-graph viz running. This validates the design system in code.
3. Build a shared layout (Nav + BottomRail + BackgroundField) that wraps the inner pages.
4. Stand up routing and stub the five inner pages.
5. Stand up the BFF per `BFF.md` — start with `/bff/v1/landing` and `/bff/v1/metagame`. Write fixtures first so the frontend is never blocked on `barrins_api`.
6. Build inner pages one at a time using `PAGES.md` as the brief and `API_TYPES.ts` as the data contract.
7. Take the *Open questions for `barrins_api`* list at the end of `BFF.md` to whoever owns the backend — several answers change the shape of v1.

## Things to drop from the prototype

- **Tweaks panel** (`tweaks-panel.jsx` and all `<TweaksPanel>` / `useTweaks` / `TWEAK_DEFAULTS` code in `app.jsx`) — design-time only.
- **CDN script tags** for React/Babel — use Vite imports.
- **Inline styles** — re-implement in your styling solution of choice.

## Things to keep

- Type stack: EB Garamond (serif) + Geist (sans) + JetBrains Mono (mono)
- Midnight palette (default) plus the Twilight / Parchment alternates as theme options if you want to ship light mode
- The node-graph visualization on the landing page
- The mono-typed "telemetry callout" pattern (used in the viz; reusable for stat overlays elsewhere)
- The italic-accent trick on display headings (last word of an `<h1>` set in italic + accent color)

## Handoff manifest

```
design_handoff_tolaria_news/
├── README.md            ← you are here
├── DESIGN_SYSTEM.md     colors, type, spacing, motion, components
├── PAGES.md             per-route briefs
├── BFF.md               API contract
├── API_TYPES.ts         TypeScript response types
├── ANIMATING_STARS.md   landing-page motion spec
├── design_files/        the live prototype (HTML/JSX, CDN React)
└── screenshots/         reference captures
```

## Notes

- The prototype's text is in **English**; the project description is in French. Decide early whether `tolaria_news` ships EN, FR, or both — affects copy, fonts (EB Garamond handles French diacritics fine), and any i18n setup.
- The current banner does **not** use any branded Magic: the Gathering visual elements (no mana symbols, card frames, or WotC iconography). Keep it that way unless you have licensing.
- The node-graph viz is decorative — it visualizes "the metagame as an embedding space" but the data is procedurally generated. If `barrins_api` exposes a real embedding endpoint, wire it up; otherwise keep it decorative.
