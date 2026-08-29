<!-- cSpell:ignore JWKS tolaria -->
# Goblin Guide — Bootstrap

> **Status**: ⬜ Planned — documentation only, nothing implemented.
> `apps/goblin_guide/` is a placeholder. Shape settled 2026-08-29
> ([ADR-17](../../ops/architecture/decisions.md#adr-17-shared-code-lives-in-a-top-level-libs-directory)):
> a **shared frontend library** plus a thin standalone shell — see §3.
>
> **Backend counterpart**: [Barrin's Identity — Integration Contract](../../back/barrins_identity/integration.md).
> Every screen here maps to a section of that page; this doc is its
> client-side mirror.

---

## 1. Purpose

Goblin Guide is the login and account-management frontend for Barrin's
Identity (`apps/barrins_identity/`), the RS256 JWT + JWKS identity service
described in
[Platform Architecture](../../back/barrins_identity/platform.md).

A shared Barrin's account (constitution §13.1) needs one implementation of
"sign in, verify an email, reset a password, manage the account" —
usable by `tamiyo_scroll`, `tolaria_news` and future apps alike, not
re-implemented per app. So Goblin Guide ships as a **shared frontend
library** (screens + hooks + client-side token handling) that each
frontend mounts, plus a **thin standalone shell** that serves a canonical
`goblin.barrins-codex.org` and gives the T9 reverse-proxy a login page to
redirect to.

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

| # | Item | Status |
| --- | --- | --- |
| `G-01` | Stack | **Resolved** (2026-08-29, ADR-17) — the ecosystem default (React 19 + TypeScript + Tailwind + shadcn/ui, constitution §14), built in **Vite library mode**. React Router and TanStack Query are **peer dependencies** the host app provides — the library owns screens, hooks and token handling, not routing or the query client |
| `G-02` | Standalone app vs. per-app widget | **Resolved** (2026-08-29, ADR-17) — one shared library each frontend mounts, plus a thin standalone shell for `goblin.barrins-codex.org` and the T9 login page. Not a standalone-only app; not a copy-pasted widget |
| `G-03` | Delivery order | **Proposed** — login + silent refresh first, then signup + email verification, then password reset, then account settings and delete. `username` (platform.md `Q-03`) lands with signup |
| `G-04` | Admin service-account management (Integration Contract §4.6) | **Resolved** (2026-08-29, ADR-17) — part of the Goblin Guide library, `admin`-gated. It is identity account management and belongs with the rest, not split into a separate CLI-only surface |

The library boundary (§1) and the token-storage split (§5) are settled;
everything else about page layout / UX is open. Confirm specifics before
building (constitution §16.2).

---

## 4. Identity endpoint → Goblin Guide flow

| Goblin Guide screen / action | Identity endpoint(s) | Contract |
| --- | --- | --- |
| Login | `POST /api/v1/auth/token` | [§8.1](../../back/barrins_identity/integration.md#81-first-login) |
| Session kept alive | `POST /api/v1/auth/refresh` | [§8.2](../../back/barrins_identity/integration.md#82-silent-refresh) |
| Logout | `POST /api/v1/auth/logout` | [§4.1](../../back/barrins_identity/integration.md#41-human-login-and-session) |
| Create account + verify email | `POST /api/v1/auth/signup`, `/signup/verify`, `/signup/resend` — the signup form gains a `username` field (platform.md `Q-03`) | [§8.3](../../back/barrins_identity/integration.md#83-signup-and-verify) |
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
- **`G-05` (open):** refresh-token storage. Default — keep it in memory
  too, so a closed tab means re-login. A host app that wants persistent
  sessions wraps the library with its own BFF that holds the refresh
  token in an `HttpOnly` cookie; the library must support both without
  code changes (a pluggable token store).
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
