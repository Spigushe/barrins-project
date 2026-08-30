# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [Unreleased]

### Added

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
