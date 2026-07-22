<!-- cSpell:ignore JWKS pyjwt respx tolaria conftest -->
# Barrin's Identity — Test Plan

> **Status**: ⬜ Proposed — **must be reviewed and confirmed by the user
> before any implementation phase in [platform.md](./platform.md) starts**
> (constitution §16.4 — tests are planned, confirmed, then implemented,
> before the missing production logic is built).
>
> §7–§11 below extend this plan to cover password reset, account
> deletion, global account settings, and per-app settings
> ([platform.md](./platform.md) §14–§17) — confirmed by the user and
> **implemented** (2026-07-22).

---

## 1. Coverage target

Same rule as the rest of the ecosystem (see
[auth_roles.md](../barrins_api/auth_roles.md#testing)): ≥ 92% overall on
`apps/barrins_identity`, 100% on `app/models/` and `app/schemas/`.

---

## 2. Test files — `apps/barrins_identity`

| Path | Covers |
| ---- | ------ |
| `tests/conftest.py` | Test DB session fixture, HTTP client, `User` / `ServiceAccount` factories |
| `tests/test_security.py` | Argon2 hash/verify/needs-rehash; JWT RS256 encode/decode, `kid`, expiry |
| `tests/test_models.py` | 100% — `User`, `UserRole.level`, `ServiceAccount` |
| `tests/test_schemas.py` | 100% — `PasswordStr`, `TokenData`, service-account schemas |
| `tests/test_routes_auth.py` | `/token`, `/refresh`, `/logout`, `/register`, `/me`, including negative cases |
| `tests/test_routes_service_accounts.py` | Create, list, revoke; `/service-token` |
| `tests/test_jwks.py` | JWKS response format; public/private key consistency |
| `tests/test_rate_limit.py` | `LOGIN_RATE_LIMIT` exceeded on `/token` → `429` |

## 3. Required negative cases

- `/token`: unknown email → `401`, response time equivalent to a wrong
  password (timing test with tolerance — same pattern `barrins_api` already
  uses for `dummy_verify`).
- `/token`: `is_active=False` → `401` after password verification (never
  before — must not reveal that a disabled account exists before the secret
  is validated).
- A `refresh`-type token presented to a route expecting `access` → `401`
  (`type` claim).
- A service-account token presented to `get_current_user` → `401`
  (`account_type` claim).
- A user token presented to `get_current_service_account` → `401`
  (symmetric case).
- Invalid `client_secret` on `/service-token` → `401`, without
  distinguishing "unknown `client_id`" from "invalid secret" in the error
  message (anti-enumeration, same principle as `/token`).
- Revoked service account (`is_active=False`, `token_version` incremented)
  → already-issued tokens rejected on next verification via
  `token_version` mismatch.
- `POST /register` without the admin role → `403`.
- `POST /service-accounts` without the admin role → `403` (even if the
  calling service account has some scope — service-account management stays
  a human administrative action).

## 4. Contract test — `apps/barrins_api`

`tests/test_identity_client_contract.py` verifies that the `identity_client/`
module copied into `barrins_api` (§4 / §9 of [platform.md](./platform.md))
stays compatible with the token format issued by `barrins-identity`,
without depending on a real running instance (mocked JWKS via `respx`):

```python
"""Verifies identity_client stays compatible with barrins-identity's token
format, using a mocked JWKS endpoint instead of a live service."""

import pytest
import respx

from cryptography.hazmat.primitives.asymmetric import rsa
from identity_client.dependencies import make_verify_dependency
from identity_client.jwks import build_cache


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048
    )
    return private_key, private_key.public_key()


@respx.mock
async def test_verify_accepts_valid_service_token(rsa_keypair):
    # Serialize the public key as JWKS, mock GET /.well-known/jwks.json
    # with respx, sign a test token with the private key, call the
    # dependency returned by make_verify_dependency(), and assert the
    # resulting VerifiedPrincipal (account_type == "service", expected
    # scopes).
    ...
```

`respx` (an `httpx` mock library) is a new test-only dependency for
`barrins_api` — add it under `[project.optional-dependencies].test`. This
test must be written in full — no `...` placeholder — before Phase 12
(Tests) in [platform.md](./platform.md) is considered done. Use
`test_jwks.py` in `barrins-identity` as the reference JWKS serialization
format.

## 5. Tolaria News integration

Once `tolaria_news` routes exist in `apps/barrins_api`
(`tests/test_routes_tolaria_*.py`), each must gain: a call without
`Authorization` → `401`; a call with an insufficiently-scoped token → `403`;
a call with a valid `tolaria:read` service token → `200` (behavior otherwise
unchanged). A `tolaria_service_token` fixture should be added to
`tests/conftest.py` for this purpose.

## 6. Manual verification commands

```bash
# barrins-identity, after the ORM/migration phase:
alembic upgrade head

# after each functional phase:
pytest tests/

# after the tests phase:
pytest --cov=app --cov-report=term-missing tests/
# threshold: >= 92% overall, 100% on app/models/ and app/schemas/

# after the JWKS phase:
curl http://localhost:8001/.well-known/jwks.json

# after the user-routes phase:
curl -X POST http://localhost:8001/api/v1/auth/token \
  -d "username=admin@example.com&password=<password>"

# after the service-accounts phase:
curl -X POST http://localhost:8001/api/v1/service-token \
  -H "Content-Type: application/json" \
  -d '{"client_id": "sa_...", "client_secret": "..."}'

# barrins_api, after the cutover:
pytest tests/  # zero regression on existing routes (db_stats, mtgjson, ml,
                # decklist)

# barrins_api, after Tolaria News securing:
curl http://localhost:8000/api/v1/tolaria/meta
# must return 401 without Authorization
```

---

## 7. New test files — lifecycle & per-app settings ([platform.md](./platform.md) §14–§17)

Same ≥92%/100% coverage bar (§1) applies; 100% on any new file under
`app/models/` and `app/schemas/`.

| Path | Covers |
| ---- | ------ |
| `tests/test_routes_password_reset.py` | `/auth/password-reset/request`, `/auth/password-reset/confirm` |
| `tests/test_routes_users.py` | `PATCH /users/me`, `DELETE /users/me`, `/users/me/email-change/verify`, `/users/me/email-change/resend` |
| `tests/test_routes_app_settings.py` | `GET`/`PUT /users/me/settings/{app_key}` |
| `tests/test_models.py` (extended) | `PasswordResetCode`, `EmailChangeRequest`, `AppSettings`, `AppKey` |
| `tests/test_schemas.py` (extended) | `AccountSettingsUpdate`, password-reset request/confirm schemas, app-settings request/response schemas |
| `tests/test_email_service.py` (extended) | `send_password_reset_code`, `send_email_change_code` on both `ConsoleEmailSender` and `SMTPEmailSender` |

## 8. Required negative cases — password reset

- `POST /auth/password-reset/request`: unknown email → same generic `202`
  as a known email (anti-enumeration — no timing/response-shape
  difference).
- `POST /auth/password-reset/request`: email of an existing but
  soft-deleted (anonymized) account → same generic `202` — the lookup by
  the original address naturally finds no row (platform.md §14.3), no
  special-casing needed; this test exists to prove that consequence
  holds, not to add a branch.
- `POST /auth/password-reset/request`: exceeding `PASSWORD_RESET_RATE_LIMIT`
  → `429`.
- `POST /auth/password-reset/confirm`: wrong code → `400`, generic
  message (does not distinguish "wrong code" from "no pending reset").
- `POST /auth/password-reset/confirm`: expired code → `400`.
- `POST /auth/password-reset/confirm`: exceeding `PASSWORD_RESET_MAX_ATTEMPTS`
  → `429`.
- `POST /auth/password-reset/confirm`: replaying an already-consumed code
  (row deleted after first successful confirm) → `400` (row no longer
  exists, same as "no pending reset").
- `POST /auth/password-reset/confirm` success → all previously-issued
  access/refresh tokens for that account rejected afterward
  (`token_version` mismatch, mirrors the existing `/auth/logout` test
  pattern) and the response includes a fresh, usable `TokenPair`.
- `new_password` failing `PasswordStr` complexity rules → `422` (same
  validator already covered for `/auth/register`/`/auth/signup`).

## 9. Required negative cases — account deletion

- `DELETE /users/me` with wrong `current_password` → `401`, account not
  modified (still `is_active=True`, `email` unchanged).
- `DELETE /users/me` without a token → `401` (standard `CurrentUser`
  dependency behavior, no new logic to test beyond wiring).
- `DELETE /users/me` success → `204`; a second call with the
  now-stale access token → `401` (already-rejected by `is_active=False`
  before the `token_version` check is even reached — assert this
  ordering, not just the end result, since platform.md §15.2 relies on
  it).
- `DELETE /users/me` success → `email` and `display_name` anonymized in
  the database row (not visible via any API response — there is no
  `GET` for a deleted user, this is a direct DB-row assertion).
- After deletion, the original email is immediately available again for
  a brand-new `POST /auth/signup` (proves the anonymization actually
  frees the unique constraint).

## 10. Required negative cases — global account settings (email change)

- `PATCH /users/me` with only `display_name` → applied immediately,
  `email` untouched, no `EmailChangeRequest` row created.
- `PATCH /users/me` with an `email` already registered to a *different*
  account → `409`, `user.email` unchanged.
- `PATCH /users/me` with a new `email`, `REQUIRE_EMAIL_VERIFICATION=true`
  → `200`, response still shows the **old** email, `EmailChangeRequest`
  row created, code sent to the **new** address only.
- `PATCH /users/me` with a new `email`, `REQUIRE_EMAIL_VERIFICATION=false`
  → `email` overwritten immediately, no `EmailChangeRequest` row, no email
  sent.
- A second `PATCH /users/me` with yet another new email before confirming
  the first → replaces the pending `EmailChangeRequest` row (same
  "resend replaces" precedent as `EmailVerification`), old pending code
  invalidated.
- `POST /users/me/email-change/verify` with wrong/expired code → `400`.
- `POST /users/me/email-change/verify` with no pending request → `404`.
- `POST /users/me/email-change/verify` when the target `new_email` was
  registered by a *different* account in the interim (race between
  request and confirm) → `409`, `user.email` unchanged, and the pending
  `EmailChangeRequest` row is deleted (the queued address is now
  permanently unusable for this request, so keeping it around just holds
  stale state — the user must `PATCH /users/me` again with a different
  address, which creates a fresh request).
- `POST /users/me/email-change/verify` success → `user.email` updated,
  `EmailChangeRequest` row deleted, existing access tokens **not**
  invalidated (email claim is informational only, platform.md §16.3).

## 11. Required negative cases — per-app settings

- `GET /users/me/settings/{app_key}` for an app_key never written →
  `200`, `{}`.
- `GET`/`PUT /users/me/settings/{app_key}` with an unknown `app_key`
  (not in the `AppKey` enum) → `404`, not `422`.
- `PUT /users/me/settings/{app_key}` with a body exceeding
  `MAX_APP_SETTINGS_BYTES` → `413`.
- `PUT /users/me/settings/{app_key}` with a non-JSON-object body (e.g. a
  bare string or array) → `422`.
- `PUT /users/me/settings/{app_key}` twice with different payloads →
  second call fully replaces the first (no field-level merge — full
  replace semantics, unlike `PATCH /users/me`).
- User A's `GET`/`PUT /users/me/settings/{app_key}` never returns or
  modifies user B's row for the same `app_key` (row scoped by
  `user_id` from `CurrentUser`, not a caller-supplied id — explicit test,
  not just an implied consequence of the dependency).
- A call to `/users/me/settings/{app_key}` with a service-account token
  instead of a user token → `401` (only `CurrentUser` is wired for now,
  platform.md §17.3 — the service-account path is documented, not
  implemented).
