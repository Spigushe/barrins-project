# T14. Goblin Guide — account settings + delete

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `libs/goblin_guide/`, `apps/goblin_guide/`, `docs/content/front/goblin_guide/bootstrap.md`, `docs/content/ops/architecture/decisions.md` (ADR-17) | / |
| **Initial date** | 2026-08-30 | / |
| **Status** | 🟨 **Account-settings slice done (2026-08-30)** — `G-03` step 4 on `feat/goblin-guide-login`. Library `npm run build` + 73 tests green; shell `npm run build` + 11 tests green; `oxlint` + `prettier --check` clean on both. Admin service-account management (the last `G-03` slice), host mounting, and the deploy playbook remain **out of scope**. | / |
| **Source** | [Goblin Guide — Bootstrap](../../../content/front/goblin_guide/bootstrap.md) `G-03`, [Barrin's Identity — Integration Contract](../../../content/back/barrins_identity/integration.md) §4.4 / §8.5 / §8.6 | / |
| **Dependency** | **T13** (the password-reset slice this builds on — reuses `CodeField` and the resend-cooldown pattern from `VerifyEmailScreen`). | / |

---

## Context

T13 landed `G-03` step 3 (password reset). The locked `G-03` order
(bootstrap.md §3) puts **account settings + delete** next, then admin
service-account management. The backend is already on the release line
and tested (`apps/barrins_identity/app/api/v1/users.py`): `PATCH
/api/v1/users/me`, `POST /api/v1/users/me/email-change/verify` +
`/resend`, `DELETE /api/v1/users/me` — wire contract frozen in
[integration.md §4.4 / §8.5 / §8.6](../../../content/back/barrins_identity/integration.md#44-account-management).
This slice is frontend only; no backend change.

**Decisions (user, 2026-08-30):**

- **Tracking** — its own work item (T14), one logical commit.
- **Screen home** — a shared-library `AccountScreen`, mounted at `/` by
  the shell in place of `Shell.tsx`'s read-only card (its footer already
  promised this "in a later release"). The shell keeps its own header
  (user chip + log out).
- **Email-change flow** — an inline PATCH → code panel: entering a new
  address reveals a 6-digit `CodeField` and a 60s resend cooldown in
  place; the current address stays shown and authoritative until
  confirmed. A standalone `/confirm-email-change` route (behind
  `RequireAuth`) renders the same panel from the emailed deep link.
- **Delete UX** — a "Danger zone" card with a current-password field,
  introducing one new token `--gg-danger` plus `.gg-button-danger`
  (solid at the final confirm step; an outline variant for the resting
  trigger). Approved via a design canvas ("Goblin Guide Account
  Settings") before code, same as T13.
- **Deep link** — confirmed against `apps/barrins_identity`
  (`_build_email_change_link`): the confirmation email links to
  `{FRONTEND_BASE_URL}/confirm-email-change?email=<enc>&code=<6 digits>`.
  Unlike `/verify-email` and `/reset-password`, this route needs a
  Bearer token (the verify call is authenticated), so it sits behind
  `RequireAuth`; an unauthenticated hit is bounced to
  `/login?next=/confirm-email-change…` and returns after sign-in.
- **Password change is out of scope** — the identity service exposes no
  authenticated password-change endpoint (integration.md §4.4); users
  change a password through the existing password-reset flow.

## Design

- **`libs/goblin_guide/`**
  - `schemas.ts` — `emailChangeResendResponseSchema` (`{ detail }`).
    `PATCH /users/me` and `/email-change/verify` both return the existing
    `principalSchema`.
  - `client.ts` — `IdentityClient` gains `updateAccount({ displayName?,
    email? })` (PATCH; `displayName`/`email` → snake_case, a field left
    `undefined` is omitted, `displayName: null` clears; `409`/`502` →
    `IdentityError`), `verifyEmailChange(code)` (POST `{code}` only — the
    caller is authenticated), `resendEmailChange()` (POST, no body,
    `202`), and `deleteAccount(currentPassword)` (DELETE
    `{current_password}`; clears the token store on `204`; `401` →
    `IdentityError`). A small `authedJson(path, method, body)` wraps
    `authed` with a JSON body, so all four get the single silent-refresh
    retry.
  - `hooks.ts` — `useUpdateAccount`, `useVerifyEmailChange`,
    `useResendEmailChange` (the first two invalidate `me`), and
    `useDeleteAccount` (`onSuccess` → `queryClient.clear()`; a failed
    attempt leaves the cache untouched so the confirm form stays put).
  - `AccountScreen` — a `useCurrentUser()` gate delegating to an inner
    `AccountScreenForm` once `user` is defined (so display-name state
    initialises from the principal without a sync effect). Three
    sections on the `gg-` token CSS:
    - **Profile** — read-only username + role rows, then an inline
      display-name field (`.gg-inline-edit`: `.gg-input` + a
      `.gg-icon-btn` check button, disabled until dirty). Save →
      `updateAccount({ displayName })` (`null` when blanked); a
      `.gg-success-text` confirms.
    - **Email** — the current address + a "Verified"/"(unverified)"
      marker. `idle` shows a secondary "Change email"; `editing` shows a
      new-email field → `updateAccount({ email })`; `pending` shows the
      warning banner naming the pending address, the `CodeField`,
      "Confirm new email" → `verifyEmailChange(code)`, the 60s cooldown
      + "Resend code" → `resendEmailChange()`, and "Use a different
      address" (there is no server cancel — the pending change simply
      expires or is re-PATCHed).
    - **Danger zone** — the `--gg-danger`-toned title, a permanence
      note, then a current-password form → `deleteAccount(password)`; on
      success `onDeleted()` (tokens already cleared).
  - `styles.css` — `--gg-danger` token; `.gg-button-danger` plus its
    `--outline` variant, `.gg-button--secondary`, `.gg-icon-btn`,
    `.gg-inline-edit`, and the account-screen layout classes
    (`.gg-account`, `.gg-section`, `.gg-section-title`, `.gg-row`,
    `.gg-chip-ok`, `.gg-note`, `.gg-success-text`).
  - `LoginScreen` — a new `accountDeleted?` prop renders an
    "account has been deleted" banner alongside `sessionExpired`.
  - `index.ts` exports `AccountScreen` + props, the four hooks,
    `AccountUpdateInput`, and `EmailChangeResendResponse`.
- **`apps/goblin_guide/`**
  - `Shell.tsx` takes optional `initialEmailChangeCode` /
    `initialPendingEmail`, renders `<AccountScreen>` in `<main>`, and
    wires `onDeleted` → `/login?deleted=1`.
  - `ConfirmEmailChangeRoute` (`/confirm-email-change`) reads `?code=` /
    `?email=` and renders `<Shell>` with them; the route is wrapped in
    `RequireAuth`.
  - `App.tsx` — `RequireAuth` gains a `?next=` return path
    (`/login?next=<encoded path>`); the new route is registered before
    `/`.
  - `LoginRoute` — follows a same-origin `?next=` after login, and
    passes `accountDeleted={?deleted=1}`.
- **CI** — no workflow change: the `goblin_guide` job and its
  `apps/goblin_guide/** + libs/goblin_guide/**` paths filter (T11)
  already cover this slice.

## Done statement

- `libs/goblin_guide/` — `npm run build` green (ES bundle + CSS +
  `dist/*.d.ts`), 73 vitest tests (`client` 33, `tokenStore` 3,
  `LoginScreen` 7, `SignupScreen` 7, `VerifyEmailScreen` 5,
  `ForgotPasswordScreen` 5, `ResetPasswordScreen` 5, `PasswordRules` 3,
  `AccountScreen` 5), `oxlint` + `prettier --check` clean.
  `CHANGELOG.md` + `README.md` updated.
- `apps/goblin_guide/` — `npm run build` green, 11 vitest tests (`App`:
  the 9 earlier-slice cases plus the account-deleted banner and the
  `/confirm-email-change` auth bounce), `oxlint` + `prettier --check`
  clean.
- Docs: `bootstrap.md` status banner + `G-03` row + §6; ADR-17 gains a
  T14 consequence bullet; this tracker; project index T14 row and the
  T13 "Not done" list trimmed; `apps/goblin_guide/README.md`;
  `docs/CHANGELOG.md`.
- One logical commit (constitution §18.3). **Not touched:**
  `apps/tamiyo_scroll/**`, `apps/tolaria_news/**`,
  `apps/barrins_identity/**`, `ops/**`, `.github/**`.

## UAT (manual)

- [x] `cd libs/goblin_guide && npm run build` — `tsc` clean, Vite emits
      `dist/goblin-guide.js` + `.css` + `dist/*.d.ts` (new `AccountScreen`
      declaration included).
- [x] `cd libs/goblin_guide && npm test` — 73 passed.
- [x] `cd apps/goblin_guide && npm run build` + `npm test` — 11 passed.
- [x] `npm run lint` + `prettier --check` — clean in both packages.
- [x] Run the shell against a live `barrins_identity` — validated on
      `https://goblin-staging.barrins-codex.org` + `identity-staging`
      during rollout Phase 6 (2026-09-01): display-name change (empty
      field clears it — stores NULL), email-change verified at the new
      address via the `/confirm-email-change?email=&code=` deep link,
      per-address resend cooldown, real delete → `/login?deleted=1` then
      handle / email reuse.

## Non-regression tests

- `libs/goblin_guide/src/auth/client.test.ts` — `updateAccount`:
  `display_name` PATCH with a bearer token; `display_name: null` clears
  and absent fields are omitted; an email-only PATCH; the `409`.
  `verifyEmailChange`: posts only the code, returns the new-email
  principal; the `400`. `resendEmailChange`: no body, `202` detail; the
  `404`. `deleteAccount`: `204` clears the store; a wrong-password `401`
  surfaces *after* the silent-refresh retry and leaves a live session.
- `libs/goblin_guide/src/components/AccountScreen.test.tsx` — Save
  disabled until the display name changes, then PATCHes `{ display_name
  }` and confirms; a cleared field sends `display_name: null`; the email
  change walks address → code step (pending address in the banner) →
  "Email updated." with a short-code guard in between; a deep link opens
  on the code step prefilled and resends with the cooldown; delete
  blocks an empty password, surfaces the `401`, then fires `onDeleted`
  with the token store cleared.
- `libs/goblin_guide/src/components/LoginScreen.test.tsx` — the
  `accountDeleted` banner.
- `apps/goblin_guide/src/App.test.tsx` — the `/login?deleted=1` banner;
  an unauthenticated `/confirm-email-change` bounces to `/login` with
  `?next=`. The three "lands on the shell" assertions now target the
  `Account` heading.
- CI: the existing `goblin_guide` job runs both packages on any change
  under `apps/goblin_guide/**` or `libs/goblin_guide/**`.
