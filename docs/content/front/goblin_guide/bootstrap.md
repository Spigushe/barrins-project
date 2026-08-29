<!-- cSpell:ignore JWKS tolaria -->
# Goblin Guide — Bootstrap

> **Status**: ⬜ Planned — documentation only, nothing implemented.
> `apps/goblin_guide/` is a placeholder.
>
> **Backend counterpart**: [Barrin's Identity — Integration Contract](../../back/barrins_identity/integration.md).
> Every screen here maps to a section of that page; this doc is its
> client-side mirror.

---

## 1. Purpose

Goblin Guide is the planned frontend — the login and account-management
UI — for Barrin's Identity (`apps/barrins_identity/`), the RS256 JWT +
JWKS identity service described in
[Platform Architecture](../../back/barrins_identity/platform.md).

It exists as a distinct app because a shared Barrin's account
(constitution §13.1) needs one place to sign in, verify an email, reset a
password, and manage the account — usable by `tamiyo_scroll`,
`tolaria_news` and future apps alike, not re-implemented per app.

---

## 2. Backend counterpart

Goblin Guide renders flows that Barrin's Identity defines and stores
authentication **state** only. It never:

- decides permissions or roles (constitution §4.1, §13.5) — the backend
  returns `role`; the UI reflects it;
- validates a password rule it invented — the complexity rule is exposed
  in `GET /openapi.json` and enforced server-side;
- verifies a JWT — the browser holds tokens; verification is a backend /
  reverse-proxy concern (see §5).

Each flow below cites the
[Integration Contract](../../back/barrins_identity/integration.md)
section that owns its wire format.

---

## 3. Scope and open shape questions

Nothing about Goblin Guide's implementation is decided yet.

| # | Open question |
| --- | --- |
| `G-01` | Stack — the ecosystem default is React 19 + Vite + TypeScript + React Router + TanStack Query + Zod + Tailwind + shadcn/ui (constitution §14), unconfirmed for this app |
| `G-02` | Standalone application vs. an embeddable widget consumed by `tamiyo_scroll` / `tolaria_news` for their own login (the same unresolved question `tolaria_news`'s frontend plan records) |
| `G-03` | Which routes ship first — likely login + refresh + signup/verify, with password reset and account settings in a second pass |
| `G-04` | Whether admin service-account management (Integration Contract §4.6) lives in Goblin Guide or stays a `barrins_api`/CLI concern |

Do not implement against assumptions here — confirm scope first
(constitution §16.2).

---

## 4. Identity endpoint → Goblin Guide flow

| Goblin Guide screen / action | Identity endpoint(s) | Contract |
| --- | --- | --- |
| Login | `POST /api/v1/auth/token` | [§8.1](../../back/barrins_identity/integration.md#81-first-login) |
| Session kept alive | `POST /api/v1/auth/refresh` | [§8.2](../../back/barrins_identity/integration.md#82-silent-refresh) |
| Logout | `POST /api/v1/auth/logout` | [§4.1](../../back/barrins_identity/integration.md#41-human-login-and-session) |
| Create account + verify email | `POST /api/v1/auth/signup`, `/signup/verify`, `/signup/resend` | [§8.3](../../back/barrins_identity/integration.md#83-signup-and-verify) |
| Forgot / reset password | `POST /api/v1/auth/password-reset/request`, `/confirm` | [§8.4](../../back/barrins_identity/integration.md#84-forgot-password) |
| Account settings — display name / email | `PATCH /api/v1/users/me`, `/users/me/email-change/verify`, `/resend` | [§8.5](../../back/barrins_identity/integration.md#85-change-email) |
| Delete account | `DELETE /api/v1/users/me` | [§8.6](../../back/barrins_identity/integration.md#86-delete-account) |
| Per-app preferences (on behalf of another app) | `GET`/`PUT /api/v1/users/me/settings/{app_key}` | [§4.5](../../back/barrins_identity/integration.md#45-per-app-settings) |
| (admin) Service-account management | `POST`/`GET /api/v1/service-accounts`, `/revoke` | [§4.6](../../back/barrins_identity/integration.md#46-service-accounts) |

`GET /api/v1/auth/me` backs the "who am I" header/context on every
authenticated screen.

---

## 5. Token handling (client side)

- Hold the **access token in memory**; attach it as
  `Authorization: Bearer` to API calls.
- On a `401`, run the silent-refresh flow
  ([Integration Contract §8.2](../../back/barrins_identity/integration.md#82-silent-refresh))
  once, then retry; if `/refresh` also fails, drop to the login screen.
- Refresh-token storage (in-memory vs. an `HttpOnly` cookie set by a thin
  BFF) is part of `G-02` — a pure SPA has no good place for a 7-day
  secret, which is one argument for the widget/BFF shape.
- No JWKS handling in the browser. The frontend never verifies a token;
  it treats the access token as opaque and lets the backend (or the T9
  reverse-proxy gate,
  [§8.8](../../back/barrins_identity/integration.md#88-proxy-role-gate))
  do verification.
- On logout or account deletion, clear all in-memory token state — the
  server-side `token_version` bump already invalidates the tokens.

---

## 6. Tests-first note

When this app is built, tests come first (constitution §16.4) and cover
the critical paths (constitution §19.3): login success/failure, silent
refresh and its dead-session fallback, the signup + verification form
(including `verification_required=false`), the reset form, and the
error/loading states for each.

---

## See also

- [Barrin's Identity — Integration Contract](../../back/barrins_identity/integration.md)
- [Barrin's Identity — Platform Architecture](../../back/barrins_identity/platform.md)
