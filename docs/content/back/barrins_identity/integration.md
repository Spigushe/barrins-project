<!-- cSpell:ignore JWKS pyjwt slowapi respx cutover keypair OIDC domainkey -->
# Barrin's Identity — Integration Contract

> **Status**: 🟩 On the `proj/v2.0.0-bump` release line (T10). Every
> endpoint below is implemented and tested in `apps/barrins_identity/`,
> and `libs/identity_client/` implements the §3 verification flow. The
> `username` field (§4.1) is live. ⬜ still: the `barrins_api` cutover,
> the playbook, and Goblin Guide.
>
> **Frontend counterpart**: [Goblin Guide — Bootstrap](../../front/goblin_guide/bootstrap.md)
> mirrors §8 (Consumer flows) from the client side.

The design and rationale are in [Platform Architecture](./platform.md);
this page is what a consumer needs to talk to the service — token shapes,
every endpoint, error codes, and the local-verification model.

Base path: `/api/v1`. JWKS is served at the domain root
(`/.well-known/jwks.json`), not under `/api/v1`.

---

## 1. Who consumes this

| Consumer | What it uses | Notes |
| --- | --- | --- |
| `barrins_api` | JWKS (verify user + service tokens locally), `POST /service-token` → `POST /users/lookup` (§4.9) for team-roster / sharing display labels | **First JWKS consumer.** Cut over ([platform.md §10](./platform.md#10-cutover), ADR-20): no local `users` table, issues no tokens of its own, never enumerates or counts users |
| Goblin Guide (`apps/goblin_guide/`) | Human login + the full account-lifecycle surface (§4.1–§4.5) | Browser SPA, calls this service **directly** (no BFF, ADR-18); opts into cookie mode on `/auth/token`\|`/refresh`\|`/logout` for persistent sessions |
| T9 Jupyter workbench proxy | A reverse-proxy role gate (§8.8) against a user token's `role` claim | `karn-jupyter.barrins-codex.org` — see `docs/project/v2.0.0-bump/t9-karn-jupyter-workbench/` and [ADR-15](../../ops/architecture/decisions.md#adr-15-karn-tablets-observability-job-health-and-jupyter-lab) |
| `tolaria_news`, `tamiyo_scroll` | JWKS + service tokens, once built / cut over | Future |

---

## 2. Token model

Three token types, all RS256, all carrying a `kid` header for rotation
and `type` + `account_type` claims that are enforced on decode.

| Token | Claims | TTL |
| --- | --- | --- |
| User **access** | `sub` (user UUID), `role`, `email`, `tkv`, `type="access"`, `account_type="user"`, `exp` | `ACCESS_TOKEN_EXPIRE_MINUTES` (10) |
| User **refresh** | same shape, `type="refresh"` | `REFRESH_TOKEN_EXPIRE_DAYS` (7) |
| **Service** | `sub` (client_id), `scopes` (list), `tkv`, `type="service"`, `account_type="service"`, `exp` | `SERVICE_TOKEN_EXPIRE_MINUTES` (15) |

`tkv` is the principal's `token_version` — see revocation, §5 and
[platform.md §4](./platform.md#4-revocation-model). A refresh token
presented where an access token is expected (or a service token to a user
route) is rejected on decode, before any lookup.

---

## 3. Local verification

Consumers verify tokens **locally** — no call back to `barrins-identity`
per request.

```text
startup / every IDENTITY_JWKS_CACHE_TTL_SECONDS (default 3600):
  GET {IDENTITY_SERVICE_URL}/.well-known/jwks.json  ->  cache {kid: public_key}

per protected request:
  read `kid` from the JWT header
  jwt.decode(token, cached_public_key[kid], algorithms=["RS256"])
     -> InvalidToken / Expired  => 401
  check `type` / `account_type` match what the route expects
     -> mismatch                => 401
  check the route's required scope is in `scopes`  (service tokens)
     -> missing                 => 403
```

The JWKS document is RFC 7517:

```json
{"keys": [{"kty": "RSA", "use": "sig", "alg": "RS256",
           "kid": "<id>", "n": "<modulus>", "e": "<exponent>"}]}
```

A stateless verifier does **not** re-check `tkv` per request — only
`barrins-identity` does, at `/auth/refresh`, `/auth/logout` and inside its
own dependencies. A consumer that needs revocation to bite faster than the
10-minute access TTL must call `barrins-identity` itself.

The verification client is **built**: `libs/identity_client/` —
`JWKSCache` (fetch + monotonic-TTL cache + refresh-on-unknown-`kid`),
the framework-free `verify_token`, and `make_verify_dependency` for
FastAPI (`401` with `WWW-Authenticate: Bearer` on a bad token, `403` on a
missing scope). One shared Python package every backend consumer imports,
not a per-app copy
([ADR-17](../../ops/architecture/decisions.md#adr-17-shared-code-lives-in-a-top-level-libs-directory)).
It is not yet consumed anywhere — the `barrins_api` cutover
([platform.md §10](./platform.md#10-cutover)) wires it in.

---

## 4. Endpoint contract

`extra="forbid"` on every request body — an undeclared field is `422`,
not silently ignored. `401` responses carry `WWW-Authenticate: Bearer`.

### 4.1 Human login and session

Prefix `/api/v1/auth`.

| Method | Path | Auth | Request | Response | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/token` | none | form: `username` (the email), `password` | `TokenPair` | `401` uniform `Invalid credentials.`; `429` over `LOGIN_RATE_LIMIT` |
| POST | `/refresh` | none | `{refresh_token}` | `TokenPair` (both tokens rotated) | `401` expired / malformed / wrong type / `tkv` mismatch |
| POST | `/logout` | user | — | `204` | `401` |
| POST | `/register` | admin | `UserCreate` `{email, username, password, role?, is_verified?, display_name?}` | `UserRead`, `201` | `401` / `403`; `409` email **or** username exists; `422` missing/invalid `username` |
| GET | `/me` | user | — | `UserRead` `{id, email, username, role, is_active, is_verified, display_name}` | `401` |

`TokenPair` = `{access_token, refresh_token, token_type: "bearer"}`.

**Cookie mode (ADR-18).** A browser SPA sends `X-Client: web` on `/token`,
`/refresh` and `/logout`. With it and `REFRESH_COOKIE_ENABLED=true`,
`/token` and `/refresh` set the refresh token as an
`HttpOnly; Secure; SameSite=<REFRESH_COOKIE_SAMESITE>;
Domain=<REFRESH_COOKIE_DOMAIN>; Path=/api/v1/auth` cookie and drop
`refresh_token` from the body (`access_token` only); `/refresh` reads the
cookie instead of a body field; `/logout` clears it. Cross-site callers
must send `credentials: 'include'`; the response carries
`Access-Control-Allow-Credentials: true` only when the `Origin` is in
`ALLOWED_ORIGINS`. Without the header the endpoints are unchanged
(refresh token in the body).

A unique `username` (input rule `^[A-Za-z0-9_-]{3,32}$`) is **required**
on `UserCreate` / `UserSignup` and echoed on `UserRead` (§13.2, T10). A
taken handle is a `409` with a message distinct from the email conflict.
`POST /auth/token` still authenticates by `email` only — the form field
named `username` carries the email ([`Q-05`](./platform.md#11-open-questions)).

| `POST /api/v1/auth/token` | |
| --- | --- |
| **Purpose** | Exchange email + password for an access/refresh pair |
| **Auth** | None. `@limiter.limit(LOGIN_RATE_LIMIT)`, per IP |
| **Request** | `application/x-www-form-urlencoded`: `username` (email), `password` (OAuth2 password form — needed for the Swagger Authorize button) |
| **Response** | `200` `TokenPair` |
| **Errors** | `401 Invalid credentials.` for unknown email, wrong password, **and** inactive account — same body, same timing (`verify_password` runs before the `is_active` check; a dummy Argon2 verify runs for an unknown email). `429` over the rate limit |

### 4.2 Self-registration and email verification

Prefix `/api/v1/auth`. A **live, required** flow in production
(`REQUIRE_EMAIL_VERIFICATION=true` — [ADR-3](../../ops/architecture/decisions.md#adr-3-production-email-uses-a-transactional-provider-not-self-hosted),
ADR-16). Setup: [Identity Deployment — email](../../ops/deployment/identity.md#email-verification-mandatory-production-setup-brevo).

| Method | Path | Auth | Request | Response | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/signup` | none | `UserSignup` `{email, username, password, display_name?}` | `SignupResponse`, `201` | `409` email **or** username exists (distinct messages); `422` missing/invalid `username`; `502` (no account created) if the email fails to send |
| POST | `/signup/verify` | none | `{email, code}` (`code` = `^\d{6}$`) | `TokenPair` | `400` invalid/expired code; `409` already verified; `429` over `VERIFICATION_MAX_ATTEMPTS` |
| POST | `/signup/resend` | none | `{email}` | `ResendVerificationResponse`, `202` | `502` send failure. Always the same generic body otherwise |

`SignupResponse` = `{detail, verification_required: bool, tokens: TokenPair | null}`.
Branch on `verification_required`, never on server config:
`true` ⇒ `tokens` is `null`, call `/signup/verify` next; `false`
(`REQUIRE_EMAIL_VERIFICATION=false`) ⇒ `tokens` present, already logged in.

| `POST /api/v1/auth/signup` | |
| --- | --- |
| **Purpose** | Public self-registration |
| **Auth** | None |
| **Request** | `{email, username, password, display_name?}`. `role` / `is_verified` are **not** accepted — forced server-side (`extra="forbid"` rejects an attempt with `422`) |
| **Response** | `201` `SignupResponse` |
| **Idempotency** | Not idempotent — a second call with the same email is `409` |
| **Errors** | `409` email already registered; `422` password fails the complexity rule (≥ 12 chars, 1 upper, 1 lower, 1 digit, 1 symbol) or an undeclared field is sent; `502` the verification email could not be sent (the account is rolled back — no orphan) |

### 4.3 Password reset

Prefix `/api/v1/auth`.

| Method | Path | Auth | Request | Response | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/password-reset/request` | none | `{email}` | `PasswordResetRequestResponse`, `202` | `429` over `PASSWORD_RESET_RATE_LIMIT` (per IP); `502` send failure. Always the same generic body otherwise |
| POST | `/password-reset/confirm` | none | `{email, code, new_password}` (`code` = `^\d{6}$`) | `TokenPair` | `400` invalid/expired code; `429` over `PASSWORD_RESET_MAX_ATTEMPTS` |

| `POST /api/v1/auth/password-reset/confirm` | |
| --- | --- |
| **Purpose** | Set a new password from a reset code and log the user in |
| **Auth** | None (the code is the proof) |
| **Request** | `{email, code, new_password}` |
| **Response** | `200` `TokenPair` — a fresh pair |
| **Idempotency** | Single-use — the code row is deleted on success; a replay is `400` |
| **Errors** | `400` wrong / expired / already-consumed code (one message, no distinction); `429` too many attempts; `422` `new_password` fails the complexity rule. On success **every previously issued access and refresh token for the account is invalidated** (`token_version` bump) |

### 4.4 Account management

Prefix `/api/v1/users`. `GET /auth/me` (§4.1) stays the read endpoint;
`/users/*` owns mutation of the same `User` row.

| Method | Path | Auth | Request | Response | Errors |
| --- | --- | --- | --- | --- | --- |
| PATCH | `/me` | user | `AccountSettingsUpdate` `{display_name?, email?}` (partial — a field absent is untouched; `display_name: null` clears it) | `UserRead` | `409` new email already registered; `502` email-change code could not be sent |
| POST | `/me/email-change/verify` | user | `{code}` (`^\d{6}$` — no `email`, the caller is authenticated) | `UserRead` (new email) | `404` no pending change; `400` invalid/expired code; `429` too many attempts; `409` address claimed in the interim (pending row is then deleted) |
| POST | `/me/email-change/resend` | user | — | `EmailChangeResendResponse`, `202` | `404` no pending change |
| DELETE | `/me` | user | `AccountDeleteRequest` `{current_password}` | `204` | `401` wrong password |

`PATCH /me` with a new `email` applies it immediately only when
`REQUIRE_EMAIL_VERIFICATION=false`; otherwise `users.email` (the old
address) stays authoritative, the response still shows it, and a code goes
to the new address for `/me/email-change/verify`. A confirmed email change
does **not** invalidate existing tokens — the `email` claim is
informational.

`DELETE /me` soft-deletes: the row and `id` survive, `email` /
`display_name` are anonymized, `is_active` goes `false`, `token_version`
is bumped. Cleanup of that user's data **in other apps** is each app's own
responsibility.

### 4.5 Per-app settings

Prefix `/api/v1/users`. `{app_key}` ∈ `{tamiyo_scroll, tolaria_news}`.

| Method | Path | Auth | Request | Response | Errors |
| --- | --- | --- | --- | --- | --- |
| GET | `/me/settings/{app_key}` | user | — | `AppSettingsRead` `{data}` (`{}` if no row — a GET never creates one) | `404` unknown `app_key` |
| PUT | `/me/settings/{app_key}` | user | a raw JSON **object** | `AppSettingsRead` | `404` unknown `app_key`; `413` body over `MAX_APP_SETTINGS_BYTES` (16 KiB); `422` body is not a JSON object |

| `PUT /api/v1/users/me/settings/{app_key}` | |
| --- | --- |
| **Purpose** | Store this user's opaque settings blob for one app |
| **Auth** | User access token only (the documented service-account path is not implemented) |
| **Request** | A JSON object of any shape — `barrins-identity` validates nothing about the contents beyond size |
| **Response** | `200` `AppSettingsRead` `{data}` — the stored blob |
| **Idempotency** | Full replace / upsert — the previous blob is overwritten, not merged |
| **Errors** | `404` `app_key` not in the allow-list (deliberately not `422`); `413` serialized size over the cap; `422` the body is a bare string / array / scalar |

### 4.6 Service accounts

Mounted at `/api/v1` (no extra prefix). Step-by-step create / use /
revoke / rotate and the scope model:
[Service Accounts](service-accounts.md).

| Method | Path | Auth | Request | Response | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/service-accounts` | admin | `{description?, scopes: [str] (≥ 1)}` | `ServiceAccountCreated` (incl. plaintext `client_secret`, shown once), `201` | `401` / `403` |
| GET | `/service-accounts` | admin | — | `[ServiceAccountRead]` (no secret) | `401` / `403` |
| POST | `/service-accounts/{client_id}/revoke` | admin | — | `204` | `401` / `403`; `404` unknown `client_id` |
| POST | `/service-token` | none | `{client_id, client_secret}` | `ServiceTokenResponse` | `401 Invalid client credentials.` |

| `POST /api/v1/service-token` | |
| --- | --- |
| **Purpose** | `client_credentials`-style exchange for a short-lived service token |
| **Auth** | None — the body *is* the credential |
| **Request** | `{client_id, client_secret}` |
| **Response** | `200` `{access_token, token_type: "bearer", expires_in}` — `expires_in` = `SERVICE_TOKEN_EXPIRE_MINUTES * 60` (900) |
| **Errors** | `401 Invalid client credentials.` for an unknown `client_id`, a wrong secret, **and** a revoked account — same body, dummy verify on an unknown id |

### 4.7 Application directory (ADR-19)

Mounted at `/api/v1` (no extra prefix). The role-aware cross-app launcher
for Goblin Guide — "which apps can this user open" is a backend decision
(constitution §4.1).

| Method | Path | Auth | Response | Errors |
| --- | --- | --- | --- | --- |
| GET | `/applications` | optional bearer | `[ApplicationRead]` | `401` for a supplied-but-invalid token |

| `GET /api/v1/applications` | |
| --- | --- |
| **Purpose** | List the Barrin's apps with a per-caller `access` state |
| **Auth** | Optional. No `Authorization` header ⇒ treated as anonymous. A header that is present but invalid still `401`s (so the client can silent-refresh) |
| **Response** | `200` `[{key, name, description, url, logo_svg, access, min_role}]`, ordered by `sort_order`. Inactive apps omitted. `logo_svg` is inline SVG markup — render it as an `<img>` `data:` URI, never `dangerouslySetInnerHTML`. `min_role` is `null` unless the app is role-restricted |
| **`access`** | `open` — caller can open it now · `login_required` — a members app the caller must sign in for · `role_denied` — signed in but role below `min_role` |
| **Rule** | `!needs_authentication` → `open`. Else anonymous → `login_required`. Else `!is_role_restricted` → `open`. Else `role.level >= min_role.level` → `open`, otherwise `role_denied` |
| **Current app** | Not filtered server-side — a host SPA drops its own `key` (`currentAppKey`) |

### 4.8 Discovery and health

| Method | Path | Auth | Response |
| --- | --- | --- | --- |
| GET | `/.well-known/jwks.json` | none | JWKS document (RFC 7517), domain root |
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/` | none | `301` → `/docs` |

### 4.9 Batch user directory (ADR-20)

Mounted at `/api/v1/users`. Lets a JWKS consumer that stores identity
user ids on its own domain rows (`barrins_api` after the cutover — team
rosters, chat authors, "shared with you" labels) resolve display labels
without a local copy of the `users` table.

| Method | Path | Auth | Request | Response | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/users/lookup` | service token, scope `identity:users:read` | `{ids: [UUID] (1..200)}` | `[{id, username, display_name}]` | `401` no/invalid/ user token; `403` valid service token without the scope; `422` empty list or > 200 ids |

| `POST /api/v1/users/lookup` | |
| --- | --- |
| **Purpose** | Batch-resolve public label attributes for a set of identity user ids |
| **Auth** | Service token only (`account_type: "service"`), and its `scopes` must contain `identity:users:read`. A user token is rejected `401` |
| **Request** | `{ "ids": ["<uuid>", …] }` — 1 to 200 ids; duplicates are collapsed |
| **Response** | `200` `[{id, username, display_name}]` for the **active** accounts among `ids`. Unknown ids and deactivated / soft-deleted accounts are simply omitted (no error, no placeholder row) |
| **Privacy** | The response carries the public handle and optional display name **only** — never `email`, `role`, `is_active`, or any timestamp. Consumers that show a label fall back to a generic string (`"a kind user"`) for an omitted id |
| **Consumer** | `barrins_api`'s `app/services/identity_directory.py` — acquires a service token via `POST /service-token`, calls this endpoint in ≤ 200-id batches, and caches `{id: {username, display_name}}` in-process (~5 min TTL). Empty service-account credentials ⇒ the directory is disabled and every label falls back |

---

## 5. Anti-enumeration and rate limiting

- **Login and service-token**: unknown identifier and wrong secret return
  the *same* `401` with the *same* message, and a dummy Argon2 verify runs
  on the unknown-identifier path so the response time matches.
  `verify_password` runs before `is_active`, so a disabled account is not
  distinguishable from a wrong password.
- **`/auth/signup/resend` and `/auth/password-reset/request`**: always the
  same generic `202`, whether or not the account exists, is verified, is
  active, or is in cooldown.
- **Rate limits** (`slowapi`, per client IP): `LOGIN_RATE_LIMIT`
  (`5/minute`) on `/auth/token`; `PASSWORD_RESET_RATE_LIMIT` (`5/minute`)
  on `/auth/password-reset/request`. Over the limit → `429`. These are
  in-process counters — with multiple `uvicorn` workers the effective
  limit multiplies by worker count, same caveat as `barrins_api`; an
  nginx `limit_req` in front is the real control at scale.
- **CORS**: `ALLOWED_ORIGINS` is required, no wildcard (constitution §33),
  `allow_credentials=true`.

---

## 6. Consumer configuration

For an app that verifies `barrins-identity` tokens and/or calls other
services on a user's behalf:

| Variable | Description |
| --- | --- |
| `IDENTITY_SERVICE_URL` | Base URL of `barrins-identity` |
| `IDENTITY_JWKS_CACHE_TTL_SECONDS` | Public-key cache TTL (default `3600`) |
| `IDENTITY_SERVICE_CLIENT_ID` / `IDENTITY_SERVICE_CLIENT_SECRET` | This app's own service-account credentials, if it needs `POST /service-token` |

---

## 7. Error envelope

`barrins-identity` uses the standard Barrin's exception handlers
(`app/core/error_handlers.py`, same shape as `barrins_api`). A `4xx` here
looks exactly like a `4xx` anywhere else in the ecosystem: `{"detail":
"..."}` for a raised error, `{"detail": [ ... ]}` for a `422` validation
failure. Every response echoes `X-Request-ID` (generated if the caller
didn't send one).

---

## 8. Consumer flows

Step sequences for the client. Goblin Guide's
[Bootstrap §4](../../front/goblin_guide/bootstrap.md#4-identity-endpoint-goblin-guide-flow)
maps its screens onto these anchors.

### 8.1 First login

1. `POST /api/v1/auth/token` (form `username` = email, `password`).
2. Keep `access_token` and `refresh_token` client-side (see Goblin Guide
   Bootstrap §5).
3. Send `Authorization: Bearer <access_token>` on protected calls.

### 8.2 Silent refresh

1. A protected call returns `401` (or the access token is near `exp`).
2. `POST /api/v1/auth/refresh` `{refresh_token}` → a new pair. The
   presented refresh token is now spent (rotation).
3. Retry the original call with the new access token.
4. If `/refresh` itself returns `401`, the session is over — go to login.

### 8.3 Signup and verify

1. `POST /api/v1/auth/signup` `{email, username, password, display_name?}` → `201`.
2. If `verification_required` is `false`, `tokens` is present — done.
3. Otherwise collect the 6-digit code and
   `POST /api/v1/auth/signup/verify` `{email, code}` → `TokenPair`.
4. `POST /api/v1/auth/signup/resend` `{email}` re-sends (enforce the
   60-second cooldown in the UI; the response is always generic).

### 8.4 Forgot password

1. `POST /api/v1/auth/password-reset/request` `{email}` → always `202`.
2. Collect the code and a new password.
3. `POST /api/v1/auth/password-reset/confirm` `{email, code, new_password}`
   → `TokenPair`. Every other session for the account is now revoked.

### 8.5 Change email

1. `PATCH /api/v1/users/me` `{email}` (Bearer) → `200`; the response
   still shows the **old** email; a code is sent to the new address.
2. `POST /api/v1/users/me/email-change/verify` `{code}` → `200` with the
   new email. Existing tokens keep working.
3. `POST /api/v1/users/me/email-change/resend` re-sends to the pending
   address.

### 8.6 Delete account

1. `DELETE /api/v1/users/me` `{current_password}` (Bearer) → `204`.
2. Every token for the account is now rejected — clear local state and
   return to login. Not reversible from the client.

### 8.7 Service to service call

1. `POST /api/v1/service-token` `{client_id, client_secret}` →
   `{access_token, expires_in}`.
2. Cache the token until `expires_in` elapses.
3. Call the target service with `Authorization: Bearer <access_token>`.
   The target verifies locally against JWKS and checks the route's
   required scope is in the token's `scopes`.

### 8.8 Proxy role gate

The T9 Jupyter Lab pattern — an app with no auth of its own, gated at the
reverse proxy (nginx `auth_request` or a small sidecar):

1. The proxy holds the user's token (from a Goblin Guide login).
2. On each request it verifies the token against JWKS and checks
   `account_type == "user"` and `role` level ≥ `ml_developer`.
3. `200` → forward to Jupyter; `401` → send to login; `403` → deny.

No change to the protected app. See
`docs/project/v2.0.0-bump/t9-karn-jupyter-workbench/` and
[ADR-15](../../ops/architecture/decisions.md#adr-15-karn-tablets-observability-job-health-and-jupyter-lab).

---

## See also

- [Platform Architecture](./platform.md) — design and rationale.
- [Test Plan](./tests.md) — the negative-case matrix behind these codes.
- [Goblin Guide — Bootstrap](../../front/goblin_guide/bootstrap.md) — the
  client-side mirror of §8.
- [JWT Authentication & Roles](../barrins_api/auth_roles.md) — the
  `barrins_api` auth model this follows.
