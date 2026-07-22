<!-- cSpell:ignore JWKS pyjwt slowapi argon respx tolaria cutover keypair -->
# Barrin's Identity — Implementation Plan

> **Target**: `apps/barrins_identity/` (this monorepo) — consumed by
> `apps/barrins_api/` and, once built, by `apps/tolaria_news/` and
> `apps/tamiyo_scroll/`. Frontend: `apps/goblin_guide/` (placeholder, see
> [Goblin Guide](../../front/goblin_guide/bootstrap.md)).
> **Status**: 🟨 Partially implemented (2026-07-22) — the standalone
> `barrins-identity` service (§6–§8: config, models, RS256 security, human
> login, service accounts, JWKS) is built on `feat/barrins-identity` per
> the confirmed [test plan](./tests.md). Phase 9 (`barrins_api` cutover)
> and Phase 10 (Tolaria News routes) are **not** implemented — §9 is
> explicitly a live-data migration requiring a user-confirmed maintenance
> window, and §10 depends on front specification that isn't final yet.
> **§14–§18 (below) are proposed, not implemented** — password reset,
> account deletion, global account settings, and per-app settings. Per
> constitution §16.4, they require explicit user sign-off on the open
> design questions in §18 and a confirmed [test plan](./tests.md) extension
> before any code is written.
> **Supersedes**: the "Future Architecture Proposal" previously on this page
> (OAuth2/OIDC, "wait for a second account-based app") and constitution §40 in
> their prior form. See [Superseded decision](#2-superseded-decision) below
> for why.

---

## 1. Purpose

Extract authentication (`apps/barrins_api/app/models/user.py`,
`app/core/security.py`, `app/dependencies/auth.py`,
`app/api/v1/routers/auth.py` — see
[JWT Authentication & Roles](../barrins_api/auth_roles.md)) out of
`barrins_api` into its own app, `apps/barrins_identity/`, so that
`barrins_api`, `tolaria_news` and `tamiyo_scroll` can share one identity
without a shared signing secret.

This document prepares implementation. It does not implement anything. Per
the project's tests-first rule (constitution §16.4), the companion
[Tests](./tests.md) plan must be reviewed and confirmed before any of the
phases below are coded.

---

## 2. Superseded decision

The prior version of this page proposed a full OAuth 2.0 / OpenID Connect
provider, to be built only after a second account-based Barrin's application
existed, explicitly recommending *not* to build it yet. That plan predates
two facts that now hold:

- The repo split this plan was written to precede (`barrins_api`,
  `tolaria_news`, `tamiyo_scroll` as separate GitHub repos) has already been
  consolidated into this monorepo — `apps/barrins_identity/`,
  `apps/tolaria_news/` and `apps/tamiyo_scroll/` already exist as scaffolded
  app directories.
- The user has validated moving forward now, on branch
  `feat/barrins-identity`.

The new, authoritative decision: build `barrins-identity` now, as a **JWT
RS256 + JWKS** service (not a full OIDC provider — no authorization-code
flow, no third-party client registration). This is a smaller surface than
OAuth2/OIDC, sized to this project's actual need: one shared human login
flow, plus a `client_credentials`-style machine-to-machine flow for
service-to-service calls.

---

## 3. Context

`barrins_api` currently owns a complete, working JWT auth system (HS256,
Argon2id, DB-backed `token_version` revocation — see
[auth_roles.md](../barrins_api/auth_roles.md)), but it is locked inside
`barrins_api`'s own process and database. That coupling becomes a problem
the moment a second service needs to authenticate its own users or its own
machine-to-machine calls:

- `tolaria_news` (`apps/tolaria_news/`) — a Duel Commander tournament
  aggregator, currently an empty placeholder app — will need its
  consumer-facing routes secured from the day it gets its first route in
  `barrins_api` (there is no such route yet; grep confirms no `tolaria` path
  exists under `apps/barrins_api/app/api` today, so this is "secure it from
  the start," not "add auth to something already public").
- `tamiyo_scroll` already authenticates today through `barrins_api`'s local
  auth; it becomes a consumer of `barrins-identity` once the cutover (§9)
  lands.
- A shared HS256 secret across services is an anti-pattern: compromising any
  one consumer compromises every other consumer's ability to *forge* tokens,
  not just verify them, and there is no way to revoke trust for one service
  without redeploying all of them.

---

## 4. Decision: RS256 + JWKS, no shared secret

| Option | Mechanism | Verdict |
| ------ | --------- | ------- |
| **RS256 (chosen)** | `barrins-identity` signs with an RSA private key; consumers verify with the public key served at `/.well-known/jwks.json` | No shared secret; key rotation via `kid` without coordinating a redeploy of every consumer; verification is fully local (no network call per request) |
| HS256 shared secret | Same symmetric secret distributed to every consumer | Rejected — any consumer that can verify can also forge; rotation requires a synchronized redeploy of every service |

### Revocation: short TTL, not per-request introspection

Access tokens carry a short TTL (10 min) and are verified locally (signature
\+ expiry only, no DB lookup). `token_version` is checked only at `/refresh`
and `/logout`, same pattern as today's `barrins_api` auth. Consequence: a
compromised-account revocation takes up to 10 minutes to take effect on
already-issued access tokens. Rejected alternative: consumers calling
`/introspect` on every request — this recreates a hard synchronous coupling
and a single point of failure, defeating the purpose of JWKS.

> Open item (non-blocking): if instant revocation becomes a real product
> need (e.g. admin ban), add a short-cache revocation-list endpoint
> (`GET /revocations?since=`). Not implemented now — a 10-minute TTL is
> judged sufficient for current scope.

### Verification client: duplicated module, not a shared package

The verification client (`identity_client/`, ~150 lines: JWKS fetch + cache,
FastAPI dependency factory) is copied as-is into each consumer app directory
(`apps/barrins_api/identity_client/`, later `apps/tolaria_news/`,
`apps/tamiyo_scroll/` if they end up needing server-side verification)
rather than published as an internal package. Since all consumers already
live in this monorepo, this could arguably be a shared
`libs/identity_client/` package instead of a copy-per-app — **open question,
needs a decision before Phase 9** (see §11).

---

## 5. Target architecture

```text
barrins-identity  (new app: apps/barrins_identity/)
  DB: users, service_accounts
  |
  |-- JWKS (public key, cached) ------------> barrins_api
  |                                            (verifies locally)
  |-- service-token (client_credentials) ---> barrins_api
  |                                            (routes /tolaria/*)
  |-- access/refresh (human login) ---------> barrins_api, tamiyo_scroll
  |
  |-- JWKS + service-token (same flows) -----> tolaria_news (future)
                                                tamiyo_scroll (post-cutover)
```

- `barrins-identity` is the only app holding a signing private key and
  touching plaintext passwords.
- All consumers verify tokens locally (cached public key) — no network call
  per protected request in steady state. Network calls to `barrins-identity`
  happen only at: human login, refresh, periodic JWKS refresh (long cache,
  e.g. 1h), service-token issuance (cached until expiry).

---

## 6. Configuration

`apps/barrins_identity/app/config/base.py`:

| Variable | Description | Default |
| -------- | ------------ | ------- |
| `DATABASE_URL` | Own PostgreSQL connection | required |
| `JWT_PRIVATE_KEY` | RSA private key PEM (`SecretStr`) | required, generated via `openssl genrsa` |
| `JWT_KID` | Current key id (rotation) | `"2026-07"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `10` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `SERVICE_TOKEN_EXPIRE_MINUTES` | Service-account token lifetime | `15` |
| `ARGON2_MEMORY_COST_KIB` / `ARGON2_TIME_COST` / `ARGON2_PARALLELISM` | Argon2id cost params | `65536` / `3` / `4` |
| `LOGIN_RATE_LIMIT` | `/token` limit | `5/minute per IP` |
| `ALLOWED_ORIGINS` | CORS | required |
| `PASSWORD_RESET_CODE_TTL_MINUTES` | Reset code validity (§14) | `15` |
| `PASSWORD_RESET_MAX_ATTEMPTS` | Attempts allowed before a reset code is invalidated (§14) | `5` |
| `PASSWORD_RESET_RESEND_COOLDOWN_SECONDS` | Minimum delay between two reset code sends (§14) | `60` |
| `PASSWORD_RESET_RATE_LIMIT` | `/auth/password-reset/request` limit, per IP (§14) | `5/minute` |
| `MAX_APP_SETTINGS_BYTES` | Size cap on a per-app settings blob (§17) | `16384` |

Email-change confirmation (§16) reuses the existing
`VERIFICATION_CODE_TTL_MINUTES` / `VERIFICATION_MAX_ATTEMPTS` /
`VERIFICATION_RESEND_COOLDOWN_SECONDS` settings from §8 — no new config for
that flow.

Consumers (`apps/barrins_api/app/config/base.py`, later `tolaria_news`,
`tamiyo_scroll`):

| Variable | Description |
| -------- | ------------ |
| `IDENTITY_SERVICE_URL` | Base URL of `barrins-identity` |
| `IDENTITY_JWKS_CACHE_TTL_SECONDS` | Public key cache TTL (default `3600`) |
| `IDENTITY_SERVICE_CLIENT_ID` / `IDENTITY_SERVICE_CLIENT_SECRET` | This app's own service-account credentials, if it needs to call other services |

---

## 7. Data model

`apps/barrins_identity/app/models/`:

- `User` — same shape as today's `apps/barrins_api/app/models/user.py`,
  migrated as-is except the placeholder role is renamed `role_c` →
  `moderator` (clean-slate opportunity on the new schema; the old
  `barrins_api` table keeps `role_c` until the cutover in §9).
- `ServiceAccount` (new) — `client_id`, hashed `client_secret` (Argon2id,
  same mechanism as user passwords — never stored or logged in plaintext),
  `scopes`, `is_active`, `token_version`.
- `EmailVerification` — same shape as
  `apps/barrins_api/app/models/email_verification.py`, one pending row per
  unverified account (`UNIQUE(user_id)`), used by the self-registration
  flow in §8.

Stack: SQLAlchemy 2.x (`Mapped[...]` / `mapped_column`), Alembic
(hand-written migrations — no autogenerate needed for a schema this small),
Pydantic v2 schemas with `extra="forbid"` on every input schema, PyJWT (not
`python-jose` — picks up the `barrins_api` TODO item to drop
`python-jose`, but only in the new service; `barrins_api` itself drops the
dependency entirely once it only verifies tokens, see §9).

---

## 8. Routes

### Human login (`apps/barrins_identity/app/api/v1/routers/auth.py`)

| Method | Path | Auth | Notes |
| ------ | ---- | ---- | ----- |
| `POST` | `/token` | none | `OAuth2PasswordRequestForm` (not raw `email`/`password` params — needed for the Swagger "Authorize" button and `OAuth2PasswordBearer` compatibility); rate-limited (`LOGIN_RATE_LIMIT`) |
| `POST` | `/refresh` | none | Rotates both tokens; consumes the presented refresh token |
| `POST` | `/register` | admin | |
| `GET` | `/me` | user | |
| `POST` | `/logout` | user | Increments `token_version` — all outstanding tokens rejected |

All login failure branches (unknown email, wrong password, inactive
account) return the same `401` with the same message, in the order
`verify_password` → `is_active`, so a disabled account can't be
distinguished from a wrong password by timing or status code — same
anti-enumeration pattern already used in `barrins_api` (see
[auth_roles.md](../barrins_api/auth_roles.md)).

### Self-registration & email verification (`.../auth.py`)

Ported as-is from `barrins_api`'s existing, working implementation
(constitution §13.2–§13.3), gated behind `REQUIRE_EMAIL_VERIFICATION`
(default `true`) so the flow can be enabled without a code change once
SMTP is configured:

| Method | Path | Auth | Notes |
| ------ | ---- | ---- | ----- |
| `POST` | `/signup` | none | Creates an unverified account, sends a 6-digit code by email. Returns `409` if the email is already registered, `502` (no account created) if the email fails to send. |
| `POST` | `/signup/verify` | none | Validates the code, sets `is_verified=True`, returns a token pair. `400` for any invalid/expired/missing code (single message), `409` if already verified, `429` beyond `VERIFICATION_MAX_ATTEMPTS`. |
| `POST` | `/signup/resend` | none | Always returns the same generic `202` message regardless of whether the account exists, is already verified, or is in cooldown (anti-enumeration). |

If `REQUIRE_EMAIL_VERIFICATION=false` (temporary workaround while SMTP
isn't configured), `/signup` creates an already-verified account and logs
the user in immediately — no email sent, no `EmailVerification` row
created. `SMTP_HOST`/`FRONTEND_BASE_URL` are only required in production
while this flag is `true` (same `_production_requires_real_smtp_and_frontend_url`
model validator as `barrins_api`).

Email sending goes through an `EmailSender` protocol
(`app/services/email/`) — `ConsoleEmailSender` (logs instead of sending,
used whenever `SMTP_HOST` is empty) or `SMTPEmailSender` (stdlib
`smtplib`, no new dependency). New table: `auth_email_verifications`
(one row per pending account, `UNIQUE(user_id)`).

### Service accounts (`.../routers/service_accounts.py`)

`client_credentials`-style flow for machine-to-machine calls (`barrins_api`
calling on behalf of `tolaria_news` routes, for instance):

| Method | Path | Auth |
| ------ | ---- | ---- |
| `POST` | `/service-accounts` | admin — create, list, revoke |
| `POST` | `/service-token` | none (authenticates via `client_id`/`client_secret` in body) |

An invalid `client_secret` returns `401` without distinguishing "unknown
`client_id`" from "wrong secret" (same anti-enumeration principle as
`/token`).

### JWKS (`.../routers/well_known.py`)

| Method | Path | Auth |
| ------ | ---- | ---- |
| `GET` | `/.well-known/jwks.json` | none (public key only) |

The private key is parsed and the public key derived **once**, at module
load (`app/core/security.py`) — not on every token decode or every JWKS
request.

---

## 9. Migration & `barrins_api` cutover

`apps/barrins_api` changes (one-time cutover, not incremental):

| Action | Files |
| ------ | ----- |
| Create | `scripts/migrate_users_to_identity.py` (copies `users` rows to `barrins-identity`'s DB — must run inside a single transaction: `target_engine.begin()`, not `.connect()`, so a mid-loop failure rolls back fully rather than leaving a partial cutover) |
| Create | `identity_client/` (copied from `apps/barrins_identity/identity_client/`, see §4) |
| Replace | `app/dependencies/auth.py` — now verifies via `identity_client`, no local DB user lookup |
| Delete | `app/models/user.py`, `app/schemas/auth.py`, `app/core/security.py`, `app/api/v1/routers/auth.py`, `scripts/create_admin.py` (all move to `barrins_identity`) |
| Create | Alembic migration dropping the local `users` table |
| Modify | `app/config/base.py` — remove local JWT/Argon2 fields, add `identity_service_url`, `identity_jwks_cache_ttl_seconds` |
| Modify | `pyproject.toml` — remove `python-jose`, `argon2-cffi`; add `pyjwt`, `respx` (test-only) |
| Adapt | Routers currently depending on the local auth dependency (`db_stats`, `decklist_import`, `format_dc`, `ml`, `mtgjson`) — dependency import changes only, no logic change |

This is the highest-risk phase (live data cutover). Do not run it against
production data without an explicit user-confirmed maintenance window; in
dev/CI it can run against two test databases without extra confirmation.

---

## 10. Tolaria News

Unlike the source plan this was adapted from (which assumed existing,
unsecured `/api/v1/tolaria/*` routes), **no such routes exist yet** in
`apps/barrins_api` — `tolaria_news` is currently an empty placeholder app.
So this is not a retrofit: whichever routes get built for `tolaria_news`
must depend on a `barrins-identity` service-token (scope, e.g.
`tolaria:read`) from their very first commit, following the same
`require_scope(...)` dependency pattern as `barrins_api`'s own role checks.

`tolaria_news` will also gain a second, independent backend: a periodic
calculation service reading from and writing back to `barrins_api`. See
[Tolaria News platform.md
§3](../../front/tolaria_news/platform.md#3-backend-side-detail-karn_tablets-informational-only)
— this is the first concrete second-backend consumer of the service-account
design in §4, which until now only had `tolaria_news`'s (not-yet-built) BFF
routes as a hypothetical justification.

---

## 11. Open questions before implementation starts

1. **Shared `identity_client/` package vs. copy-per-app** (§4) — still open,
   deferred to Phase 9 (not started tonight). Leaning towards copy-per-app
   as documented, but not yet decided.
2. **`apps/tolaria_news` scope and timeline** — still open, deferred to
   Phase 10/11 (front under specification).
3. **Role rename `role_c` → `moderator`** — **resolved**: `moderator` is
   the name implemented in `app/models/user.py` (this app's `UserRole`
   enum). See the implementation decision log in this app's README /
   session notes for the full list of choices made during the unattended
   implementation pass on 2026-07-22, flagged for review.

---

## 12. Quality review carried over

The source plan (18 phase documents) went through an internal review before
this consolidation; the corrections below are already reflected in this
document and must not be reintroduced:

- `/token` must use `OAuth2PasswordRequestForm`, not raw parameters (§8).
- The Tolaria News scope dependency must be passed as the dependency
  function itself, never as a string (§10) — a string argument would raise
  `TypeError` at import time.
- The RSA public key must be derived once at module load, not on every
  decode/JWKS call (§6, §8).
- The data-migration script must use `target_engine.begin()` for atomicity,
  not `.connect()` (§9).
- `/refresh` must catch `jwt.PyJWTError` specifically, never a bare
  `Exception`.

---

## 13. Deployment notes

- Never commit a real RSA private key, even for tests — tests generate an
  ephemeral keypair
  (`cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key`).
- Key rotation: publish the new public key under a new `kid` in the JWKS
  response before switching `JWT_PRIVATE_KEY`/`JWT_KID` to the new pair, so
  tokens signed with the outgoing key remain verifiable until they
  naturally expire.
- Deployment follows the same independent-deployment principle as the rest
  of the ecosystem (constitution §26–§33): `barrins-identity` is deployable
  and rollback-able independently of `barrins_api`.

---

## 14. Password reset

> **Status**: 🟦 Proposed. Not implemented. Requires sign-off on the
> mechanism choice below (§18.3) and a confirmed test plan
> ([tests.md](./tests.md) §7–§8) before implementation.

### 14.1 Mechanism

Two things must be decided: what kind of token proves "this request came
from the email owner," and how it's delivered.

| Option | Description | Verdict |
| ------ | ----------- | ------- |
| **6-digit code + throttle (chosen)** | Reuses the exact machinery already built for signup (`generate_verification_code`, `hash_verification_code`, `verify_verification_code`, attempts/cooldown) against a **new sibling table**, `PasswordResetCode` | No new crypto primitive, no new email-link-vs-code UX pattern to design from scratch; the throttle/attempts semantics are already implemented and tested |
| Signed JWT reset link | A short-lived JWT (`type: "password_reset"`) embedded in an emailed link, verified via `app/core/security.py` | Rejected — introduces a second "prove you own this inbox" pattern alongside the code mechanism for no functional gain; a link-based flow also can't reuse the attempts/cooldown throttle already built for codes without inventing an equivalent for JWTs (replay window, single-use tracking) |
| Purpose column on existing `EmailVerification` table | Add a `purpose: Literal["signup", "password_reset"]` discriminator to `auth_email_verifications`, widen `UNIQUE(user_id)` to `UNIQUE(user_id, purpose)` | Rejected — `auth_email_verifications` already shipped (migration `b2c3d4e5f6a7`, this branch); altering its unique constraint touches a live table for a benefit (avoiding one more small table) that doesn't outweigh the migration risk. A new additive table is lower-risk and keeps each flow's row genuinely single-purpose (readability) |

**Decision**: 6-digit code, same throttle mechanism, new table `PasswordResetCode`
(mirrors `EmailVerification`'s shape exactly: `id`, `user_id` `UNIQUE`,
`code_hash`, `expires_at`, `attempts`, `last_sent_at`, `created_at`).
`hash_verification_code`'s existing binding to `user_id` (not to a
"purpose") is still sufficient here: each flow's code lives in its own
table, looked up by the route that owns that flow, so there is no
cross-flow replay surface to close.

TTL 15 minutes (`PASSWORD_RESET_CODE_TTL_MINUTES`), 5 attempts
(`PASSWORD_RESET_MAX_ATTEMPTS`), 60s resend cooldown
(`PASSWORD_RESET_RESEND_COOLDOWN_SECONDS`) — same defaults as signup
verification, configured separately so they can be tuned independently.

### 14.2 Routes

| Method | Path | Auth | Notes |
| ------ | ---- | ---- | ----- |
| `POST` | `/auth/password-reset/request` | none | Body: `{email}`. Always returns the same generic `202` message, rate-limited per IP (`PASSWORD_RESET_RATE_LIMIT`, same pattern as `LOGIN_RATE_LIMIT`) |
| `POST` | `/auth/password-reset/confirm` | none | Body: `{email, code, new_password}`. `400` for any invalid/expired/missing code (single message), `429` beyond `PASSWORD_RESET_MAX_ATTEMPTS`. On success: hashes `new_password`, bumps `token_version` (all outstanding sessions invalidated — a password reset implies "assume the account was compromised"), deletes the `PasswordResetCode` row, and returns a fresh `TokenPair` (same auto-login UX as `/auth/signup/verify`) |

### 14.3 Anti-enumeration

`POST /auth/password-reset/request` never reveals whether the email
exists, whether the account is verified, or whether it's active — same
generic response in every case (pattern already used by
`/auth/signup/resend`). No account existence check leaks through timing
either (the code generation + email send only happens on the success
path; the "user not found" path returns immediately, same shape of
short-circuit already accepted for `/auth/signup/resend`).

A consequence of the account-deletion design (§15): a soft-deleted
account's `email` column is overwritten with an anonymized value at
deletion time, so a reset request against the original address simply
finds no matching row and gets the generic response — no special-casing
needed for "can't reset a deleted account."

Password reset does not check `is_verified` — consistent with `/auth/token`,
which also does not gate login on `is_verified` today (only `is_active`
is checked). It does implicitly require `is_active=True` to find a
matching row, for the reason above.

### 14.4 Email delivery

New `EmailSender` protocol method, `send_password_reset_code(*, to_email,
code, reset_link)`, implemented by both `ConsoleEmailSender` and
`SMTPEmailSender` alongside the existing `send_verification_code`. Kept as
a distinct method rather than a `purpose` parameter on the existing one:
the email copy differs ("reset your password" vs. "confirm your
account") and a distinct method name keeps that difference explicit
(constitution §4.6) instead of branching inside a single method on a
string flag.

---

## 15. Account deletion

> **Status**: 🟦 Proposed. Not implemented. Requires sign-off on soft vs.
> hard delete (§18.2) before implementation.

### 15.1 Soft vs. hard delete

| Option | Description | Verdict |
| ------ | ----------- | ------- |
| **Soft delete (chosen)** | `is_active=False`, `token_version += 1`, `email` and `display_name` anonymized (`email = f"deleted-{uuid4()}@barrins.invalid"`, `display_name = None`), `hashed_password` overwritten with the hash of a random, never-issued secret. Row (and `id`) kept. | `barrins_identity` is the FK anchor for every other app's user-owned data (tournament results, decklists, ...); a hard delete would orphan those rows or require every consumer to handle a "deleted user" sentinel on day one. Anonymizing frees the original email/display_name for reuse without destroying the anchor. |
| Hard delete | Row removed entirely. `email` immediately reusable. | Rejected — destroys the audit trail and any FK relationship other apps hold on this `user_id`, ahead of those apps having a defined "deleted user" story. Simpler, but permanent in a way the ecosystem isn't ready to assume (constitution §48 — prefer migration paths over destructive rewrites). |

**Decision**: soft delete, as above. A data-retention/cleanup job for
anonymized rows is explicitly out of scope for this task (§5 non-goals) —
the schema choice must not block one being added later, and it doesn't:
nothing here prevents a future scheduled job from hard-deleting rows past
some retention window.

Cascading cleanup of **app-owned** data (e.g. `barrins_api`'s
`TSPersonalDeck` rows for a deleted user) is explicitly **out of scope**
for `barrins_identity` — each consuming app owns its own data retention
policy on account deletion (constitution §4.1: identity doesn't own app
business data). `barrins_identity` never reaches into another app's
database.

### 15.2 Route

| Method | Path | Auth | Notes |
| ------ | ---- | ---- | ----- |
| `DELETE` | `/users/me` | user | Body: `{current_password}`. `401` if the password doesn't match. On success: soft-deletes as in §15.1, `204 No Content`. |

**Re-auth mechanism** — current password in the request body, not a
"recent token" freshness check. A freshness check (e.g. rejecting access
tokens older than N minutes) would need a new `iat` claim threaded through
`create_access_token`/`TokenData`, and only proves a device recently
authenticated — not that the caller currently knows the password. Password
re-entry is simpler (reuses `verify_password`, already used everywhere
else) and is the stronger guarantee for a destructive, irreversible-feeling
action. This is a UX/implementation call, not one of the headline open
questions, but is flagged here for visibility.

**Verb** — `DELETE` with a JSON body, not `POST /users/me/delete`. FastAPI
and this project's actual clients (its own frontends/BFFs, not third-party
integrators) support a body on `DELETE` without the proxy-stripping
concerns that make `DELETE`+body risky for public-facing APIs behind
arbitrary intermediaries. Deleting the `/users/me` resource with `DELETE`
is the more direct mapping once `/users/me` exists as a resource at all
(see §16).

Once deleted (`is_active=False`), `get_current_user` already rejects every
outstanding token on that account via its existing `is_active` check
(`app/dependencies/auth.py`) — before it even reaches the `token_version`
comparison. Bumping `token_version` too is redundant for that reason
alone, but is done anyway for consistency with the existing
`revoke_service_account` pattern (which sets both simultaneously) — not
because it's independently necessary here.

---

## 16. Global account settings

> **Status**: 🟦 Proposed. Not implemented.

### 16.1 Route split: `/auth/me` vs. `/users/me`

`GET /auth/me` (existing, unchanged) stays the read endpoint for
session/auth context. A new `/users` router (`app/api/v1/users.py`, mounted
at `/api/v1/users`) owns account-resource mutation: `PATCH /users/me`
(this section), `DELETE /users/me` (§15), `GET`/`PUT
/users/me/settings/{app_key}` (§17). This keeps `/auth/*` scoped to
authentication/session lifecycle (token issuance, refresh, logout,
"who am I") and `/users/*` scoped to account-resource management — both
operate on the same `User` row via the same `CurrentUser` dependency, so
this is a route-surface split, not duplicated logic.

### 16.2 `PATCH /users/me`

Request schema `AccountSettingsUpdate` (`extra="forbid"`):

```python
class AccountSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = None
    email: EmailStr | None = None
```

Partial-update semantics via `model_fields_set` (same pattern as
`barrins_api`'s `UserSettingsUpdate` in
`app/api/bff/ts_router/settings.py`, see §17.4 for that file's other
role in this document): a field absent from the payload is left
untouched; `display_name` explicitly set to `null` clears it.

**`display_name`**: applied immediately, no verification — display name
carries no security meaning.

**`email`**: this is the part that needs an explicit intermediate-state
decision, because the constitution requires the old address to "stay
active/authoritative until the new one is confirmed" — which rules out
simply overwriting `user.email` and re-running the signup verification
flow against it (that would lock the user out of their own account with
their old, working address the moment they fat-finger the new one).

| Behavior | `REQUIRE_EMAIL_VERIFICATION=true` (default) | `REQUIRE_EMAIL_VERIFICATION=false` |
| -------- | -------------------------------------------- | ----------------------------------- |
| On `PATCH /users/me` with a new `email` | `user.email` **unchanged**. A new row is written to `EmailChangeRequest` (below) and a code is emailed to the **new** address. `PATCH` response reflects the still-current (old) email. | `user.email` overwritten immediately, no code, no `EmailChangeRequest` row — same gating precedent as `/auth/signup` (§8). |
| Uniqueness check | `409` if the new email is already registered to a *different* account — checked at request time, and re-checked at confirm time (§16.3) to close the race where someone else registers it in between. | `409` at request time (same check, no confirm step to re-check at). |

New table `EmailChangeRequest` (one pending change per user,
`UNIQUE(user_id)` — a second `PATCH` with a new email before confirming
replaces the pending request, same "resend replaces" precedent as
`EmailVerification`): `id`, `user_id`, `new_email`, `code_hash`,
`expires_at`, `attempts`, `last_sent_at`, `created_at`. Reuses the
existing `VERIFICATION_CODE_TTL_MINUTES` / `VERIFICATION_MAX_ATTEMPTS` /
`VERIFICATION_RESEND_COOLDOWN_SECONDS` settings (§8) — this is explicitly
"the *existing* verification-code mechanism," not a new one.

### 16.3 Confirming the email change

| Method | Path | Auth | Notes |
| ------ | ---- | ---- | ----- |
| `POST` | `/users/me/email-change/verify` | user | Body: `{code}` — no `email` param needed, unlike `/auth/signup/verify`, because the caller is already authenticated as the account with the pending change. Re-checks `new_email` uniqueness (race close), then sets `user.email = new_email`, deletes the `EmailChangeRequest` row. `400` invalid/expired code, `404` no pending change, `429` beyond max attempts. `409` if the address was claimed by someone else in the interim — in that case the pending `EmailChangeRequest` row is also deleted (the queued address is now permanently unusable for this request); the user must `PATCH /users/me` again with a different address to create a fresh request. |
| `POST` | `/users/me/email-change/resend` | user | Resends the code to the pending `new_email`, cooldown-gated. Not anti-enumeration-sensitive (the caller is already authenticated) — `404` if there's no pending change is fine here, unlike the public, unauthenticated `/auth/signup/resend`. |

`user.email`'s value inside already-issued access tokens (the `email`
claim in `_claims()`) is not force-invalidated on an email change —
consistent with the existing "short TTL, not per-request introspection"
revocation model (§4): the claim is informational, never used for
authorization, so a stale claim for up to one access-token TTL is
accepted, same as it already is for a display-only field.

New `EmailSender` method, `send_email_change_code(*, to_email, code,
verify_link)` — distinct from `send_verification_code` (signup) and
`send_password_reset_code` (§14.4) for the same reason: different email
copy, explicit method name over a shared method branching on a purpose
string.

---

## 17. Per-app settings

> **Status**: 🟦 Proposed. Not implemented. Requires sign-off on the data
> shape (§18.1) before implementation.

### 17.1 Data shape

| Option | Description | Verdict |
| ------ | ----------- | ------- |
| **(a) Opaque JSON blob per `(user_id, app_key)` (chosen)** | `barrins_identity` stores and serves the JSON verbatim, validates nothing about its internal shape beyond overall size; each consuming app/BFF owns its own schema for what's inside. Matches the existing `ServiceAccount.scopes` `JSONBCompat` precedent (`app/models/_types.py`). | Minimal new surface area in `barrins_identity`; a malformed payload from one app can't corrupt another app's row (separate rows), only its own. No server-side validation of content is the accepted trade-off. |
| (b) One typed table per app | Stronger validation; every new app or new setting requires a migration + endpoint in `barrins_identity`. | Rejected — couples app-specific concerns into the identity service, working against constitution §4.1 (identity shouldn't accumulate app business logic) and against keeping `barrins_identity` a thin, app-agnostic store. |

**Decision**: (a). New table `AppSettings`: `id`, `user_id` (FK
`users.id`, `ondelete="CASCADE"` — schema-level integrity; in practice the
row is never actually deleted since accounts are soft-deleted, §15),
`app_key` (`String`, not a Postgres native `ENUM` — see §17.2), `data`
(`JSONBCompat`, default `{}`), `created_at`, `updated_at`.
`UNIQUE(user_id, app_key)`.

### 17.2 `app_key`

A fixed set, not a free-form string (prevents typo'd/unbounded key
sprawl): a Python `StrEnum` (`AppKey`, `app/models/app_settings.py`) with
members `tamiyo_scroll`, `tolaria_news` today. Stored as a plain `String`
column rather than a Postgres native `ENUM` type: a DB-level enum needs an
`ALTER TYPE ... ADD VALUE` migration every time a new Barrin's app is
added, which is exactly the kind of migration friction this design should
avoid for something that's really just an API-level allow-list.

The route's path parameter is typed `str`, not `AppKey`, deliberately:
FastAPI's default behavior for an enum-typed path parameter that doesn't
match any member is `422`, but the contract calls for `404` on an unknown
`app_key` (unknown resource, not a malformed request) — so membership is
checked manually in the handler, raising `404` explicitly.

### 17.3 Routes

| Method | Path | Auth | Notes |
| ------ | ---- | ---- | ----- |
| `GET` | `/users/me/settings/{app_key}` | user | Returns the stored blob, or `{}` if no row exists yet — a `GET` never creates a row (only `PUT` does, avoiding empty-row churn from read-only clients). `404` for an unknown `app_key`. |
| `PUT` | `/users/me/settings/{app_key}` | user | Full replace (upsert: creates the row if absent, else overwrites `data` and bumps `updated_at`). Body: raw JSON object, capped at `MAX_APP_SETTINGS_BYTES` (default 16 KiB). `404` unknown `app_key`, `413` payload too large. |

The size cap is enforced in the route handler, not via a Pydantic
validator on the request schema: Pydantic validation failures are always
`422`, but "too large" is semantically a `413`, so the handler
deserializes the body, computes its serialized size, and raises `413`
explicitly when it exceeds the cap — kept separate from "malformed JSON"
(still `422`, from normal body parsing).

Authentication for now is `CurrentUser` (human access token) only. The
service-account-token path described in the original request/response
contract sketch (`settings:{app_key}:read` / `settings:{app_key}:write`
scopes) is **not implemented** — see §18.4: it only becomes usable once
`barrins_api`'s BFF has real `barrins_identity` user UUIDs to pass, i.e.
after the Phase 9 cutover (§9).

### 17.4 Concrete example: `tamiyo_scroll`'s current BFF settings

`barrins_api`'s existing (unrelated, not wired to this contract — see
§18.4) `TSUserSettings`
(`apps/barrins_api/app/models/tamiyo_scroll.py`,
`apps/barrins_api/app/api/bff/ts_router/settings.py`) is used here only to
sanity-check the blob shape against a real payload:

```json
{
  "data_shared": false,
  "active_personal_deck_id": null
}
```

This is the kind of shape `tamiyo_scroll`'s BFF would `PUT` to
`/users/me/settings/tamiyo_scroll` if it were wired to this contract — it
is not wired today (§18.4, §5 non-goals).

---

## 18. Open design decisions requiring sign-off

Per constitution §16.2/§16.3, these are presented as alternatives with a
recommendation — not silently decided. Implementation of §14–§17 above
does not start until the user has signed off on 18.1–18.3, and until the
[test plan](./tests.md) extension (§7–§11 there) is confirmed.

### 18.1 Per-app settings data shape (§17.1)

Recommended: **(a) opaque JSON blob**, matching the existing
`ServiceAccount.scopes` `JSONBCompat` precedent.

### 18.2 Account deletion: soft vs. hard delete (§15.1)

Recommended: **soft delete** with anonymized `email`/`display_name`,
given `barrins_identity` is the FK anchor for every other app's
user-owned data.

### 18.3 Password reset mechanism (§14.1)

Recommended: **6-digit code + throttle, new sibling table
`PasswordResetCode`** — reuses the existing hashing/throttle helpers,
avoids widening `auth_email_verifications`'s unique constraint on an
already-shipped table.

### 18.4 `barrins_api` BFF ↔ `barrins_identity` settings contract timing

The user-ID mismatch: `barrins_api`'s own `users` table (local,
pre-cutover) and `barrins_identity`'s `users` table are not the same rows
today — this is the same gap Phase 9 (§9) exists to close. A BFF route in `barrins_api`
(`app/api/bff/ts_router/settings.py`) authenticates against
`barrins_api`'s local `CurrentUser`, whose `id` does not exist in
`barrins_identity`'s database.

| Option | Description | Verdict |
| ------ | ----------- | ------- |
| **1. Design + implement `barrins_identity`-side only now (chosen)** | Routes, schemas, tests for §14–§17 ship in `barrins_identity`. `barrins_api`'s BFF wiring to this contract is a documented, unwired follow-up for Phase 9. | Lowest risk, no dependency on the cutover timeline. |
| 2. Wire a working BFF integration now, via a `barrins_identity` service-account token | `barrins_api` would call `barrins_identity`'s settings API server-to-server on a user's behalf. | **Blocked**, not just deprioritized: this only works if `barrins_api` passes a real `barrins_identity` user UUID, which it doesn't have pre-cutover. The only way around that is a temporary ID-mapping table — throwaway complexity ahead of a cutover (§9) that makes it unnecessary. Not recommended. |

Recommended: **option 1**. This is not really a subjective trade-off
between two viable paths (option 2 is mechanically blocked today) — it's
flagged here for explicit sign-off because it means `tamiyo_scroll`'s
existing `TSUserSettings` BFF route stays exactly as it is, unmodified,
until Phase 9, which is worth confirming the user is fine waiting for.

### 18.5 Flagged, not resolved: `username` field

Constitution §13.2 mentions a `username` field; the already-implemented
`User` model (this branch) only has `email` — there is no `username`
anywhere in `barrins_identity`. This task does not add one (§5 non-goals).
Flagged here for visibility per the task's own instruction, not silently
reconciled.
