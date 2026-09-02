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

> **Status**: 🟨 All five Goblin Guide bootstrap `G-03` slices — `POST
/api/v1/auth/token`, an in-memory token store, silent refresh,
> self-registration with email verification (`/signup`, `/verify-email`),
> password reset (`/forgot-password`, `/reset-password`), account
> management at `/` (`AccountScreen` — display name, a two-step email
> change with a `/confirm-email-change` deep-link route, and account
> delete), and admin service-account management at `/service-accounts`
> (`ServiceAccountsScreen` — admin-gated list, create, revoke; a
> `?next=`-aware `RequireAuth` bounce for logged-out visitors, an
> in-app access panel for non-admins). Not yet mounted in `tamiyo_scroll`
> or `tolaria_news`; no deploy playbook.

## What it will never own

Business or authorization rules. Goblin Guide renders the flows Barrin's
Identity defines and stores authentication _state_ only — it never
decides permissions (constitution §4.1, §13.5).

## Configuration

| Variable                    | Default                 | Meaning                                   |
| --------------------------- | ----------------------- | ----------------------------------------- |
| `VITE_IDENTITY_SERVICE_URL` | `http://localhost:8001` | Base URL of the Barrin's Identity service |

See `.env.example`.

This shell runs in **cookie mode** (ADR-18): it calls Barrin's Identity
directly with `credentials: 'include'`, and the refresh token lives in an
`HttpOnly` cookie set by the service — never in JS. The identity
deployment it points at must set `REFRESH_COOKIE_ENABLED=true` and list
this app's origin in `ALLOWED_ORIGINS`.

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
