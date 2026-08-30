# @barrins/goblin-guide

Shared **Goblin Guide** frontend library — the login and account-management
UI for [Barrin's Identity](../../apps/barrins_identity/), mounted by every
Barrin's frontend (Tamiyo Scroll, Tolaria News, future apps) and by the
standalone shell in [`apps/goblin_guide/`](../../apps/goblin_guide/).

Imported, never deployed on its own ([ADR-17](../../docs/content/ops/architecture/decisions.md)).
Consumers add it as a path dependency:

```jsonc
// apps/<frontend>/package.json
"dependencies": {
  "@barrins/goblin-guide": "file:../../libs/goblin_guide"
}
```

## What's here (Goblin Guide bootstrap `G-03` steps 1–2)

| Export                                                   | Purpose                                                                                               |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `IdentityProvider`                                       | Context wiring the hooks to a service URL + token store. Sits under the host's `QueryClientProvider`. |
| `LoginScreen`                                            | `POST /api/v1/auth/token` form — default / error / pending / session-expired states.                  |
| `SignupScreen`                                           | `POST /api/v1/auth/signup` form — `username` field + client-side password-rule checklist (UX only).   |
| `VerifyEmailScreen`                                      | `POST /api/v1/auth/signup/verify` — 6-digit code entry, resend with a mirrored 60-second cooldown.    |
| `useLogin`, `useCurrentUser`, `useLogout`, `useIdentity` | TanStack Query hooks over the identity endpoints.                                                     |
| `useSignup`, `useVerifyEmail`, `useResendVerification`   | TanStack Query hooks for the signup + email-verification flow.                                        |
| `createIdentityClient`                                   | Framework-free `fetch` client with single-flight silent refresh on `401`.                             |
| `createMemoryTokenStore`, `TokenStore`                   | Pluggable token storage (`G-05`); the default keeps both tokens in memory.                            |

Later slices add password reset, account settings + delete, and admin
service-account management, in that order.

## Styling

The library ships `@barrins/goblin-guide/styles.css`. Every value resolves a
host CSS custom property (`--color-*`, `--radius-*`, `--font-sans`) with a
fallback, so it renders in each host app's own theme. Class names are
prefixed `gg-`.

## Peer dependencies

`react` ^19, `react-dom` ^19, `@tanstack/react-query` ^5 — provided by the
host app.

## Scripts

```bash
npm run build        # tsc typecheck + Vite library build + .d.ts emit → dist/
npm run lint         # oxlint
npm run format:check # prettier
npm test             # vitest
```
