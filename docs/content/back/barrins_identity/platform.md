<!-- cSpell:ignore JWKS pyjwt slowapi argon respx cutover keypair OIDC -->
# Barrin's Identity — Platform Architecture

> **Status**: 🟩 On the `proj/v2.0.0-bump` release line (T10). The service
> in `apps/barrins_identity/` (login, refresh, logout, register, signup +
> email verification, password reset, account deletion, account settings,
> per-app settings, service accounts, JWKS) and the shared
> `libs/identity_client/` verification package are implemented and tested
> here — copied over from `feat/barrins-identity` +
> `claude/barrins-identity-lifecycle-settings-4g2lyh` rather than
> cherry-picked, then reconciled with current monorepo conventions and
> extended with the `username` handle (§7, `Q-03`).
> Still ⬜: the `barrins_api` **cutover** (§10), the
> `ops/my-server/barrins_identity.yml` playbook, and the Goblin Guide
> frontend — each a separate, later, gated phase.
>
> **App**: `apps/barrins_identity/` · **Frontend**: `apps/goblin_guide/`
> (Goblin Guide — see [Bootstrap](../../front/goblin_guide/bootstrap.md))
> · **Consumers**: `barrins_api`, then `tolaria_news` / `tamiyo_scroll`
> after the cutover (§10), plus the T9 Jupyter workbench proxy.
>
> **Supersedes** the "Future Architecture Proposal" previously on this
> page (a full OAuth 2.0 / OIDC provider, to be built only after a second
> account-based app existed). See [ADR-16](../../ops/architecture/decisions.md#adr-16-adopt-barrins-identity-as-the-rs256-jwks-authority).

This page is the *design and rationale* reference. The consumer-facing
wire contract (every endpoint, request/response shape, error codes, the
JWKS verification flow) lives in the
[Integration Contract](./integration.md); the test plan lives in
[Test Plan](./tests.md).

---

## 1. Purpose

Extract authentication out of `barrins_api`
(`app/models/user.py`, `app/core/security.py`, `app/dependencies/auth.py`,
`app/api/v1/routers/auth.py` — see
[JWT Authentication & Roles](../barrins_api/auth_roles.md)) into its own
app, so that `barrins_api`, `tolaria_news`, `tamiyo_scroll` and the T9
Jupyter workbench can share one Barrin's account (constitution §13.1)
without distributing a shared signing secret.

`barrins-identity` is the only app that holds a signing private key and
the only one that ever touches a plaintext password.

---

## 2. Why now

The prior page proposed a full OIDC provider, to be built only once a
second account-based application existed, and recommended **not** building
it yet — the same call [ADR-7](../../ops/architecture/decisions.md#adr-7-delay-barrins-identity-keep-identity-on-barrins_api)
recorded (2026-07-25).

Two things changed. The repo split that plan assumed was consolidated
into this monorepo — `apps/barrins_identity/`, `apps/tolaria_news/`,
`apps/tamiyo_scroll/` and `apps/goblin_guide/` now all exist as app
directories. And **T9** (the Karn Tablets Jupyter Lab workbench,
`karn-jupyter.barrins-codex.org`) needs `admin`/`ml_developer`-only
access enforced by a live role check — its sub-decision 1
(`docs/project/v2.0.0-bump/t9-karn-jupyter-workbench/`) resolves to a
check against `barrins_identity`, which is exactly the
"second real consumer" ADR-7 was waiting for. ADR-16 records the delay
condition firing.

The new decision: build `barrins-identity` as a **JWT RS256 + JWKS**
service — one shared human login flow plus a `client_credentials`-style
machine-to-machine flow. Not a full OIDC provider: no authorization-code
flow, no third-party client registration.

---

## 3. RS256 and JWKS

| Option | Mechanism | Verdict |
| --- | --- | --- |
| **RS256 (chosen)** | `barrins-identity` signs with an RSA private key; consumers verify with the public key served at `/.well-known/jwks.json` | No shared secret; key rotation via `kid` without a coordinated redeploy of every consumer; verification is fully local (no network call per request) |
| HS256 shared secret | The same symmetric secret on every consumer | Rejected — any consumer that can verify can also forge; rotation needs a synchronized redeploy of every service |

The RSA private key is parsed and the public key derived **once**, at
module load (`app/core/security.py`) — never per token decode or per JWKS
request. `BaseAppSettings.jwt_private_key_must_be_a_valid_rsa_key` rejects
a malformed or non-RSA `JWT_PRIVATE_KEY` at startup, not at first token
issuance.

Argon2id (via `argon2-cffi`) hashes both user passwords and
service-account client secrets, with cost parameters from settings
(`ARGON2_MEMORY_COST_KIB` / `_TIME_COST` / `_PARALLELISM`, default
`65536` / `3` / `4`, RFC 9106 low-memory) rather than library defaults so
they are documented and tunable per environment.

---

## 4. Revocation model

Access tokens carry a short TTL (10 min) and are verified locally
(signature + `exp` + `type` / `account_type` claim only — no database
lookup). `token_version` (`tkv` claim) is checked only at `/auth/refresh`,
`/auth/logout`, and inside the auth dependencies (`get_current_user`,
`get_current_service_account`). `POST /auth/logout` and
`POST /service-accounts/{client_id}/revoke` each increment
`token_version`, which invalidates every outstanding token for that
principal on its next verification.

Consequence: revoking a compromised account takes up to one access-token
TTL (10 min) to take effect on already-issued access tokens. Rejected
alternative — consumers calling an `/introspect` route on every request —
recreates the hard synchronous coupling JWKS exists to avoid.

> Open item (non-blocking): if instant revocation becomes a real product
> need (an admin ban), add a short-cache revocation-list endpoint
> (`GET /revocations?since=`). Not built — a 10-minute window is judged
> sufficient for current scope.

---

## 5. Target architecture

```text
barrins-identity  (apps/barrins_identity/, own process, own database)
  DB: users, service_accounts, auth_email_verifications,
      auth_password_reset_codes, auth_email_change_requests, app_settings
  |
  |-- JWKS (public key, cached ~1h) --------> every consumer
  |                                            (verifies locally)
  |-- access / refresh (human login) -------> barrins_api, goblin_guide,
  |                                            later tamiyo_scroll
  |-- service-token (client_credentials) ---> barrins_api, T9 Jupyter proxy
  |-- account lifecycle (signup, reset, ----> goblin_guide
  |   settings, delete)
```

Network calls to `barrins-identity` happen only at: human login, refresh,
periodic JWKS refresh, service-token issuance, and the account-lifecycle
actions. Every protected request elsewhere is verified against the cached
public key with no call back here.

---

## 6. Roles

`UserRole` (`app/models/user.py`) is a `StrEnum` ranked by an ordinal
`level`; `require_role()` compares levels, never names.

| Role | `level` | Notes |
| --- | --- | --- |
| `user` | 1 | Base authenticated account |
| `moderator` | 2 | The renamed `role_c` placeholder from `barrins_api`'s `UserRole` — a clean-slate rename on this new schema |
| `ml_developer` | 3 | Machine Learning Developer — the T9 Jupyter access floor |
| `admin` | 4 | Everything, including user and service-account management |

Dependency aliases (`app/dependencies/auth.py`): `CurrentUser`,
`ModeratorUser`, `MLDevUser`, `AdminUser`, `CurrentServiceAccount`. A
service-account token presented to a user route (or vice versa) is
rejected via the `account_type` claim before any role check.

Until the cutover (§10), `barrins_api` keeps its own `UserRole` with
`role_c` at level 2; the rename only lands here.

---

## 7. Data model

SQLAlchemy 2.x (`Mapped[...]` / `mapped_column`), PostgreSQL (`asyncpg`
at runtime, `psycopg2` for Alembic). `app/models/_types.py` provides
`JSONBCompat` (JSONB on Postgres, JSON elsewhere), copied from
`barrins_api`. Migrations are hand-written and chained linearly:
`a1b2c3d4e5f6` (users + service_accounts) → `b2c3d4e5f6a7`
(email_verifications) → `c3d4e5f6a7b8` (password_reset_codes) →
`d4e5f6a7b8c9` (email_change_requests) → `e5f6a7b8c9d0` (app_settings).

### `users`

| Column | Type | Constraint | Description |
| --- | --- | --- | --- |
| `id` | `UUID` | PK, `default uuid4` | |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL, INDEX | Login identifier |
| `username` | `VARCHAR(64)` | UNIQUE, NOT NULL, INDEX | Unique public handle (§13.2, [ADR-17](../../ops/architecture/decisions.md#adr-17-shared-code-lives-in-a-top-level-libs-directory)). Added on T10 by migration `f6a7b8c9d0e1`; required in `UserSignup` / `UserCreate` and echoed in `UserRead`. Input rule `^[A-Za-z0-9_-]{3,32}$` (`schemas.auth.USERNAME_PATTERN`); the column is wider so a soft-deleted row can be anonymized to `deleted-<uuid>`. Login still authenticates by `email` — `Q-05` |
| `hashed_password` | `VARCHAR(255)` | NOT NULL | Argon2id hash (`"!"` for a soft-deleted account — never a valid hash) |
| `role` | `ENUM userrole` | NOT NULL, server default `user` | |
| `is_active` | `BOOLEAN` | NOT NULL, server default `true` | Deactivation without deletion; also the soft-delete flag |
| `is_verified` | `BOOLEAN` | NOT NULL, server default `false` | Email verified |
| `display_name` | `VARCHAR(100)` | NULLABLE | |
| `token_version` | `INTEGER` | NOT NULL, server default `0` | `tkv` claim — instant revocation |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | NOT NULL | |

### `service_accounts`

| Column | Type | Constraint | Description |
| --- | --- | --- | --- |
| `id` | `UUID` | PK | |
| `client_id` | `VARCHAR(64)` | UNIQUE, NOT NULL, INDEX | `sa_<16 hex>` |
| `hashed_client_secret` | `VARCHAR(255)` | NOT NULL | Argon2id — plaintext returned once at creation |
| `description` | `VARCHAR(255)` | NULLABLE | |
| `scopes` | `JSONBCompat` | NOT NULL, default `[]` | `list[str]` |
| `is_active` | `BOOLEAN` | NOT NULL, server default `true` | |
| `token_version` | `INTEGER` | NOT NULL, server default `0` | |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | NOT NULL | |

### `auth_email_verifications`, `auth_password_reset_codes`, `auth_email_change_requests`

Three sibling tables, one active row per user
(`user_id` FK → `users.id` `ON DELETE CASCADE`, `UNIQUE`), each holding a
hashed short-lived code:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID` | PK |
| `user_id` | `UUID` | FK CASCADE, **UNIQUE** — a resend replaces the row |
| `code_hash` | `VARCHAR(64)` | `sha256(f"{code}:{user_id}")` — bound to the user, not a purpose |
| `expires_at` | `TIMESTAMPTZ` | |
| `attempts` | `INTEGER` | default `0` — invalidated past the max |
| `last_sent_at` | `TIMESTAMPTZ` | resend-cooldown anchor |
| `created_at` | `TIMESTAMPTZ` | |

`auth_email_change_requests` adds one column, `new_email VARCHAR(255)` —
the address awaiting confirmation. Three tables rather than a `purpose`
discriminator on `auth_email_verifications`: that table shipped first, and
widening its unique constraint would touch a live schema for no
functional gain (§9).

### `app_settings`

| Column | Type | Constraint | Description |
| --- | --- | --- | --- |
| `id` | `UUID` | PK | |
| `user_id` | `UUID` | FK → `users.id` CASCADE | |
| `app_key` | `VARCHAR(64)` | | Plain string, **not** a Postgres `ENUM` — an API-level allow-list (`AppKey`: `tamiyo_scroll`, `tolaria_news`), so a new app needs no `ALTER TYPE` migration |
| `data` | `JSONBCompat` | NOT NULL, default `{}` | Opaque per-app blob |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | NOT NULL | |
| — | | `UNIQUE(user_id, app_key)` | |

---

## 8. Configuration

`app/config/base.py` (`BaseAppSettings`, `pydantic-settings`,
`env_file=".env"`, `case_sensitive=False`, `extra="ignore"`). The
annotated template is `apps/barrins_identity/.env.example`; the deployment
secrets file is `ops/my-server/secrets/barrins_identity/{production,staging}.env`
(git-ignored — constitution §34, [ADR-1](../../ops/architecture/decisions.md#adr-1-secrets-must-never-be-committed-even-encrypted)).

| Variable | Default | Notes |
| --- | --- | --- |
| `DATABASE_URL` | *required* | `PostgresDsn`; own database, never shared. `database_url_sync` (asyncpg → psycopg2) is computed for Alembic |
| `DATABASE_ECHO` | `false` | |
| `JWT_PRIVATE_KEY` | *required* | `SecretStr`, RSA PEM; validated at startup |
| `JWT_KID` | `2026-08` | Current signing key id (rotation) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `SERVICE_TOKEN_EXPIRE_MINUTES` | `15` | |
| `ARGON2_MEMORY_COST_KIB` / `_TIME_COST` / `_PARALLELISM` | `65536` / `3` / `4` | |
| `LOGIN_RATE_LIMIT` | `5/minute` | `slowapi` spec, per IP, on `POST /auth/token` |
| `ALLOWED_ORIGINS` | *required* | `list[str]`, no wildcard (constitution §33) |
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` |
| `DEBUG` | `false` | |
| `REQUIRE_EMAIL_VERIFICATION` | `true` | **Production must run `true`** ([ADR-3](../../ops/architecture/decisions.md#adr-3-production-email-uses-a-transactional-provider-not-self-hosted), ADR-16). `false` makes `/auth/signup` and the email-change flow apply immediately with no code — a dev/staging-only fallback, never the resting prod state |
| `SMTP_HOST` | *(empty)* | Empty ⇒ `ConsoleEmailSender` (logs the code). Required in production while `REQUIRE_EMAIL_VERIFICATION=true` |
| `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_USE_TLS` | `587` / — / — (`SecretStr`) / `true` | STARTTLS |
| `SMTP_FROM_ADDRESS` | `barrins-identity@gmail.com` | **Production value: `identity@barrins-codex.org`** via Brevo (ADR-3) |
| `VERIFICATION_CODE_TTL_MINUTES` / `_MAX_ATTEMPTS` / `_RESEND_COOLDOWN_SECONDS` | `15` / `5` / `60` | Reused by the email-change flow too |
| `FRONTEND_BASE_URL` | `http://localhost:5173` | Builds `{FRONTEND_BASE_URL}/verify-email` etc.; must differ from the default in production |
| `PASSWORD_RESET_CODE_TTL_MINUTES` / `_MAX_ATTEMPTS` / `_RESEND_COOLDOWN_SECONDS` / `_RATE_LIMIT` | `15` / `5` / `60` / `5/minute` | |
| `MAX_APP_SETTINGS_BYTES` | `16384` | 16 KiB cap on a per-app settings blob → `413` |
| `LOG_*` | see `.env.example` | Rotating file + console logging |

Two production guards fail the process at startup rather than later:
`jwt_private_key_must_be_a_valid_rsa_key` (the key must be a valid PEM RSA
private key) and `_production_requires_real_smtp_and_frontend_url` (in
production with `REQUIRE_EMAIL_VERIFICATION=true`, `SMTP_HOST` must be set
and `FRONTEND_BASE_URL` must not be the localhost default).

Consumers (`barrins_api`, later the others) read a small separate set —
`IDENTITY_SERVICE_URL`, `IDENTITY_JWKS_CACHE_TTL_SECONDS` (default
`3600`), `IDENTITY_SERVICE_CLIENT_ID` / `_SECRET` — see the
[Integration Contract §6](./integration.md#6-consumer-configuration).

---

## 9. Account lifecycle design

The rationale for each flow; the wire contract is
[Integration Contract §4](./integration.md#4-endpoint-contract).

**Self-registration + email verification.** `POST /auth/signup` writes an
unverified `User` + an `EmailVerification` row (6-digit code, hashed) and
emails the code; a send failure rolls the transaction back and returns
`502` (no orphan account). `POST /auth/signup/verify` sets
`is_verified=True`, deletes the row, and returns a token pair (auto-login).
`REQUIRE_EMAIL_VERIFICATION=false` skips all of that and returns tokens
straight from `/auth/signup`.

**Password reset.** Chosen: a 6-digit code + throttle against a **new
sibling table** `PasswordResetCode`, reusing the exact
`generate_verification_code` / `hash_verification_code` /
`verify_verification_code` helpers and the attempts/cooldown semantics
already built for signup. Rejected: a signed-JWT reset link (a second
"prove you own this inbox" pattern) and a `purpose` column on the
already-shipped `auth_email_verifications` (touches a live unique
constraint for no functional gain). `/auth/password-reset/confirm` sets
the new password, **bumps `token_version`** (a reset implies "assume the
account was compromised"), deletes the code row, and returns a fresh token
pair. There is no `REQUIRE_EMAIL_VERIFICATION` bypass for reset — it is
the one flow where the requester has no other credential to fall back on.

**Account deletion.** Chosen: **soft delete** — `is_active=False`,
`token_version += 1`, `email` / `username` / `display_name` anonymized
(`email = f"deleted-{id}@barrins.invalid"`, `username = f"deleted-{id}"`,
`display_name = None`), `hashed_password = "!"`. `barrins_identity` is the
FK anchor for every other app's user-owned data; a hard delete would
orphan those rows or force every consumer to carry a "deleted user"
sentinel from day one. Anonymizing frees the original email **and
username** for reuse without destroying the anchor. `DELETE /users/me`
re-authenticates with the current password in the body (stronger than a
token-freshness check, and reuses `verify_password`). Cascading cleanup
of **app-owned** data is each consumer's responsibility (constitution
§4.1) — identity never reaches into another app's database.

**Global account settings.** `GET /auth/me` stays the read endpoint; a
new `/users` router owns account-resource mutation (`PATCH /users/me`,
`DELETE /users/me`, `GET`/`PUT /users/me/settings/{app_key}`) — a
route-surface split on the same `User` row, not duplicated logic.
`display_name` changes apply immediately. A new `email` is applied
immediately only when `REQUIRE_EMAIL_VERIFICATION=false`; otherwise an
`EmailChangeRequest` row is written, a code is sent to the **new**
address, and `users.email` (the old address) stays authoritative until
`POST /users/me/email-change/verify` confirms. The `email` claim inside
already-issued access tokens is **not** force-invalidated on change — it
is informational, never used for authorization (§4).

**Per-app settings.** Chosen: an **opaque JSON blob** per
`(user_id, app_key)`, stored and served verbatim, validated only for
overall size (`MAX_APP_SETTINGS_BYTES` → `413`, checked in the handler so
it is a `413` and not Pydantic's `422`). Each consuming app owns its own
schema for the contents. `app_key` is an API-level allow-list (`404` on
an unknown key, deliberately not `422`). A `GET` never creates a row;
`PUT` is a full replace/upsert.

---

## 10. Cutover

**Not done** — the one deliberately deferred phase. `libs/identity_client/`
now exists (built on T10, not yet imported anywhere), so the cutover is
the set of `apps/barrins_api` changes below (one-time, not incremental):

| Action | Files |
| --- | --- |
| Create | `scripts/migrate_users_to_identity.py` — copies `users` rows into `barrins-identity`'s database inside a single transaction (`target_engine.begin()`, not `.connect()`, so a mid-loop failure rolls back fully) |
| Wire in | `libs/identity_client/` — already built (JWKS fetch + cache + `make_verify_dependency`, one shared package per [ADR-17](../../ops/architecture/decisions.md#adr-17-shared-code-lives-in-a-top-level-libs-directory)); the cutover adds it as a `[tool.uv.sources]` path dep and consumes it |
| Replace | `app/dependencies/auth.py` — verifies via `libs/identity_client`, no local DB user lookup |
| Delete | `app/models/user.py`, `app/schemas/auth.py`, `app/core/security.py`, `app/api/v1/routers/auth.py`, `scripts/create_admin.py` (all now live here) |
| Create | An Alembic migration dropping the local `users` table |
| Modify | `app/config/base.py` — drop local JWT/Argon2 fields, add `identity_service_url`, `identity_jwks_cache_ttl_seconds` |
| Modify | `pyproject.toml` — drop `python-jose`, `argon2-cffi`; add `pyjwt`, `respx` (test-only), `identity_client` path dep |

Highest-risk phase (live data cutover). Never run against production data
without a user-confirmed maintenance window; in dev/CI it can run against
two test databases with no extra confirmation.

---

## 11. Open questions

| # | Item | Status |
| --- | --- | --- |
| `Q-01` | `identity_client` packaging | **Resolved & built** (T10) — `libs/identity_client/` shared Python package (`JWKSCache` + `verify_token` + `make_verify_dependency`), 100% test coverage, not imported by any consumer until the cutover |
| `Q-02` | `apps/tolaria_news` scope and timeline — its routes must depend on a `barrins-identity` service-token scope from their first commit | Open — blocked on the Tolaria News frontend spec, not on this service |
| `Q-03` | `username` field — constitution §13.2 requires a unique `username` | **Resolved & built** (T10) — `username` `VARCHAR(64)` UNIQUE NOT NULL INDEX on `users` (migration `f6a7b8c9d0e1`); required in `UserSignup` / `UserCreate`, echoed in `UserRead`, threaded through `/auth/signup`, `/auth/register` and `create_admin.py`; anonymized on soft-delete |
| `Q-04` | T9 sub-decision 1 (auth-enforcement fork) | **Resolved** — option (b), a live role check against `barrins_identity`; recorded in the T9 tracker (2026-08-29) |
| `Q-05` | Login credential — accept `username`, `email`, or both on `POST /auth/token`? | **Open (deferred)**. T10 kept `email` as the sole credential: the OAuth2 form field named `username` carries the email, unchanged, for Swagger / `OAuth2PasswordBearer` compatibility. Accepting the real handle as a login is a later, separate change |

---

## 12. Quality notes carried over

Corrections already reflected here — do not reintroduce:

- `/auth/token` uses `OAuth2PasswordRequestForm` (the form's `username`
  field carries the email today — see `Q-05` for once a real `username`
  column exists), not raw parameters — needed for the Swagger Authorize
  button and `OAuth2PasswordBearer` compatibility.
- The RSA public key is derived once at module load, not per decode / per
  JWKS request.
- The user-migration script uses `target_engine.begin()` for atomicity.
- `/auth/refresh` catches `jwt.PyJWTError` specifically, never a bare
  `Exception`.
- A future Tolaria News scope dependency is passed as the dependency
  function itself, never as a string.

---

## See also

- [Integration Contract](./integration.md) — the consumer-facing wire
  contract.
- [Test Plan](./tests.md) — coverage target and negative-case matrix.
- [Identity Deployment](../../ops/deployment/identity.md) — playbook
  shape, and the mandatory Brevo / OVH email setup.
- [JWT Authentication & Roles](../barrins_api/auth_roles.md) — the
  `barrins_api` auth this extracts.
- [Goblin Guide — Bootstrap](../../front/goblin_guide/bootstrap.md) — the
  frontend counterpart.
- [ADR-16](../../ops/architecture/decisions.md#adr-16-adopt-barrins-identity-as-the-rs256-jwks-authority),
  [ADR-7](../../ops/architecture/decisions.md#adr-7-delay-barrins-identity-keep-identity-on-barrins_api),
  [ADR-3](../../ops/architecture/decisions.md#adr-3-production-email-uses-a-transactional-provider-not-self-hosted).
