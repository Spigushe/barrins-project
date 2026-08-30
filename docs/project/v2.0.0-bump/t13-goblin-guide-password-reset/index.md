# T13. Goblin Guide — password reset

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `libs/goblin_guide/`, `apps/goblin_guide/`, `docs/content/front/goblin_guide/bootstrap.md`, `docs/content/ops/architecture/decisions.md` (ADR-17) | / |
| **Initial date** | 2026-08-30 | / |
| **Status** | 🟨 **Password-reset slice done (2026-08-30)** — `G-03` step 3 on `proj/v2.0.0-bump`. Library `npm run build` + 57 tests green; shell `npm run build` + 9 tests green; `oxlint` + `prettier --check` clean on both. Account settings + delete, and admin service-account management (remaining `G-03` slices), host mounting, and the deploy playbook remain **out of scope** (each a later slice or phase). | / |
| **Source** | [Goblin Guide — Bootstrap](../../../content/front/goblin_guide/bootstrap.md) `G-03`, [Barrin's Identity — Integration Contract](../../../content/back/barrins_identity/integration.md) §4.3 / §8.4 | / |
| **Dependency** | **T12** (the signup slice this builds on — shared `PasswordRules` / `CodeField` are extracted from its `SignupScreen` / `VerifyEmailScreen`). | / |

---

## Context

T12 landed `G-03` step 2 (signup + email verification). The locked
`G-03` order (bootstrap.md §3) puts **password reset** next. The backend
is already on the release line and tested
(`apps/barrins_identity/app/api/v1/auth.py`): `POST
/api/v1/auth/password-reset/request`, `/password-reset/confirm` — wire
contract frozen in
[integration.md §4.3 / §8.4](../../../content/back/barrins_identity/integration.md#43-password-reset).
This slice is frontend only; no backend change.

**Decisions (user, 2026-08-30):**

- **Tracking** — its own work item (T13), one logical commit.
- **Design first** — mockups approved via a design canvas ("Goblin Guide
  Password Reset") before code: forgot-password, the generic
  confirmation, the reset form, and the bad-code state, all on the
  existing `gg-` token CSS. No new tokens.
- **Shared-component extraction** — the password-rule checklist and the
  digit-masked 6-code field are used a third time here, so they are
  pulled into shared components (`PasswordRules`, `CodeField`) and
  `SignupScreen` / `VerifyEmailScreen` are refactored onto them rather
  than keeping a third copy.
- **Deep link** — confirmed against `apps/barrins_identity`
  (`_build_reset_link`): the reset email links to
  `{FRONTEND_BASE_URL}/reset-password?email=<enc>&code=<6 digits>`,
  exactly the same shape as `/verify-email`.

## Design

- **`libs/goblin_guide/`**
  - `schemas.ts` — `passwordResetRequestResponseSchema` (`{ detail }`).
    `/password-reset/confirm` returns the existing `tokenPairSchema`.
  - `client.ts` — `IdentityClient` gains `requestPasswordReset(email)`
    (JSON; `502` → `IdentityError`; otherwise the generic body) and
    `confirmPasswordReset(email, code, newPassword)` (JSON
    `{ email, code, new_password }`; stores the returned pair).
  - `hooks.ts` — `usePasswordResetRequest` and `usePasswordResetConfirm`
    (the latter invalidates `me`, like `useVerifyEmail`).
  - `ForgotPasswordScreen` — one email field. Submit →
    `requestPasswordReset`; on success the screen swaps to the generic
    confirmation (`response.detail`, shown verbatim — it never confirms
    whether an account exists, integration.md §5) with an "Enter reset
    code" button (`onEnterCode(email)`) and a "Send again" link that
    re-requests. Empty-field guard, in-flight lock, server error in
    `role="alert"`.
  - `ResetPasswordScreen` — email + `CodeField` (both pre-fillable from
    the deep link) + new password with the `PasswordRules` checklist.
    Submit guard on a non-empty email, `^\d{6}$` code and a non-empty
    password; `400` / `429` / `422` surface in `role="alert"`. On
    success → `onAuthenticated` (the fresh pair is already stored; every
    other session for the account is revoked server-side).
  - `PasswordRules` (`passwordPolicy.ts` holds `PASSWORD_RULES`) and
    `CodeField` (`codeMask.ts` holds `onlyDigits`) — new shared
    components; `SignupScreen` / `VerifyEmailScreen` now consume them.
    Helper constants live in sibling `.ts` files so the `.tsx`
    components export only components (`react/only-export-components`).
  - `icons.tsx` — `KeyIcon` for the reset banners.
  - `index.ts` exports the two screens + props, the two hooks +
    `PasswordResetConfirmVariables`, and `PasswordResetRequestResponse`.
- **`apps/goblin_guide/`** — `ForgotPasswordRoute` (`/forgot-password`,
  redirects out when authenticated; `onEnterCode` → `/reset-password?email=…`)
  and `ResetPasswordRoute` (`/reset-password`, reads `?email=` /
  `?code=`). Both routes wired into `App.tsx` before the catch-all;
  `LoginRoute` now passes `onForgotPassword` → `/forgot-password`.
- **CI** — no workflow change: the `goblin_guide` job and its
  `apps/goblin_guide/** + libs/goblin_guide/**` paths filter (T11)
  already cover this slice.

## Done statement

- `libs/goblin_guide/` — `npm run build` green (ES bundle + CSS +
  `dist/*.d.ts`), 57 vitest tests (`tokenStore` 3, `client` 23,
  `LoginScreen` 6, `SignupScreen` 7, `VerifyEmailScreen` 5,
  `ForgotPasswordScreen` 5, `ResetPasswordScreen` 5, `PasswordRules` 3),
  `oxlint` + `prettier --check` clean. `CHANGELOG.md` + `README.md`
  updated.
- `apps/goblin_guide/` — `npm run build` green, 9 vitest tests (`App`:
  the 6 login/signup-slice cases plus forgot link → forgot screen,
  request → reset screen with the email carried, deep-link prefilled →
  reset → shell), `oxlint` + `prettier --check` clean.
- Docs: `bootstrap.md` status banner + `G-03` row + §6 updated; ADR-17
  gains a T13 consequence bullet; this tracker; project index T13 row
  and the T12 "Not done" list trimmed; `apps/goblin_guide/README.md`;
  `docs/CHANGELOG.md`.
- One logical commit (constitution §18.3). **Not touched:**
  `apps/tamiyo_scroll/**`, `apps/tolaria_news/**`,
  `apps/barrins_identity/**`, `ops/**`, `.github/**`.

## UAT (manual)

- [x] `cd libs/goblin_guide && npm run build` — `tsc` clean, Vite emits
      `dist/goblin-guide.js` + `.css` + `dist/*.d.ts` (new
      `ForgotPasswordScreen` / `ResetPasswordScreen` declarations
      included).
- [x] `cd libs/goblin_guide && npm test` — 57 passed.
- [x] `cd apps/goblin_guide && npm run build` + `npm test` — 9 passed.
- [x] `npm run lint` + `npx prettier --check .` — clean in both
      packages.
- [ ] Run the shell against a live `barrins_identity` (`npm run dev`,
      the emailed `/reset-password?email=&code=` deep link, and the
      per-address resend cooldown) — deferred to the cutover/playbook
      phase; no live service is running yet, and the identity service's
      `FRONTEND_BASE_URL` must point at the shell origin for the deep
      link to resolve here.

## Non-regression tests

- `libs/goblin_guide/src/auth/client.test.ts` — `requestPasswordReset`:
  `202` returns the generic `detail`; `502` throws.
  `confirmPasswordReset`: success stores the fresh pair; `400` surfaces
  the single message and stores nothing; `429` throws.
- `libs/goblin_guide/src/components/ForgotPasswordScreen.test.tsx` —
  empty submit blocked with no request; a request swaps to the generic
  confirmation and offers "Enter reset code"; `onEnterCode` fires with
  the email; a server error shows in `role="alert"`; "Send again"
  re-hits the endpoint.
- `libs/goblin_guide/src/components/ResetPasswordScreen.test.tsx` —
  prefill from `initialEmail` / `initialCode` (non-digits stripped);
  sub-6-digit submit blocked; success → `onAuthenticated`; the `400`
  message; the checklist tracks the typed password.
- `libs/goblin_guide/src/components/PasswordRules.test.tsx` — all rules
  unmet for `""`, all met for a valid value, only the failing rule
  flagged otherwise.
- `apps/goblin_guide/src/App.test.tsx` — the login "Forgot password?"
  link opens `/forgot-password`; a request lands on `/reset-password`
  with the email carried over; a deep link prefills the code and resets
  through to the account shell.
- CI: the existing `goblin_guide` job runs both packages on any change
  under `apps/goblin_guide/**` or `libs/goblin_guide/**`.
