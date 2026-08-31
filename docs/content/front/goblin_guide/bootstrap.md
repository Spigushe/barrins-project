<!-- cSpell:ignore JWKS tolaria -->
# Goblin Guide — Bootstrap

> **Status**: 🟨 All five `G-03` slices built (T11–T15) —
> `libs/goblin_guide/` (`@barrins/goblin-guide`, the shared library) and
> `apps/goblin_guide/` (the standalone shell) exist on the release line
> with: login, in-memory token store, silent refresh, the `GET /auth/me`
> account view, self-registration + email verification (`SignupScreen` +
> `VerifyEmailScreen`, the `username` field, the resend cooldown, the
> `/verify-email?email=&code=` deep link), password reset
> (`ForgotPasswordScreen` + `ResetPasswordScreen`, the
> generic-confirmation copy, the `/reset-password?email=&code=` deep
> link), account management (`AccountScreen` — inline display-name
> edit, the two-step email change with a `/confirm-email-change` deep
> link, and a password-gated account delete; mounted at `/` in the shell
> in place of the read-only card), and admin service-account management
> (`ServiceAccountsScreen` — a `useCurrentUser()` gate: `admin` gets the
> list + create + revoke flows, everyone else an access panel; mounted
> at `/service-accounts` behind a `?next=`-aware `RequireAuth`). The
> password-rule checklist and the digit-masked code field are shared
> components. Not yet mounted in `tamiyo_scroll` or `tolaria_news`; no
> deploy playbook. Shape settled 2026-08-29
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
| `G-03` | Delivery order | **Resolved** (2026-08-29, T11) — login + silent refresh first, then signup + email verification, then password reset, then account settings and delete, then admin service-account management. `username` (platform.md `Q-03`) lands with signup. **All five slices built** (T11–T15) |
| `G-04` | Admin service-account management (Integration Contract §4.6) | **Resolved** (2026-08-29, ADR-17); **built (T15, 2026-08-30)** — `ServiceAccountsScreen` in the Goblin Guide library, `admin`-gated with an access panel for everyone else, mounted by the shell at `/service-accounts`. Create shows the `client_secret` once; the list keeps revoked accounts; `POST /service-token` is not surfaced (machine-to-machine only) |

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
- **`G-05` (settled — ADR-18):** refresh-token storage. Shipped as a
  pluggable `TokenStore` interface; the default (`createMemoryTokenStore`)
  keeps both tokens in memory, so a closed tab means re-login. For
  persistent sessions the library has a **cookie mode**: auth calls go to
  `VITE_IDENTITY_SERVICE_URL` directly (no BFF) with
  `credentials: 'include'` and an `X-Client: web` header, and
  `barrins_identity` itself holds the refresh token in an
  `HttpOnly; Secure; SameSite=None` cookie
  ([Integration Contract §4.1](../../back/barrins_identity/integration.md#41-human-login-and-session)).
  In cookie mode there is no refresh token in JS and no store for it. The
  `goblin_guide` shell ships in cookie mode; other host apps opt in once
  their origin is in identity's `ALLOWED_ORIGINS`.
- No JWKS handling in the browser. The frontend never verifies a token;
  it treats the access token as opaque and lets the backend (or the T9
  reverse-proxy gate,
  [§8.8](../../back/barrins_identity/integration.md#88-proxy-role-gate))
  do verification.
- On logout or account deletion, clear all in-memory token state — the
  server-side `token_version` bump already invalidates the tokens.

---

## 6. Tests-first note

Each slice ships with tests covering its critical paths (constitution
§19.3). The login slice (T11) covers: login success/failure with the
uniform `401`, the client-side empty-field guard, the in-flight lock,
the session-expired banner, single-flight silent refresh + its
dead-session fallback (store cleared), and `logout` clearing local
state even when the request fails. The signup slice (T12) covers:
`signup` with `verification_required` both ways (tokens stored only
when present), the `{ error: { message } }` envelope on a `409`, the
password-rule checklist and empty-field guard, `verifyEmail` success +
the `400` message, and `resend` starting the mirrored cooldown. The
password-reset slice (T13) covers: `requestPasswordReset` returning the
generic body and its `502`; `confirmPasswordReset` storing the fresh
pair, plus the single `400` message and the `429` attempt cap; the
forgot screen's empty-field guard, generic confirmation and "send
again"; the reset screen's deep-link prefill and six-digit submit
guard; and the shared `PasswordRules` checklist. The account-settings
slice (T14) covers: `updateAccount` mapping `displayName`/`email` to the
snake_case body and omitting absent fields (`display_name: null`
clears), plus the `409`/`502` errors; `verifyEmailChange` posting only
the code; `resendEmailChange` posting no body; `deleteAccount` clearing
the token store on `204` and surfacing a wrong-password `401` after the
silent-refresh retry; and `AccountScreen`'s inline display-name save,
the email-change walk (address → code step with the pending address in
the banner → back to idle on success), the mirrored 60s resend
cooldown, the deep-link code prefill, and the password-gated delete
(empty-field guard, `401` message, `onDeleted` fired with tokens
cleared). The admin service-account slice (T15) covers: `client.ts`
`listServiceAccounts` / `createServiceAccount` (description omitted when
absent) / `revokeServiceAccount` (`204`; the `404` and the non-admin
`403`); and `ServiceAccountsScreen`'s non-admin access panel (no list
fetch), the active/revoked badges with Revoke offered on active
accounts only, the empty state, the no-scope create guard, the
create → one-time-secret panel → back-to-list walk with the POST body,
and the revoke confirm (cancel and confirm paths, the `/revoke` POST).

---

## See also

- [Barrin's Identity — Integration Contract](../../back/barrins_identity/integration.md)
- [Barrin's Identity — Platform Architecture](../../back/barrins_identity/platform.md)
