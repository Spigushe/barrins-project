# T12. Goblin Guide — signup + email verification

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `libs/goblin_guide/`, `apps/goblin_guide/`, `docs/content/front/goblin_guide/bootstrap.md`, `docs/content/ops/architecture/decisions.md` (ADR-17) | / |
| **Initial date** | 2026-08-30 | / |
| **Status** | 🟨 **Signup slice done (2026-08-30)** — `G-03` step 2 on `proj/v2.0.0-bump`. Library `npm run build` + 39 tests green; shell `npm run build` + 6 tests green; `oxlint` + `prettier --check` clean on both. Password reset, account settings + delete, and admin service-account slices, host mounting, and the deploy playbook remain **out of scope** (each a later slice or phase). | / |
| **Source** | [Goblin Guide — Bootstrap](../../../content/front/goblin_guide/bootstrap.md) `G-03`, [Barrin's Identity — Integration Contract](../../../content/back/barrins_identity/integration.md) §4.2 / §8.3 | / |
| **Dependency** | **T11** (the login slice this builds on — shared `IdentityProvider`, `createIdentityClient`, `styles.css`, the `goblin_guide` CI job). | / |

---

## Context

T11 landed `G-03` step 1 (login, silent refresh, `GET /auth/me`). The
locked `G-03` order (bootstrap.md §3) puts **signup + email verification**
next. The backend is already on the release line and tested
(`apps/barrins_identity/app/api/v1/auth.py`): `POST /api/v1/auth/signup`,
`/signup/verify`, `/signup/resend` — wire contract frozen in
[integration.md §4.2 / §8.3](../../../content/back/barrins_identity/integration.md#42-self-registration-and-email-verification).
This slice is frontend only; no backend change.

**Decisions (user, 2026-08-30):**

- **Tracking** — its own work item (T12); T11 stays the login slice.
- **UX** — mockups approved first via a design canvas ("Goblin Guide
  Signup Slice"), then matched in code against the login slice's `gg-`
  token CSS and `tamiyo_scroll`'s `LoginPage` / `VerifyEmailPage`.
- **Two screens** — `SignupScreen` + `VerifyEmailScreen`, not one
  wizard: the verification email deep-links to a standalone
  `/verify-email?email=&code=` entry.
- **Adjacent fixes folded in** — the identity service returns
  `{ "error": { "message" } }`, not a bare `detail`; `readDetail` now
  reads both, so real-server error messages surface instead of a
  generic fallback. `userRoleSchema` gains `moderator` (was a stale
  `placeholder` copied from `tamiyo_scroll`).

## Design

- **`libs/goblin_guide/`**
  - `schemas.ts` — `signupResponseSchema`
    (`{ detail, verification_required, tokens: TokenPair | null }`),
    `resendVerificationResponseSchema` (`{ detail }`). `userRoleSchema`
    fixed to match `apps/barrins_identity`.
  - `client.ts` — `readDetail` reads `error.message` then `detail`.
    `IdentityClient` gains `signup(input)` (JSON; stores the pair only
    when `tokens` is non-null), `verifyEmail(email, code)` (stores the
    pair), `resendVerification(email)` (`502` → `IdentityError`).
  - `hooks.ts` — `useSignup` (invalidates `me` when tokens come back),
    `useVerifyEmail` (invalidates `me`), `useResendVerification`.
  - `SignupScreen` — email, `username` (with the input-rule hint and
    `aria-invalid` on a client-side miss), optional display name,
    password with a live 5-rule checklist. The username and password
    checks mirror `apps/barrins_identity/app/schemas/auth.py`
    (`USERNAME_PATTERN` / `PASSWORD_PATTERN`) for **feedback only** —
    the backend stays the source of truth on submit. Empty-field guard,
    in-flight lock, server error in `role="alert"`. On success:
    `tokens` present → `onAuthenticated`; else
    `onVerificationRequired(email)`.
  - `VerifyEmailScreen` — email (pre-fillable) + 6-digit code (masked to
    digits), submit guard on `^\d{6}$`. Resend mirrors the service's
    60-second cooldown (button disabled during the countdown); the
    resend response is shown verbatim in a success-tone `role="status"`
    banner and is deliberately generic. `400` / `409` / `429` surface in
    `role="alert"`.
  - `styles.css` — `.gg-hint`, `.gg-rules` / `.gg-rule[data-met]` (first
    use of the `--gg-success` token), `.gg-banner[data-tone='success']`,
    `.gg-code`. `icons.tsx` — `CheckIcon`, `DotIcon`, `MailIcon`.
  - `index.ts` exports the two screens + props, the three hooks, and the
    `SignupInput` / `SignupResponse` / `ResendVerificationResponse`
    types.
- **`apps/goblin_guide/`** — `SignupRoute` (`/signup`, redirects out
  when authenticated; `onVerificationRequired` → `/verify-email?email=…`)
  and `VerifyEmailRoute` (`/verify-email`, reads `?email=` / `?code=`).
  Both routes wired into `App.tsx` before the catch-all; `LoginRoute`
  now passes `onCreateAccount` → `/signup`.
- **CI** — no workflow change: the `goblin_guide` job and its
  `apps/goblin_guide/** + libs/goblin_guide/**` paths filter (T11)
  already cover this slice.

## Done statement

- `libs/goblin_guide/` — `npm run build` green (ES bundle + CSS +
  `dist/*.d.ts`), 39 vitest tests (`tokenStore` 3, `client` 18,
  `LoginScreen` 6, `SignupScreen` 7, `VerifyEmailScreen` 5), `oxlint` +
  `prettier --check` clean. `CHANGELOG.md` + `README.md` updated.
- `apps/goblin_guide/` — `npm run build` green, 6 vitest tests (`App`:
  the 3 login-slice cases plus signup-link → signup screen, new signup →
  `/verify-email` with the email carried, deep-link prefilled → verify →
  shell), `oxlint` + `prettier --check` clean.
- Docs: `bootstrap.md` status banner + `G-03` row + §6 updated; ADR-17
  gains a T12 consequence bullet; this tracker; project index T12 row
  and the T11 "Not done" list trimmed; `apps/goblin_guide/README.md`
  (syncs to `docs/content/front/goblin_guide/index.md`);
  `docs/CHANGELOG.md`.
- One logical commit (constitution §18.3). **Not touched:**
  `apps/tamiyo_scroll/**`, `apps/tolaria_news/**`,
  `apps/barrins_identity/**`, `ops/**`, `.github/**`.

## UAT (manual)

- [x] `cd libs/goblin_guide && npm run build` — `tsc` clean, Vite emits
      `dist/goblin-guide.js` + `.css` + `dist/*.d.ts` (new
      `SignupScreen` / `VerifyEmailScreen` declarations included).
- [x] `cd libs/goblin_guide && npm test` — 39 passed.
- [x] `cd apps/goblin_guide && npm install` + `npm run build` +
      `npm test` — 6 passed.
- [x] `npm run lint` + `npx prettier --check .` — clean in both
      packages.
- [x] Run the shell against a live `barrins_identity` — validated on
      `https://goblin-staging.barrins-codex.org` + `identity-staging`
      during rollout Phase 6 (2026-09-01): signup → real inbox → emailed
      `/verify-email?email=&code=` deep link, resend cooldown, wrong
      code.

## Non-regression tests

- `libs/goblin_guide/src/auth/client.test.ts` — `signup`:
  `verification_required` true (stores nothing) / false with `tokens`
  (stores the pair); `display_name` omitted when unset; `409` surfaces
  the `{ error: { message } }` envelope; `422` throws. `verifyEmail`:
  success stores the pair; `400` surfaces the message. `resend`: `202`
  returns the generic `detail`; `502` throws. `readDetail`: prefers
  `error.message`, falls back to a bare `detail`.
- `libs/goblin_guide/src/components/SignupScreen.test.tsx` — renders the
  fields; empty submit blocked with no request; the checklist tracks the
  typed password; `verification_required` → `onVerificationRequired`;
  `tokens` → `onAuthenticated`; the `409` server message shows;
  in-flight lock.
- `libs/goblin_guide/src/components/VerifyEmailScreen.test.tsx` —
  prefill from `initialEmail` / `initialCode` (non-digits stripped);
  sub-6-digit submit blocked; success → `onAuthenticated`; `400`
  message; resend hits the endpoint and starts the cooldown.
- `apps/goblin_guide/src/App.test.tsx` — the login link opens
  `/signup`; a new signup lands on `/verify-email` with the email
  carried over; a deep link prefills the code and verifies through to
  the account shell.
- CI: the existing `goblin_guide` job runs both packages on any change
  under `apps/goblin_guide/**` or `libs/goblin_guide/**`.
