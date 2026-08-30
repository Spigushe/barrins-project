# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [Unreleased]

### Added

- Account-settings + delete slice (T14), Goblin Guide bootstrap `G-03`
  step 4. `AccountScreen` and `useUpdateAccount` / `useVerifyEmailChange`
  / `useResendEmailChange` / `useDeleteAccount` over
  `PATCH /api/v1/users/me`, `/users/me/email-change/verify` + `/resend`,
  `DELETE /api/v1/users/me` (integration.md §4.4, §8.5–§8.6). Inline
  display-name edit (a check-button commit); a two-step email change
  that keeps the pending address apart from `user.email`, reuses the
  shared `CodeField`, and mirrors a 60-second resend cooldown; a
  password-gated account delete that clears the token store on `204`.
  `client.ts` gains `updateAccount` / `verifyEmailChange` /
  `resendEmailChange` / `deleteAccount` (all authenticated, so they get
  the single silent-refresh retry) and the `AccountUpdateInput` type;
  `schemas.ts` gains `emailChangeResendResponseSchema`. `LoginScreen`
  gains an `accountDeleted` banner prop. `styles.css` gains one new
  token, `--gg-danger`, plus `.gg-button-danger` and the account-screen
  layout classes. Authenticated password change is intentionally absent
  — the identity service has no endpoint for it; users go through the
  password-reset flow.
- Password-reset slice (T13), Goblin Guide bootstrap `G-03` step 3.
  `ForgotPasswordScreen` + `ResetPasswordScreen` and
  `usePasswordResetRequest` / `usePasswordResetConfirm` over
  `POST /api/v1/auth/password-reset/request` and `/password-reset/confirm`
  (integration.md §4.3, §8.4). The forgot screen shows the service's
  generic confirmation verbatim (never confirms whether an account
  exists); the reset screen reads the `?email=`/`?code=` deep link, and
  a successful confirm returns a fresh pair (every other session for the
  account is revoked server-side). The password-rule checklist
  (`PasswordRules`) and the digit-masked code field (`CodeField`) are
  now shared components — `SignupScreen` and `VerifyEmailScreen` were
  refactored onto them rather than keeping a third copy. `icons.tsx`
  gains `KeyIcon`.
- Signup + email-verification slice (T12), Goblin Guide bootstrap
  `G-03` step 2. `SignupScreen` + `VerifyEmailScreen` and `useSignup` /
  `useVerifyEmail` / `useResendVerification` over
  `POST /api/v1/auth/signup`, `/signup/verify`, `/signup/resend`
  (integration.md §4.2, §8.3). The signup form adds the `username`
  field and a client-side password-rule checklist (UX feedback only —
  the backend stays the source of truth); the verify screen mirrors the
  60-second resend cooldown.
- Initial package (T11), login slice — Goblin Guide bootstrap `G-03`
  step 1. `IdentityProvider` + `LoginScreen` + `useLogin` /
  `useCurrentUser` / `useLogout` / `useIdentity` over
  `POST /api/v1/auth/token`, `/auth/refresh`, `GET /auth/me`,
  `POST /auth/logout` (integration.md §4.1, §8.1–§8.2).
- `createIdentityClient`: framework-free `fetch` client with a
  single-flight silent-refresh retry on `401`.
- `createMemoryTokenStore` / `TokenStore`: pluggable client-side token
  storage (`G-05`); the default keeps both tokens in memory.
- `styles.css`: token-driven (`--color-*` / `--radius-*` with
  fallbacks), so the library renders in each host app's theme.
- Not wired into `tamiyo_scroll` or `tolaria_news` yet — consumed only
  by the standalone shell in `apps/goblin_guide/`.

### Fixed

- `IdentityError` messages now read the `{ "error": { "message" } }`
  envelope Barrin's Identity actually returns (previously only a bare
  `detail` was read, so real-server errors fell back to a generic
  string).
- `UserRole` schema: `moderator` (was a stale `placeholder`), matching
  `apps/barrins_identity`.
