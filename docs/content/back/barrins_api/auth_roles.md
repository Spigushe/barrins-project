# JWT Authentication & Role-Based Access Control

> **Target**: [`barrins-project/barrins_api`](https://github.com/barrins-project/barrins_api)
> **Initial date**: 2026-04-27
> **Status**: ✅ Implemented — replaces the ad hoc `X-Admin-Key` header with
> full JWT authentication and hierarchical role-based authorization.

---

## Objective

Secure the API by replacing the `X-Admin-Key` mechanism with a complete JWT
authentication system backed by hierarchical roles. At the end of this
implementation, the API:

1. Issues and validates signed JWTs (HS256).
2. Identifies every request with an authenticated user, or rejects it.
3. Applies five hierarchical access levels to every endpoint.
4. Exposes standard authentication routes (`/auth/token`, `/auth/refresh`,
   `/auth/logout`, `/auth/register`, `/auth/me`).
5. Replaces `_require_admin_key` in `routers/mtgjson.py` with a role-based
   dependency.
6. Supports refresh tokens and instant revocation — required before opening
   the API to the frontend, since non-persistent sessions are a blocking UX
   issue.

---

## Role hierarchy

| Level | Role | Description | Access |
| ----- | ---- | ------------ | ------ |
| 0 | `anonymous` | Not authenticated | Public reads (sets, cards) |
| 1 | `user` | Base authenticated account | Public reads + personal profile |
| 2 | `role_c` 🔲 | Placeholder — final name and scope not yet decided | TBD |
| 3 | `ml_developer` | Machine learning developer | TBD |
| 4 | `admin` | Administrator | Everything, including MTGJSON import and user management |

Hierarchy: `admin` ⊃ `ml_developer` ⊃ `role_c` ⊃ `user` ⊃ `anonymous`. A role
of level *N* always satisfies a `require_role` constraint of level < *N* — the
`require_role()` factory compares ordinal levels, never role names, so a
future rename of `role_c` only requires updating one mapping.

The `anonymous` level is not stored in the database — it represents the
absence of a token and corresponds to endpoints that declare no
authentication dependency at all.

---

## Security matrix

| Method | Endpoint | Required role | Note |
| ------ | -------- | -------------- | ---- |
| `GET` | `/sets/`, `/sets/{code}`, `/sets/{code}/cards` | anonymous | Public |
| `GET` | `/cards/{uuid}`, `/cards/{uuid}/prices`, `/cards/by-name/{name}` | anonymous | Public |
| `GET` | `/mtgjson/status` | anonymous | Public |
| `POST` | `/mtgjson/import` | **admin** | Replaces `X-Admin-Key` |
| `POST` | `/auth/token` | anonymous | Login — returns `access_token` + `refresh_token` |
| `POST` | `/auth/refresh` | anonymous | Exchanges a refresh token for a new pair |
| `POST` | `/auth/logout` | **user** | Instantly revokes all of the caller's tokens |
| `POST` | `/auth/register` | **admin** | Account creation by an administrator |
| `GET` | `/auth/me` | **user** | Current user's profile |
| `POST` | `/auth/signup` | anonymous | ⏳ Not registered yet — see "Self-registration" below |

---

## Target architecture

```text
POST /auth/token (login)
        |
        v
verify_password + dummy_verify (timing-safe) --> User
        |
        v
claims = {sub, role, email, tkv}
        |
        +--> create_access_token()  (30 min, type=access)
        +--> create_refresh_token() (7 days, type=refresh)
                |
                v
          TokenPair { access_token, refresh_token }

Every protected request
        |
        v
  get_current_user(token)
    - decode_access_token() -> JWTError => 401
    - user missing / inactive          => 401
    - user.token_version != token.tkv  => 401 (revoked)
        |
        v
  require_role(*roles) -> 403 if role not in allowed set

POST /auth/refresh {refresh_token}
        |
        v
  decode_refresh_token() -> validate type + tkv -> new TokenPair (rotation)

POST /auth/logout
        |
        v
  user.token_version += 1  --> every access/refresh token in circulation
                                is immediately rejected
```

---

## Configuration

Fields on `BaseAppSettings` (`app/config/base.py`):

| Field | Default | Description |
| ----- | ------- | ----------- |
| `secret_key` | `"CHANGE_ME_GENERATE_WITH_OPENSSL"` | HS256 signing key |
| `algorithm` | `"HS256"` | JWT signing algorithm (kept configurable rather than hard-coded) |
| `access_token_expire_minutes` | `30` | Access token lifetime |
| `refresh_token_expire_days` | `7` | Refresh token lifetime (`ge=1, le=90`) |

A `model_validator` (the same pattern already used for `admin_api_key`)
raises a startup error if `environment == "production"` and `secret_key`
still holds its default placeholder value.

---

## Data model

### `UserRole` enum

```python
class UserRole(str, enum.Enum):
    """User roles ordered by increasing access level.

    The ordinal value (`level`) is used by require_role() for hierarchical
    comparisons — role names are never compared directly.
    """

    user = "user"            # level 1
    role_c = "role_c"        # level 2 — 🔲 placeholder, final name TBD
    ml_developer = "ml_developer"  # level 3
    admin = "admin"          # level 4

    @property
    def level(self) -> int:
        return {
            UserRole.user: 1,
            UserRole.role_c: 2,
            UserRole.ml_developer: 3,
            UserRole.admin: 4,
        }[self]
```

### `User` (`app/models/user.py`)

| Column | SQL type | Constraint | Description |
| ------ | -------- | ---------- | ----------- |
| `id` | `UUID` | PK | From `IDUuidMixin` |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL, INDEX | Login identifier |
| `hashed_password` | `VARCHAR(255)` | NOT NULL | Argon2id hash |
| `role` | `ENUM('user','role_c','ml_developer','admin')` | NOT NULL, DEFAULT `user` | Access level (🔲 `role_c` provisional) |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `true` | Deactivation without deletion |
| `is_verified` | `BOOLEAN` | NOT NULL, DEFAULT `false` | Verified account (email or manual) |
| `display_name` | `VARCHAR(100)` | NULLABLE | Optional display name |
| `token_version` | `INTEGER` | NOT NULL, DEFAULT `0` | Instant revocation of all tokens — see "Refresh tokens & revocation" below |
| `created_at` / `updated_at` | `TIMESTAMP` | NOT NULL | From `TimestampMixin` |

### Database migration

The generated Alembic migration creates the `users` table and the
`userrole` PostgreSQL enum type. Two details matter for correctness:

- **Idempotent enum creation/drop**: the enum type is built through a shared
  `_userrole_type()` helper, reused in both `upgrade()` and `downgrade()`,
  and created with `checkfirst=True`. `op.execute("CREATE TYPE ...")`
  followed by a `downgrade` + `upgrade` cycle otherwise raises
  `DuplicateObject: type "userrole" already exists`, since `op.drop_table`
  does not implicitly drop the enum type — and `sa.Enum(name=...)` without
  its values is ambiguous on SQLAlchemy 2.x when used to build the `DROP`.
- **`server_default` on `role` and `token_version`**: required so that a
  future `ALTER TABLE ADD COLUMN` on a populated table doesn't fail with a
  `NOT NULL` violation.
- SQLite (used in tests) has no native enum type — SQLAlchemy substitutes a
  `VARCHAR` + `CHECK` constraint, and the `.create()`/`.drop()` calls on the
  enum type become no-ops there.

### Bootstrapping the first admin account

`POST /auth/register` is itself protected by the `admin` role, so the first
account must be created outside the API. `scripts/create_admin.py` seeds one
admin account, prompting for the password interactively via `getpass` so it
never appears in shell history or process logs:

```bash
python scripts/create_admin.py --email admin@example.com --display-name "Alice"
```

---

## Pydantic schemas (`app/schemas/auth.py`)

### Password validation

Pydantic v2's validation engine (the Rust `regex` crate) doesn't support
look-around assertions, so `Field(pattern=...)` can only describe the rule
for the OpenAPI schema — actual enforcement goes through an
`AfterValidator`. The check is factored into a single reusable
`PasswordStr` annotated type shared by every schema that accepts a
password, so the rule only exists in one place and produces one consistent
error message rather than two (a `Field(min_length=...)` mismatch and a
validator mismatch reporting differently):

```python
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])"      # >= 1 lowercase
    r"(?=.*[A-Z])"       # >= 1 uppercase
    r"(?=.*\d)"          # >= 1 digit
    r"(?=.*[^\w\s])"     # >= 1 symbol (`_` excluded — included in \w)
    r".{12,}$"
)
PASSWORD_RULE = (
    "At least 12 characters with 1 uppercase, 1 lowercase, "
    "1 digit and 1 symbol."
)

PasswordStr = Annotated[
    str,
    Field(json_schema_extra={
        "pattern": PASSWORD_PATTERN.pattern,
        "description": PASSWORD_RULE,
    }),
    AfterValidator(_check_password_complexity),
]
```

`PASSWORD_PATTERN` is the single source of truth for both backend and
frontend: the frontend can read it straight from `GET /openapi.json`
(`components.schemas.UserCreate.properties.password.pattern`) instead of
re-implementing the rule.

### Schemas

| Schema | Purpose | Notable constraint |
| ------ | ------- | ------------------- |
| `UserCreate` | Admin-only account creation payload (exposes `role`, `is_verified`) | `extra="forbid"` |
| `UserSignup` | Restricted self-registration payload (no `role`, no `is_verified`) | `extra="forbid"` |
| `UserRead` | Public user representation (no password) | `from_attributes=True` |
| `TokenPair` | Response of `/auth/token` and `/auth/refresh` | `access_token` + `refresh_token` + `token_type` |
| `RefreshRequest` | Body of `/auth/refresh` | `refresh_token` |
| `TokenData` | Decoded JWT payload | `sub`, `role`, `email`, `token_version` |

Both `UserCreate` and `UserSignup` set `model_config = ConfigDict(extra="forbid")`
as defense in depth: by default Pydantic v2 silently ignores unknown fields,
so a request body like `{"email": ..., "password": ..., "role": "admin"}`
sent to `UserSignup` would otherwise be accepted without any trace of the
escalation attempt. With `extra="forbid"` it raises an explicit, loggable
`422`.

---

## Security utilities (`app/core/security.py`)

### Password hashing — Argon2id

Password hashing uses `argon2-cffi` directly rather than `passlib`:
`passlib` 1.7.4 imports `from crypt import crypt`, and the `crypt` stdlib
module was removed in Python 3.13, which crashes at import time.
`argon2-cffi` was already a project dependency and needed no wrapper.

```python
_hasher = PasswordHasher()  # RFC 9106 LOW_MEMORY: 64 MiB, time_cost=3, parallelism=4

def hash_password(plain: str) -> str:
    return _hasher.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Never raises — returns False for any invalid or malformed hash."""
    try:
        return _hasher.verify(hashed, plain)  # order: (hashed, plain)
    except (VerificationError, InvalidHashError):
        return False
```

A corrupted or malformed hash in the database must produce `401`, not an
unhandled `500` — hence the narrow `except` clause. It intentionally
catches only the argon2 exceptions that verification can raise, not a bare
`Exception`, so that unrelated failures (`MemoryError`,
`KeyboardInterrupt`, …) are not silently swallowed.

### Timing-safe login

A precomputed dummy hash lets the login handler perform a wasted Argon2
verification when the email is unknown, so an unknown-email response takes
the same time as a wrong-password response (~300 ms either way, dominated
by the Argon2 cost):

```python
_DUMMY_HASH: str = _hasher.hash("dummy_value_for_timing_equalization")

def dummy_verify(plain: str) -> None:
    try:
        _hasher.verify(_DUMMY_HASH, plain)
    except (VerificationError, InvalidHashError):
        pass
```

All three failure branches of `POST /auth/token` — unknown email, wrong
password, inactive account — return the *same* `401` with the *same*
message (`"Invalid credentials."`). `verify_password` always runs before
the `is_active` check, even though the check is cheap, specifically so a
deactivated account cannot be distinguished from a wrong password by
response time; an earlier draft returned a `403 "Account disabled."` on
that branch, which would have confirmed to an attacker that the email and
password were both correct.

### JWT tokens (HS256, `python-jose`)

Access and refresh tokens share the same claim shape and signing key, and
are distinguished only by a `type` claim, which is checked on decode so a
refresh token can never be used where an access token is expected (or vice
versa):

| Claim | Value | Present in |
| ----- | ----- | ---------- |
| `sub` | User UUID (string) | access + refresh |
| `role` | e.g. `"admin"` | access + refresh |
| `email` | User email | access + refresh |
| `tkv` | `token_version` (int) — see revocation below | access + refresh |
| `type` | `"access"` or `"refresh"` | access + refresh |
| `exp` | UTC expiry timestamp | access + refresh |

The payload is encoded, not encrypted — no sensitive data (password, PII)
belongs in it beyond what's listed above.

---

## FastAPI dependencies (`app/dependencies/auth.py`)

```python
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: DatabaseSession,
) -> User:
    """401 if the token is missing/malformed/expired/wrong-type, the user no
    longer exists, the account is inactive, or token_version doesn't match
    (i.e. the token was revoked)."""
    ...

def require_role(*roles: UserRole):
    """Dependency factory: the current user's role must be one of `roles`."""
    async def _check(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
        return current_user
    return _check

CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_role(UserRole.admin))]
```

| Alias | Minimum level | Accepted roles | Failure |
| ----- | -------------- | --------------- | ------- |
| `CurrentUser` | 1 (`user`) | `user`, `role_c` 🔲, `ml_developer`, `admin` | `401` if unauthenticated |
| `RoleCUser` | 2 (`role_c` 🔲) | `role_c`, `ml_developer`, `admin` | `403` |
| `MlDeveloperUser` | 3 (`ml_developer`) | `ml_developer`, `admin` | `403` |
| `AdminUser` | 4 (`admin`) | `admin` | `403` |

Public (`anonymous`) endpoints simply declare none of these dependencies.
When `role_c` receives its final name, only the `RoleCUser` alias and its
callers need updating — the underlying comparison is ordinal.

---

## Authentication routes (`app/api/v1/routers/auth.py`)

| Method | Path | Access | Body / params |
| ------ | ---- | ------ | -------------- |
| `POST` | `/api/v1/auth/token` | anonymous | Form: `username`, `password` |
| `POST` | `/api/v1/auth/refresh` | anonymous | JSON: `RefreshRequest` |
| `POST` | `/api/v1/auth/logout` | user | — |
| `POST` | `/api/v1/auth/register` | admin | JSON: `UserCreate` |
| `GET` | `/api/v1/auth/me` | user | — |

`POST /auth/register` is admin-only by design, to prevent uncontrolled
self-registration; self-service signup is a separate, deliberately
unregistered endpoint (see below).

### Self-registration (not yet active)

A `signup` handler accepting `UserSignup` exists in the codebase but is
**not wired into the router**. A stub endpoint registered purely to return
`404`/`501` would still appear in `GET /openapi.json`, revealing its
existence to an unauthenticated caller for no benefit. The handler is kept
as reference code, force-setting `role=UserRole.user` and
`is_verified=False` server-side regardless of the payload, and will only be
registered once an anti-abuse strategy (rate-limiting, email verification,
CAPTCHA) is ready. A regression test asserts both that `/auth/signup` is
absent from `GET /openapi.json` and that calling it returns `404`, so an
accidental future `include_router` breaks CI immediately instead of
shipping unnoticed.

> Self-registration combined with email verification was later built as a
> separate, narrower feature — see
> [Self-Registration & Email Verification](./signup_email_verification.md).

---

## Refresh tokens & revocation

The initial phases of this plan covered authentication and authorization
but left two gaps that block a production frontend: access tokens expire
after 30 minutes with no way to renew a session silently, and a stolen
token stays valid until natural expiry since `POST /auth/logout` had
nothing to actually revoke.

### Refresh token design

The refresh token is a JWT signed with the same `secret_key`, carrying
`"type": "refresh"` and a 7-day expiry — not an opaque token in a dedicated
database table, and not a Redis-backed blacklist. Both alternatives were
rejected: an opaque-token table adds an extra read that `get_current_user`
doesn't already do plus a cleanup/TTL story, and Redis is listed as a
dependency but neither configured nor deployed anywhere in the project, so
introducing it for a simple revocation counter would add unplanned
infrastructure for no real benefit over `token_version` (below). A cookie-based
refresh token was also considered but is out of scope for a backend-only
API — worth revisiting only if a BFF is introduced.

Every call to `POST /auth/refresh` **consumes** the refresh token it
receives and returns a brand-new access/refresh pair (rotation). Replaying
an old refresh token is rejected by the `token_version` check below, not by
tracking used tokens.

### Revocation via `token_version`

A `token_version` integer on `User` (default `0`) is embedded in every
token's `tkv` claim. `get_current_user` compares `user.token_version`
against the token's `tkv` on every request — a mismatch means the token was
issued before a revocation event and is rejected with `401`. This costs
nothing extra: `get_current_user` already runs a `SELECT` on `users` to
load the user, so the comparison is free.

`token_version` is incremented on:

- `POST /auth/logout` (explicit sign-out),
- password changes (invalidates sessions open on other devices),
- role changes (recommended — prevents a token minted under the old role
  from remaining valid).

Account deactivation doesn't need its own increment — `get_current_user`
already rejects inactive accounts directly.

`POST /auth/logout` therefore has real effect: it increments
`token_version`, which immediately invalidates every access and refresh
token issued before the call, without waiting for expiry and without a
token blacklist.

---

## Securing existing routes

`app/api/v1/routers/mtgjson.py`'s `_require_admin_key` (a bespoke
`X-Admin-Key` header check) is removed entirely and `POST /mtgjson/import`
now depends on `AdminUser` instead:

```python
async def trigger_import(
    session: DatabaseSession,
    _: AdminUser,
    source: Literal["AllPrices", "AllPricesToday"],
    force: bool = False,
) -> ImportStatus:
    ...
```

`admin_api_key` remains in `BaseAppSettings` for other potential uses (CLI
scripts, external webhooks) but must not be used as an HTTP authentication
mechanism going forward. Any CI/CD script or manual call that previously
sent `X-Admin-Key` must migrate to `POST /auth/token` + `Authorization:
Bearer`.

---

## Testing

`tests/test_auth.py` and `tests/test_auth_security.py` cover the full
surface: login success/failure paths (including the timing-safe branches),
role-hierarchy enforcement (401 vs 403 per level), token expiry, guard-type
rejection (an access token rejected by `decode_refresh_token` and vice
versa), refresh rotation, logout revocation of both access and refresh
tokens, and the `signup` non-exposure regression test described above. Per
project convention, `app/models/` requires 100% coverage; the rest of the
touched code sits at ≥ 90%. The suite reached 158 tests at 90.70% coverage
at the time of the last review round.

---

## Deployment

### Required environment variables

| Variable | Example | Required in prod |
| -------- | ------- | ------------------ |
| `SECRET_KEY` | `$(openssl rand -hex 32)` | ✅ Must be unique and random |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db` | ✅ |
| `ENVIRONMENT` | `production` | ✅ Enables the strict startup validators |
| `ALGORITHM` | `HS256` | No (default) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | No |
| `ADMIN_API_KEY` | *(kept or left empty)* | No — no longer used for HTTP auth |

Never store `SECRET_KEY` or `DATABASE_URL` in the repository — use a
secrets manager or encrypted CI variables.

### Migration procedure

```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
alembic upgrade head --sql   # review the generated SQL first
alembic upgrade head
psql $DATABASE_URL -c "\d users"
```

### Deployment checklist

- [x] CI green: tests (100% on `app/models`, ≥ 90% overall), `mypy`
- [ ] `SECRET_KEY` set to a non-default value in production
- [ ] Production environment variables provisioned in the secrets manager
- [ ] Migration exercised on staging (`upgrade` + `downgrade` + `upgrade`)
- [ ] Database backup taken before applying in production
- [x] `scripts/create_admin.py` executed to bootstrap the first admin
- [ ] Smoke tests in production: login returns a token pair, refresh
      returns a new pair, logout invalidates the old tokens, `/auth/me`
      returns the profile, `/mtgjson/import` requires the admin role,
      public `GET` routes remain open

---

## Known limitations / backlog

| # | Item | Blocking? |
| - | ---- | --------- |
| P-01 | Final name and scope of `role_c` (level 2) | No — deployable with the placeholder |
| P-02 | Email verification strategy for `POST /auth/signup` | No — endpoint not registered |
| P-03 | Rate-limiting on `POST /auth/token` | No — recommended before opening the frontend |
| P-05 | `secret_key` rotation procedure — invalidating tokens already in flight | No — to be documented |
| P-07 | `python-jose` maintenance activity — consider migrating to `PyJWT` | No |
| P-08 | Turn `create_admin.py` into an integrated CLI command | No |
| P-09 | Make Argon2 cost parameters (`memory_cost`, `time_cost`, `parallelism`) configurable via settings | No |
| P-10 | Add `check_needs_rehash` to the login handler for automatic rehashing when Argon2 parameters change | No |
