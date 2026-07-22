# Implementation Plan — Tamiyo Scroll Frontend Bootstrap

> **Target**: barrins-project/tamiyo_scroll
> **Initial date**: 2026-07-15
> **Status**: ✅ Implemented
> **Backend dependencies**: `barrins_api` — `/api/v1/auth/*` (login, signup, signup/verify,
> signup/resend, refresh, logout, me) and `/api/v1/tamiyo-scroll/*` (16 endpoints,
> see `barrins_api/docs/tamiyo_scroll_tracker/00_plan_general.md`). Both BFFs are
> implemented and tested on the backend side — this plan only covers frontend consumption.
> **Design source**: `Suivi Competitif MTG.dc.html` handoff from CLAUDE design
> (high fidelity, source of truth for FR labels, color/type tokens, calculation
> thresholds).

---

## Objective

By the end of this implementation, the application must:

1. Authenticate the user (login, signup, 2-step email verification) against the
   real JWT backend — no fake `localStorage`-style authentication, unlike the
   design prototype.
2. Reproduce the design's 3 tabs (Metagame, BO3 Tracking, My Decklist) pixel-perfectly
   for the current active personal deck's data.
3. Never compute client-side a value the backend already exposes pre-computed
   (conversion, win rate, decklist coloring) — consume the API response as-is
   (constitution §4.1/§4.2).
4. Allow read-only viewing of another user's shared data, with all editing
   controls disabled/hidden in that mode.
5. Handle session refresh (refresh token) transparently for the user, with a
   clean logout on failure.

### Non-goals (out of scope for this bootstrap)

- End-to-end tests (Playwright) — priority goes to unit/component tests
  (Vitest + Testing Library) for this first phase; E2E can follow separately.
- i18n (constitution §44) — a single hardcoded FR string set for now, structured
  so as not to block a future extraction (no string concatenation in
  JSX, labels centralized per screen).
- Deployment (Agent 3, out of scope — reverse proxy, TLS, static hosting).

---

## Options analysis

### A. Session management (tokens)

| Option | Mechanism | Advantages | Disadvantages |
| --- | --- | --- | --- |
| **A (chosen)** | `access_token`/`refresh_token` in `localStorage`, centralized HTTP interceptor | Simple, consistent with the backend's `OAuth2PasswordBearer` behavior (no httpOnly cookies on the API side); a single source of truth for auth | Vulnerable to XSS like any `localStorage` storage — accepted as consistent with the backend's existing JWT Bearer architecture (no CSRF to handle in exchange) |
| B | httpOnly cookies | More resistant to XSS | The backend doesn't expose this mode (`OAuth2PasswordBearer` + JSON body) — would change the auth contract shared across the whole Barrin's ecosystem, out of scope for this plan |

**Choice: A**. A centralized HTTP client (`src/api/client.ts`) intercepts 401s,
attempts a `POST /auth/refresh` once, replays the original request, and logs
the user out (purge + redirect to `/login`) if the refresh also fails.

### B. Tab routing

| Option | Mechanism | Advantages | Disadvantages |
| --- | --- | --- | --- |
| **A (chosen)** | Dedicated React Router routes (`/app/metagame`, `/app/suivi-bo3`, `/app/decklist`) | Shareable URL, working browser back button, consistent with `react-router` being present in the mandated stack | The prototype handled the active tab as plain React state — a minor, accepted deviation, UX improvement |
| B | Local React state (`activeTab`) without routing | Faithful to the prototype | `react-router`, mandated by the constitution, would then have no real usage in the app |

**Choice: A**.

### C. Email verification screen (no mockup provided)

Flagged in `docs/signup_email_verification/00_plan_general.md` (on the `barrins_api`
side): the high-fidelity design contains no code-entry field — only
Login/Signup. This plan must fill that gap while respecting the visual tokens of
the existing design rather than improvising a different style.

**Decision**: reuse the login card as-is (same `max-width:400px`,
`oklch(0.21 0.014 260)` background, border, `border-radius:16px`, `32px` padding)
with:

- title "Vérifiez votre email";
- 6-digit code field, pre-filled if `?email=&code=` are present in the URL
  (email link) **but never auto-submitted** — an explicit click on "Confirmer
  mon compte" is required (see `barrins_api` docs, Option D: don't let a
  corporate link scanner consume the code before the user does);
- "Renvoyer le code" button with a 60s delay (disabled + countdown, aligned with
  `verification_resend_cooldown_seconds` implicitly returned by the backend's
  generic 202 behavior — the frontend keeps its own local countdown, the backend
  doesn't return the remaining time);
- link back to `/login`.

### D. Test framework

| Option | Mechanism | Advantages | Disadvantages |
| --- | --- | --- | --- |
| **A (chosen)** | Vitest + React Testing Library | Native Vite integration (no separate Babel config), API already familiar and close to Jest | — |
| B | Jest | Historical React standard | Extra configuration under Vite (ESM transform), no advantage here |

**Choice: A**.

---

## Stack and tooling

Mandated by the constitution (§14.2) — no alternative considered:

- React 19, TypeScript (strict mode), Vite
- React Router (v7)
- TanStack Query (v5)
- Zod
- TailwindCSS
- shadcn/ui

Additional dependencies not explicitly listed (none is a subjective choice — all
required to make the mandated stack work):

| Dependency | Role |
| --- | --- |
| `axios` **(to validate — see Open points)** | HTTP client with interceptors (token refresh) |
| `vitest`, `@testing-library/react`, `@testing-library/user-event` | Tests |
| `eslint`, `@typescript-eslint/*`, `prettier` | Code quality |

---

## Target architecture

```text
src/
├── api/
│   ├── client.ts              ← fetch/axios wrapper, refresh token interceptor
│   ├── auth.ts                ← login, signup, verifyEmail, resendCode, me, logout
│   ├── settings.ts            ← getMySettings, updateMySettings, listSharedUsers
│   ├── personalDecks.ts       ← personal deck CRUD + versions + decklist-view
│   ├── metaDecks.ts           ← roster CRUD
│   ├── matches.ts             ← BO3 log CRUD
│   ├── cardTests.ts           ← card test feedback CRUD
│   └── stats.ts               ← archetype-summary, matchup-summary
│
├── schemas/                   ← Zod schemas mirroring backend Pydantic schemas
│   ├── auth.ts
│   └── tamiyoScroll.ts
│
├── hooks/                     ← TanStack Query hooks (useQuery/useMutation per
│   │                            resource)
│   ├── useAuth.ts              (session state, login/logout, refresh)
│   ├── usePersonalDecks.ts
│   ├── useMetaDecks.ts
│   ├── useMatches.ts
│   ├── useCardTests.ts
│   └── useStats.ts
│
├── components/
│   ├── ui/                    ← generated shadcn/ui primitives (Button, Input,
│   │                            Table, …)
│   ├── layout/
│   │   ├── AppShell.tsx        (header, personal deck selector, sharing, tabs)
│   │   └── ProtectedRoute.tsx
│   └── shared/
│       └── EditableTable.tsx   (common pattern for roster/metagame/matches/card-tests)
│
├── pages/
│   ├── LoginPage.tsx
│   ├── VerifyEmailPage.tsx
│   ├── MetagameTab.tsx
│   ├── SuiviBo3Tab.tsx
│   └── DecklistTab.tsx
│
├── lib/
│   └── queryClient.ts
│
├── App.tsx                    ← routes
└── main.tsx
```

---

## Frontend route map

| Route | Page | Protection |
| --- | --- | --- |
| `/login` | `LoginPage` (login/signup toggle) | Public |
| `/verify-email` | `VerifyEmailPage` | Public |
| `/app/metagame` | `MetagameTab` | Authenticated |
| `/app/suivi-bo3` | `SuiviBo3Tab` | Authenticated |
| `/app/decklist` | `DecklistTab` | Authenticated |
| `/` | Redirect → `/app/metagame` if authenticated, else `/login` | — |

`ProtectedRoute` redirects to `/login` if there's no valid `access_token`.

---

## Backend endpoint → frontend hook mapping

| Backend endpoint | Hook | Screen |
| --- | --- | --- |
| `POST /auth/token`, `/auth/signup`, `/auth/signup/verify`, `/auth/signup/resend`, `/auth/refresh`, `/auth/logout`, `GET /auth/me` | `useAuth` | Login, VerifyEmail, header |
| `GET/PATCH /tamiyo-scroll/me/settings`, `GET /tamiyo-scroll/shared-users` | `useSettings` | Header (sharing, "Viewing: …" selector) |
| `GET/POST/DELETE /tamiyo-scroll/personal-decks`, `.../versions*`, `.../decklist-view` | `usePersonalDecks` | Header (deck selector), Metagame (import), My Decklist |
| `GET/POST/PUT/DELETE /tamiyo-scroll/meta-decks` | `useMetaDecks` | Metagame (roster + expected-field table) |
| `GET/POST/PUT/DELETE /tamiyo-scroll/matches` | `useMatches` | BO3 Tracking |
| `GET/POST/PUT/DELETE /tamiyo-scroll/card-tests` | `useCardTests` | BO3 Tracking |
| `GET /tamiyo-scroll/archetype-summary`, `/matchup-summary` | `useStats` | Metagame (archetype breakdown, matchup summary) |

The `owner_id` parameter (shared read-only mode) is carried by a single
global state ("Viewing: {user}" selection in the header) and automatically
injected by `api/client.ts` on `GET` requests only — never on mutations,
an exact mirror of the server-side guarantee (`resolve_owner` only exists on GET
routes). `canEdit = !viewingSharedUser` derives from that same state, centralized
in `useAuth`/a dedicated context — no prop-drilling of a boolean recomputed on
every screen.

---

## Phase breakdown

| Phase | Title | Main files | Prerequisites |
| --- | --- | --- | --- |
| 1 | Scaffold (Vite, Tailwind, shadcn, ESLint, strict tsconfig) | project root | — |
| 2 | API client + refresh interceptor + Zod schemas | `src/api/`, `src/schemas/` | Phase 1 |
| 3 | Auth: login/signup/verify-email + `useAuth` + `ProtectedRoute` | `src/pages/Login*.tsx`, `VerifyEmailPage.tsx`, `useAuth.ts` | Phase 2 |
| 4 | App shell (header, deck selector, sharing, tabs) | `AppShell.tsx` | Phase 3 |
| 5 | `EditableTable` (shared component) | `components/shared/EditableTable.tsx` | Phase 1 |
| 6 | Metagame tab | `MetagameTab.tsx`, associated hooks | Phases 4, 5 |
| 7 | BO3 Tracking tab | `SuiviBo3Tab.tsx` | Phases 4, 5 |
| 8 | My Decklist tab | `DecklistTab.tsx` | Phase 4 |
| 9 | Tests (Vitest + Testing Library) | `**/*.test.tsx` | All |

---

## Decisions settled during scoping

### 1. Native `fetch`, not `axios`

The HTTP client needs an interceptor for transparent token refresh (401 →
refresh → replay the original request). Native `fetch` is enough for this need (a
roughly thirty-line wrapper) — no extra dependency to justify, consistent
with the dependency-minimization policy (constitution §22.3) and with the
equivalent choice on the backend side (stdlib `smtplib` rather than an email SDK).

### 2. Hand-written shadcn/ui primitives, not via the CLI

Verified during scoping: `ui.shadcn.com` (the registry used by `npx shadcn add`)
is not reachable from this execution environment (403 on the network proxy side),
whereas `registry.npmjs.org` is. The required primitives (Button, Input, Select,
Table, Tabs, Card, Badge, Checkbox, Textarea, Dialog) will therefore be written
directly in `src/components/ui/` following the same foundations the CLI generates
(Radix UI primitives + `class-variance-authority` + `tailwind-merge`) — this is
not a deviation from the stack choice: shadcn/ui was never a runtime dependency
but a code pattern to copy into the repo, which is what the CLI does and what
I'll do by hand.

### 3. Backend address in development

`VITE_API_BASE_URL=http://localhost:8000` by default in `.env.example`, to adjust
depending on the environment where `barrins_api` actually runs.

---

## Implementation notes

- **Phase 5**: the generic `EditableTable` component planned originally was abandoned
  along the way — the design actually contains two incompatible editing patterns
  (roster/metagame expected-field table: rows always editable inline;
  matches/tested cards: read-only rows with an explicit "Edit" toggle). Forcing
  them into a single generic component would have required a per-column
  renderer/editor config as elaborate as a mini data-grid. Each tab composes its
  own editing behavior on top of the shared `Table` primitives.
- **Renamed pages**: `MetagameTab.tsx` / `SuiviBo3Tab.tsx` / `DecklistTab.tsx` (rather
  than `*Page.tsx`, an initial deviation corrected to match this plan).
- **Bug fixed during manual smoke test** (Phase 6): `SelectTrigger` wasn't
  truncating long values (e.g. "Mon compte (email@très-long-domaine)"), which
  made the selector overflow and overlap neighboring header controls instead
  of ellipsizing — `overflow-hidden` + `truncate` added to `SelectTrigger`/`SelectItem`.
- **Bug fixed during manual smoke test** (Phase 7): the "My deck" selector in the
  "New match" form wasn't pre-filling with the header's active deck —
  the initial `useState` value captured `activeDeckId` before the `/me/settings`
  request resolved. Fixed with a `useEffect` that syncs the draft
  once `activeDeckId` is available, without overwriting a selection already made
  by the user.
- **End-to-end validation**: each phase 6-9 was manually verified against the real
  backend (`barrins_api` + PostgreSQL, no mocks) via disposable Playwright scripts
  in the scratchpad — signup, email verification, creation of a personal deck/opposing
  decks/matches/card test feedback, and confirmation that the stats (archetype,
  matchups, decklist coloring) recompute correctly server-side and flow through
  correctly to the 3 tabs without ever duplicating that computation client-side.
- **Automated tests** (Phase 9): Vitest coverage focused on the pure logic most
  at risk of silent regression — draft ↔ `MatchWrite` mapping (in particular
  the "not played" sentinel ↔ `null`), win rate/rating color thresholds, `ActiveDeckContext`
  context guard — plus the 8 already-existing API client tests. No Playwright
  E2E suite committed (out of scope for the plan); real-world usage was manually
  verified as described above.

### Post-delivery fixes and reorganization (2026-07-16)

Feedback from the client after real-world app usage, all fixed/adjusted on the frontend
side (except for the two backend bugs, see `barrins_api/docs/tamiyo_scroll_tracker/00_plan_general.md`,
"Post-delivery fixes" section):

- **`Decklist personnelle` and `Cartes testées` moved to the My Decklist tab**,
  in that order (import first), at the top of the tab before `Decklist courante`
  and `Historique des versions`. Removed from the Metagame and BO3 Tracking tabs
  respectively.
- **Tested cards scoped to the active deck**: `useCardTests` now takes
  `personalDeckId` and passes `personal_deck_id` as a query filter and in the write
  payload (mirroring the backend fix above); shows a deck-selection prompt
  when no deck is active, like `PersonalDecklistImportSection`.
- **Match log**: "my deck"'s name is no longer bold/white (repeated on
  every row, redundant with the header selector) — switched to non-bold `text-muted-foreground`;
  the opponent's deck name stays bold/white (`text-foreground`), since it's
  the most useful piece of information to spot at a glance in the log.
- **Regression check passed**: manual Playwright suite against the real backend
  (disposable account, decks/matches/card-tests created via the API, visual and
  DOM verification) — archived deck disappears from the archetype breakdown without
  reappearing after a reload, tested card visible only from the deck it was
  created in, blocks in the right order on the 2 affected tabs.
