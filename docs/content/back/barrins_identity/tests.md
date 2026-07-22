<!-- cSpell:ignore JWKS pyjwt respx tolaria conftest -->
# Barrin's Identity — Test Plan

> **Status**: ⬜ Proposed — **must be reviewed and confirmed by the user
> before any implementation phase in [platform.md](./platform.md) starts**
> (constitution §16.4 — tests are planned, confirmed, then implemented,
> before the missing production logic is built).

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
