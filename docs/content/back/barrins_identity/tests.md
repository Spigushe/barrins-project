<!-- cSpell:ignore JWKS pyjwt respx conftest tolaria -->
# Barrin's Identity — Test Plan

> **Status**: 🟩 On `proj/v2.0.0-bump` (T10). 313 tests, 98.72% overall,
> 100% on `app/models/` and `app/schemas/` — `uv run pytest` green, plus
> `libs/identity_client/` at 26 tests / 100%. The `barrins_api` contract
> test in §4 is still ⬜ (it belongs to the cutover). This page stays the
> plan of record for the surface in
> [Integration Contract](./integration.md).

---

## 1. Coverage target

Same bar as the rest of the ecosystem (see
[auth_roles.md](../barrins_api/auth_roles.md#testing)): **≥ 92% overall**
on `apps/barrins_identity`, **100% on `app/models/` and `app/schemas/`**.
Enforced by `pyproject.toml`'s `fail_under = 92`.

`tests/conftest.py` generates an **ephemeral RSA keypair per session**
(`tests/helpers.py`) — a real private key is never committed, even for
tests. Tests require a reachable PostgreSQL (`TEST_DATABASE_URL`, defaults
to `DATABASE_URL` + `_test`); each test runs in a transaction that is
rolled back. Autouse fixtures reset the rate limiter and pin test-safe
settings (`require_email_verification=True`, `smtp_host=None`).

---

## 2. Test files — `apps/barrins_identity/tests/`

| Path | Covers |
| --- | --- |
| `conftest.py`, `helpers.py` | DB session + HTTP client fixtures, ephemeral keypair, `User` / `ServiceAccount` factories |
| `test_config.py` | `BaseAppSettings` defaults, the RSA-key validator, `_production_requires_real_smtp_and_frontend_url` |
| `test_security.py` | Argon2 hash / verify / `needs_rehash` / `dummy_verify`; RS256 encode/decode, `kid`, `exp`, `type` / `account_type` guards; verification-code helpers |
| `test_core.py`, `test_error_handlers.py`, `test_log_config.py`, `test_types.py` | Error handlers, request-ID middleware, logging config, `JSONBCompat` |
| `test_models.py` | 100% — `User`, `UserRole.level`, `ServiceAccount`, `EmailVerification`, `PasswordResetCode`, `EmailChangeRequest`, `AppSettings`, `AppKey` |
| `test_schemas.py` | 100% — `PasswordStr`, token/claim models, service-account schemas, `AccountSettingsUpdate`, reset / app-settings schemas |
| `test_jwks.py` | JWKS response shape; public/private key consistency |
| `test_rate_limit.py` | `LOGIN_RATE_LIMIT` and `PASSWORD_RESET_RATE_LIMIT` exceeded → `429` |
| `test_dependencies.py` | `get_current_user` / `get_current_service_account` / `require_role` — the `401` vs `403` matrix |
| `test_routes_auth.py` | `/token`, `/refresh`, `/logout`, `/register`, `/me` — success + negatives |
| `test_signup.py` | `/signup`, `/signup/verify`, `/signup/resend`, both `REQUIRE_EMAIL_VERIFICATION` modes |
| `test_routes_password_reset.py` | `/auth/password-reset/request`, `/auth/password-reset/confirm` |
| `test_routes_users.py` | `PATCH`/`DELETE /users/me`, `/users/me/email-change/verify`, `/resend` |
| `test_routes_app_settings.py` | `GET`/`PUT /users/me/settings/{app_key}` |
| `test_routes_service_accounts.py` | create / list / revoke; `/service-token` |
| `test_email_service.py` | `ConsoleEmailSender` and `SMTPEmailSender`: `send_verification_code`, `send_password_reset_code`, `send_email_change_code` |

---

## 3. Negative-case matrix

### Login and tokens

- `/token`: unknown email → `401`, response time equivalent to a wrong
  password (dummy Argon2 verify — timing test with tolerance).
- `/token`: `is_active=False` → `401` **after** the password check, never
  before (must not reveal a disabled account before the secret is
  validated).
- A refresh token presented where an access token is expected → `401`
  (`type` claim).
- A service-account token presented to `get_current_user` → `401`
  (`account_type` claim); a user token to `get_current_service_account` →
  `401` (symmetric).
- `/refresh` with an expired / malformed / replayed (rotated) token →
  `401`; catches `jwt.PyJWTError` only, never a bare `Exception`.
- `/register` / `/service-accounts` without the `admin` role → `403`.
- After `/logout`, every access and refresh token issued earlier → `401`
  (`token_version` mismatch).

### Signup and email verification

- `/signup` with an existing email → `409`.
- `/signup` when the verification email fails to send → `502` and **no
  account row** (transaction rolled back).
- `/signup/verify`: wrong / expired code → `400` (one message); already
  verified → `409`; beyond `VERIFICATION_MAX_ATTEMPTS` → `429`.
- `/signup/resend`: unknown / verified / cooling-down account → the same
  generic `202`.
- `REQUIRE_EMAIL_VERIFICATION=false`: `/signup` returns
  `verification_required=false` + `tokens`, writes no `EmailVerification`
  row, sends nothing.

### Password reset

- `/password-reset/request`: unknown email, soft-deleted (anonymized)
  account, or a pending reset already → the same generic `202`; no
  timing difference.
- `/password-reset/request` over `PASSWORD_RESET_RATE_LIMIT` → `429`.
- `/password-reset/confirm`: wrong / expired / already-consumed code →
  `400` (one message); beyond `PASSWORD_RESET_MAX_ATTEMPTS` → `429`;
  `new_password` failing the complexity rule → `422`.
- `/password-reset/confirm` success → all prior tokens rejected
  afterward, and the response carries a fresh usable `TokenPair`.

### Account deletion

- `DELETE /users/me` with a wrong `current_password` → `401`, row
  unchanged.
- Success → `204`; a second call with the now-stale token → `401`
  (rejected by `is_active=False` before the `token_version` check).
- Success → `email` / `display_name` anonymized in the row (asserted at
  the DB level — there is no `GET` for a deleted user).
- The freed email is immediately reusable for a new `/signup`.

### Email change

- `PATCH /users/me` with only `display_name` → applied immediately, no
  `EmailChangeRequest` row.
- New email already on another account → `409`, `users.email` unchanged.
- New email, `REQUIRE_EMAIL_VERIFICATION=true` → `200`, response shows
  the **old** email, code sent only to the new address.
- A second `PATCH` with another new email before confirming → replaces
  the pending row, invalidates the old code.
- `/users/me/email-change/verify`: wrong/expired code → `400`; no pending
  change → `404`; beyond max attempts → `429`; address claimed in the
  interim → `409` **and** the pending row is deleted.
- `/users/me/email-change/verify` success → email updated, existing
  tokens **not** invalidated (informational claim).

### Per-app settings

- `GET` for an unwritten `app_key` → `200`, `{}`.
- `GET`/`PUT` with an `app_key` not in the allow-list → `404`, not `422`.
- `PUT` over `MAX_APP_SETTINGS_BYTES` → `413`.
- `PUT` with a non-object body (bare string / array) → `422`.
- `PUT` twice → the second fully replaces the first (no merge).
- User A's `GET`/`PUT` never returns or writes user B's row for the same
  `app_key`.
- A service-account token on `/users/me/settings/{app_key}` → `401` (only
  `CurrentUser` is wired).

### Service accounts

- `/service-token` with a wrong `client_secret` **or** an unknown
  `client_id` → `401`, one message, dummy verify on the unknown-id path.
- Revoked account (`is_active=False`, `token_version` bumped) →
  already-issued service tokens rejected on next verification.

---

## 4. Contract test — `apps/barrins_api`

`tests/test_identity_client_contract.py` (**not built** — it lands with
the cutover, [platform.md §10](./platform.md#10-cutover); the
`libs/identity_client/` package itself *is* built and independently
tested — `libs/identity_client/tests/test_client.py`, 26 tests, 100%,
`respx`-mocked JWKS + an ephemeral RSA keypair, covering valid user /
service tokens, expiry, unknown-`kid` refetch, `type` / `account_type`
mismatch, insufficient scope, cache hit/expiry, and the FastAPI
dependency's 401/403/200). The `barrins_api` contract test re-checks the
same compatibility from the consumer side once `identity_client` is wired
in:

```python
"""Verifies identity_client stays compatible with barrins-identity's token
format, using a mocked JWKS endpoint instead of a live service."""

@respx.mock
async def test_verify_accepts_valid_service_token(rsa_keypair):
    # serialize the public key as JWKS, mock GET /.well-known/jwks.json,
    # sign a token with the private key, call the dependency from
    # make_verify_dependency(), assert the VerifiedPrincipal
    # (account_type == "service", expected scopes).
    ...
```

`respx` is a new test-only dependency for `barrins_api` (add under
`[project.optional-dependencies].test`). Use `barrins-identity`'s
`test_jwks.py` as the reference JWKS serialization.

Once `tolaria_news` routes exist in `barrins_api`, each gains: a call with
no `Authorization` → `401`; an insufficiently-scoped token → `403`; a
valid `tolaria:read` service token → `200`.

---

## 5. Manual verification

```bash
cd apps/barrins_identity
uv run alembic upgrade head
uv run pytest
uv run pytest --cov=app --cov-report=term-missing   # >= 92% / 100% models,schemas

# JWKS
curl http://localhost:8001/.well-known/jwks.json

# login -> access + refresh
curl -X POST http://localhost:8001/api/v1/auth/token \
  -d "username=admin@example.com&password=<password>"

# service-token
curl -X POST http://localhost:8001/api/v1/service-token \
  -H "Content-Type: application/json" \
  -d '{"client_id": "sa_...", "client_secret": "..."}'

# signup end-to-end (staging, real SMTP) — see the deployment doc
curl -X POST http://localhost:8001/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "Sufficiently-Long-1!"}'
```

---

## See also

- [Integration Contract](./integration.md) — the endpoints these tests
  cover.
- [Platform Architecture](./platform.md) — the design behind the
  assertions.
- [Identity Deployment](../../ops/deployment/identity.md#validation) — the
  staging end-to-end email check.
