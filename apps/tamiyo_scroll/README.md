# Tamiyo Scroll: Duel Commander Testing Tracker

Personal frontend to track my Magic metagame, my decklist and my BO3 matches in
tournament. React 19 + Vite + TypeScript, consumes the `barrins_api` BFFs (auth +
tamiyo-scroll tracker).

## Prerequisites

- Node.js 20+
- `barrins_api` running locally (defaults to `http://localhost:8000`)

## Setup

```bash
npm install
cp .env.example .env   # adjust VITE_API_BASE_URL if the backend runs elsewhere
```

## Using the app day to day

```bash
npm run dev        # Vite dev server, http://localhost:5173
```

Log in, then the 3 tabs are under `/app/*`:

- `/app/metagame` — roster, expected metagame, personal decklist import, archetype summary
- `/app/suivi-bo3` — new match, match log, tested cards
- `/app/decklist` — current decklist + version history

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
  api/          typed fetch + Zod validation, one file per resource (auth, matches, cardTests, metaDecks, ...)
  hooks/        React Query wrappers on top of src/api
  schemas/      Zod schemas (contract with barrins_api)
  pages/        one folder per tab (metagame/, suivi-bo3/, decklist/) + LoginPage, VerifyEmailPage
  components/ui shadcn-style primitives (Radix + cva + tailwind-merge)
  contexts/     ActiveDeckContext (active personal deck, shared across tabs)
```

## Notes

- Dark theme only (oklch tokens in `src/index.css`), no light mode.
- Computed values (winrates, conversion, decklist status) always come from the
  backend, never recalculated client-side — unless explicitly noted in a comment.
- API incidents/contracts currently being renegotiated with the backend: see
  `docs/incidents/`.
