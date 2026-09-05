# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [2.0.0] "Morningtide" - 2026-09-06

### Added

- Initial service (T10), brought onto the `proj/v2.0.0-bump` release line
  from `feat/barrins-identity` + `claude/barrins-identity-lifecycle-settings-4g2lyh`
  (copied, not cherry-picked) and reconciled with current monorepo
  conventions:
  - RS256 JWT + JWKS authority — `POST /api/v1/auth/token` (by email),
    `/auth/refresh`, `/auth/logout`, `/auth/register` (admin),
    `GET /auth/me`, `GET /.well-known/jwks.json`, `GET /health`.
  - Self-registration + email verification
    (`REQUIRE_EMAIL_VERIFICATION`), password reset, account settings /
    email change, soft-delete account deletion, opaque per-app settings.
  - Service accounts (`client_credentials`-style) — create / list /
    revoke + `POST /api/v1/service-token`.
  - Argon2id hashing, per-IP `slowapi` rate limits, uniform
    anti-enumeration responses, the standard Barrin's error envelope.
- Unique `username` handle (constitution §13.2, `Q-03`): `VARCHAR(64)`
  UNIQUE NOT NULL INDEX on `users` (migration `f6a7b8c9d0e1`), input rule
  `^[A-Za-z0-9_-]{3,32}$`, required on signup / register, echoed in
  `UserRead`, `--username` on `create_admin.py`, anonymized on
  soft-delete. Login still authenticates by `email` (`Q-05` deferred).
- `scripts/workflow_ci.py` (copied from `apps/barrins_api`) and a
  dedicated `identity` job in `.github/workflows/CI.yml`
  (`apps/barrins_identity/**` / `libs/identity_client/**` paths-filter,
  Postgres service).
- `.env.example` reconciled with the deployment secrets templates
  (`PASSWORD_RESET_*`, `MAX_APP_SETTINGS_BYTES`).

- Cross-app user directory (ADR-19): `POST /api/v1/users/lookup`
  (service token, scope `identity:users:read`) — batch `{user_id:
  {username, display_name}}` resolution for a consuming app's team
  rosters / sharing labels, without exposing email addresses.
- RS256/JWKS adopted as the ecosystem's shared token authority (ADR-16):
  `barrins_api` verifies identity's tokens locally via `libs/
  identity_client` rather than minting its own — see that app's own
  changelog for the cutover (drops its local `users` table entirely,
  ADR-20). Refresh token issued as an `HttpOnly` cookie (ADR-18) so a
  reload/reopened tab in cookie-mode consuming apps stays signed in.
- `ops/my-server/barrins_identity.yml` deployment playbook and the
  Goblin Guide account-management frontend (`apps/goblin_guide`,
  `libs/goblin_guide`) — see that app's own changelog.

## [1.0.0] "WorldWake" - 2026-07-24

Nothing yet.
