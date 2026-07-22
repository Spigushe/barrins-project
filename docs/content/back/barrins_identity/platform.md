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
