# identity_client: Barrin's Identity token verification

A small package that lets any backend trust tokens issued by
`apps/barrins_identity` without calling back to it per request. It fetches
the JWKS document once, caches the RSA public key(s) by `kid`, and
verifies each token locally (RS256 signature + `exp` + `type` /
`account_type` + optional scope).

One shared package rather than a copy per consumer (ADR-17): a
token-format fix lands once, and every consumer runs the same
verification logic. It is imported, never deployed — hence `libs/`, not
`apps/`.

## Scope

- **`JWKSCache`** — fetch `{IDENTITY_SERVICE_URL}/.well-known/jwks.json`,
  cache `{kid: RSAPublicKey}` with a monotonic-clock TTL (default
  `3600s`), refresh on expiry and on an unknown `kid` (key rotation
  publishes the new `kid` before switching the private key).
- **`verify_token(...)`** — framework-free verification returning a
  `VerifiedPrincipal` (`subject`, `account_type`, `token_type`,
  `token_version`, `role`, `email`, `scopes`). Raises `InvalidToken`
  (→ 401), `InsufficientScope` (→ 403), or `JWKSError`.
- **`make_verify_dependency(cache, *, expected_account_type, ...)`** — a
  FastAPI dependency wrapping `verify_token`; `401` with
  `WWW-Authenticate: Bearer` for a bad token, `403` for a missing scope.

It does **not** re-check `token_version` (`tkv`) — a stateless verifier
can't. A consumer that needs revocation faster than the access-token TTL
must call the identity service itself (integration.md §3).

## Non-scope

No token *issuance*, no password handling, no database, no config
loading. Consumers read `IDENTITY_SERVICE_URL` /
`IDENTITY_JWKS_CACHE_TTL_SECONDS` themselves and construct one
`JWKSCache` at startup.

## Usage

```python
from identity_client import JWKSCache, make_verify_dependency

identity = JWKSCache("https://id.barrins-codex.org", cache_ttl_seconds=3600)

RequireTolariaRead = make_verify_dependency(
    identity, expected_account_type="service", required_scope="tolaria:read"
)


@router.get("/internal/thing")
async def thing(principal: VerifiedPrincipal = Depends(RequireTolariaRead)): ...
```

The token format this verifies is owned by
`apps/barrins_identity/app/core/security.py`; see
`docs/content/back/barrins_identity/integration.md` §2–§3.
