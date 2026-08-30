# Goblin Guide — standalone shell

The thin standalone app for **Goblin Guide**, the login and
account-management frontend for Barrin's Identity (`apps/barrins_identity/`).

It serves the canonical `goblin.barrins-codex.org` and gives the Karn
Tablets Jupyter reverse-proxy (T9) a login page to redirect to. All the
actual screens, hooks and token handling live in the shared library
`libs/goblin_guide/` (`@barrins/goblin-guide`), which `tamiyo_scroll`,
`tolaria_news` and future frontends mount too. This app is just a router,
a `QueryClientProvider`, an `IdentityProvider`, and the default ("Suivi")
token theme.

> **Status**: 🟨 Login, signup and password-reset slices (Goblin Guide
> bootstrap `G-03` steps 1–3) — `POST /api/v1/auth/token`, an in-memory
> token store, silent refresh, the `GET /auth/me` account view,
> self-registration with email verification (`/signup`, `/verify-email`),
> and password reset (`/forgot-password`, `/reset-password`). Account
> settings and admin service-account management come in later slices.

## What it will never own

Business or authorization rules. Goblin Guide renders the flows Barrin's
Identity defines and stores authentication _state_ only — it never
decides permissions (constitution §4.1, §13.5).

## Configuration

| Variable                    | Default                 | Meaning                                   |
| --------------------------- | ----------------------- | ----------------------------------------- |
| `VITE_IDENTITY_SERVICE_URL` | `http://localhost:8001` | Base URL of the Barrin's Identity service |

See `.env.example`.

## Scripts

```bash
npm run dev          # Vite dev server
npm run build        # tsc -b && vite build
npm run lint         # oxlint
npm run format:check # prettier
npm test             # vitest
```

`npm install` here resolves `@barrins/goblin-guide` from
`../../libs/goblin_guide` — build the library first
(`cd ../../libs/goblin_guide && npm install && npm run build`).
