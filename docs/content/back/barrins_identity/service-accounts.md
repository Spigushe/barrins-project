# Barrin's Identity — Service Accounts

Machine-to-machine credentials: a way for a background job, a BFF, or a
reverse-proxy to authenticate to a Barrin's service **without a user
signed in**. Managed from Goblin Guide (administrators only) or the API.

This page is the reproducible how-to. The wire contract is
[Integration Contract §4.6](integration.md#46-service-accounts) /
[§8.7](integration.md#87-service-to-service-call); the token format is
[§2](integration.md#2-token-model).

---

## 1. What a service account is

| | User account | Service account |
| --- | --- | --- |
| Behind it | a person | a program |
| Logs in with | email + password | `client_id` + `client_secret` |
| Gets | access + refresh token (`type=access`) | one short-lived token (`type=service`) |
| Carries | `role` (user … admin) | `scopes` (list of strings) |
| Token TTL | `ACCESS_TOKEN_EXPIRE_MINUTES` (10) | `SERVICE_TOKEN_EXPIRE_MINUTES` (15) |
| Refresh | yes (`/auth/refresh`) | no — re-exchange the credential |

A service account is a row in the `service_accounts` table:

| Field | Notes |
| --- | --- |
| `client_id` | `sa_` + 16 hex, e.g. `sa_3f9a2c7e8b1d4056`. Not secret — it identifies the account |
| `client_secret` | shown **once**, at creation. Only its Argon2id hash is stored — it cannot be retrieved or reset |
| `description` | free text, shown in the admin list so you can tell accounts apart |
| `scopes` | list of strings, at least one — see §2 |
| `is_active` | `false` after a revoke; the row is kept for the audit trail |
| `created_at` | |

---

## 2. Scopes

A scope is a **permission label**. It is an opaque string: Barrin's
Identity stores whatever you give it, copies the list verbatim into the
`scopes` claim of the service token, and **never checks it**.

Enforcement lives entirely in the **consuming** service, through the
shared `libs/identity_client` verifier:

```python
from identity_client import JWKSCache, make_verify_dependency

identity = JWKSCache("https://identity.barrins-codex.org")

RequireScriptureRead = make_verify_dependency(
    identity, expected_account_type="service", required_scope="bs:read"
)

@router.get("/internal/scripture/export")
async def export(_: VerifiedPrincipal = Depends(RequireScriptureRead)):
    ...
```

If the presented token's `scopes` list does not contain the route's
`required_scope`, the verifier raises `InsufficientScope` → **HTTP 403**.
No `required_scope` on the route means any valid service token passes.

### Naming convention

`<service-or-domain>:<action>` — lower case, `:` separator. Actions are
`read` / `write` (add more only when a route actually distinguishes
them).

| Scope | Meaning | Checked by |
| --- | --- | --- |
| `bs:read` | read Barrin's Scripture data | `barrins_api` Scripture routes |
| `kt:read` | read Karn Tablets data | `barrins_api` Karn routes |
| `tolaria:read` | read the Tolaria News BFF feed | `barrins_api` Tolaria BFF |
| `tolaria:write` | write to the Tolaria News BFF | `barrins_api` Tolaria BFF |
| `cards:write` | bulk card import (MTGJSON backfill) | `barrins_api` import job route |

This table is descriptive, not an allow-list — there is no scope registry
in code. A scope "exists" once **(a)** it is on a service account and
**(b)** some route names it in `required_scope`. To introduce a new one:
pick a name that follows the convention, put it on the account (§3), and
reference it from the consuming route's dependency.

---

## 3. Create a service account

### Prerequisites

- A Barrin's account with the **`admin`** role
  (`apps/barrins_identity/scripts/create_admin.py` seeds the first one).
- Goblin Guide reachable — `https://goblin-staging.barrins-codex.org`
  (staging) or `https://goblin.barrins-codex.org` (production).

### Via Goblin Guide (recommended)

1. Sign in to Goblin Guide as an admin.
2. In the header, click **Service accounts**, link is shown only to
   `admin` accounts.
3. Under **New service account**:
   - **Description** (optional) — e.g. `Tolaria News BFF cache warmer`.
   - **Scopes** — type one scope (e.g. `bs:read`), then press **Enter**
     or click **Add**. It becomes a removable chip. Repeat for each
     scope. At least one is required.
4. Click **Create service account**.
5. The confirmation screen shows the **`client_id`** and the
   **`client_secret`** — this is the only time the secret is displayed.
   Copy both into your secrets store (`ops/my-server/secrets/…`, a CI
   secret, etc.) now. Then click **Done**.

### Via the API

```bash
# ADMIN_TOKEN = an admin user's access token (POST /api/v1/auth/token)
curl -sS -X POST https://identity.barrins-codex.org/api/v1/service-accounts \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Nightly Scripture export", "scopes": ["bs:read"]}'
```

`201` response body:

```json
{
  "id": "…", "client_id": "sa_3f9a2c7e8b1d4056",
  "description": "Nightly Scripture export",
  "scopes": ["bs:read"], "is_active": true,
  "created_at": "2026-08-31T09:30:00Z",
  "client_secret": "…shown once…"
}
```

Errors: `401` (no/invalid admin token), `403` (token is not `admin`),
`422` (empty `scopes`).

---

## 4. Use a service account

Two calls: exchange the credential for a token, then call the target
service with it.

```bash
# 1. Exchange — no auth header, the body IS the credential
TOKEN=$(curl -sS -X POST \
  https://identity.barrins-codex.org/api/v1/service-token \
  -H "Content-Type: application/json" \
  -d '{"client_id": "sa_3f9a2c7e8b1d4056", "client_secret": "…"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Call the target service
curl -sS https://api.barrins-codex.org/internal/scripture/export \
  -H "Authorization: Bearer $TOKEN"
```

The exchange response is
`{access_token, token_type: "bearer", expires_in}` — `expires_in` is
`SERVICE_TOKEN_EXPIRE_MINUTES * 60` (900). **Cache the token** for that
long and re-exchange when it expires; do not exchange per request.

Notes:

- An unknown `client_id` and a wrong `client_secret` both return
  `401 Invalid client credentials.` (anti-enumeration — same as
  `/auth/token`). A revoked account returns the same `401`.
- `/service-token` has **no** per-IP rate limit today (unlike
  `/auth/token`).
- The target service verifies the token locally against JWKS
  (`libs/identity_client`); it does not call identity per request. It
  does **not** re-check `token_version`, so a revoke takes effect for a
  target only after the current token expires (≤ 15 min) — see §5.

---

## 5. Revoke a service account

Revoking deactivates the account **and** bumps its `token_version`, which
makes every outstanding token issued to it fail verification. The row
stays in the list (marked revoked) for the audit trail.

### Via Goblin Guide

Service accounts screen → the account's card → **Revoke** → confirm.

### Via the API

```bash
BASE=https://identity.barrins-codex.org
CID=sa_3f9a2c7e8b1d4056

curl -sS -X POST "$BASE/api/v1/service-accounts/$CID/revoke" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# 204 No Content
```

`404` if the `client_id` is unknown; `401` / `403` as for create.

Timing: identity rejects a newly-exchanged token immediately. A target
service holding an **already-exchanged** token keeps accepting it until
it expires (`expires_in`, ≤ 15 min), because the stateless verifier does
not re-check `token_version`. Schedule the switch-over around that
window.

---

## 6. Rotate a secret, or change scopes

There is **no** "reset secret" and **no** "edit scopes" endpoint — a
service account's secret and scope set are fixed at creation. To change
either:

1. Create a **new** service account with the desired scopes (§3).
2. Roll the new `client_id` / `client_secret` out to every consumer.
3. Revoke the old account (§5) once nothing uses it.

Keep the `description` distinct (e.g. add `(rotated 2026-08-31)`) so the
audit list stays readable.

---

## 7. Where it lives

| Piece | Path |
| --- | --- |
| Routes (`create` / `list` / `revoke` / `service-token`) | `apps/barrins_identity/app/api/v1/service_accounts.py` |
| Model | `apps/barrins_identity/app/models/service_account.py` |
| Token minting (`create_service_token`) | `apps/barrins_identity/app/core/security.py` |
| Consumer-side verification + `required_scope` | `libs/identity_client/` ([README](https://github.com/Spigushe/barrins-project/blob/staging/libs/identity_client/README.md)) |
| Admin UI | `libs/goblin_guide/src/components/ServiceAccountsScreen.tsx` |

## See also

- [Integration Contract §4.6](integration.md#46-service-accounts),
  [§8.7](integration.md#87-service-to-service-call)
- [Platform Architecture — `service_accounts` table](platform.md)
- [ADR-16 — identity as the JWKS authority](../../ops/architecture/decisions.md#adr-16-adopt-barrins-identity-as-the-rs256-jwks-authority),
  [ADR-17 — shared `libs/`](../../ops/architecture/decisions.md#adr-17-shared-code-lives-in-a-top-level-libs-directory)
