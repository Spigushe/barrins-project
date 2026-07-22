# Barrin's Identity: JWT (RS256) identity & service-account authority

Shared authentication for `barrins_api`, `tolaria_news` and `tamiyo_scroll`.
See the Platform doc (linked below) for the full architecture and the
Tests doc for the test plan.

## What's implemented

- Human login: `POST /api/v1/auth/token`, `POST /api/v1/auth/refresh`,
  `POST /api/v1/auth/register` (admin), `GET /api/v1/auth/me`,
  `POST /api/v1/auth/logout`.
- Service accounts (machine-to-machine, `client_credentials`-style):
  `POST /api/v1/service-accounts` (create, admin),
  `GET /api/v1/service-accounts` (list, admin),
  `POST /api/v1/service-accounts/{client_id}/revoke` (admin),
  `POST /api/v1/service-token` (public, client_id/client_secret exchange).
- `GET /.well-known/jwks.json` — public key discovery for consumers.
- `GET /health` — liveness check.

RS256 signing, Argon2id password/secret hashing, per-IP rate limiting on
`/auth/token`, and the standard Barrin's error-response envelope.

## What's NOT in this app yet

- The `barrins_api` cutover (migrating its local `users` table here,
  replacing its local JWT auth with `identity_client` verification) —
  platform.md §9. This is flagged as the highest-risk phase and requires
  an explicit user-confirmed maintenance window before touching production
  data; it was intentionally left for a follow-up task.
- `tolaria_news` routes and their `service-token` scope checks —
  platform.md §10 (front is still under specification).
- Self-service registration + email verification (constitution §13.2–13.3).
  `platform.md` §8 only documents an admin-only `/register`; the
  self-signup + email-verification flow from `barrins_api` was not carried
  over to this new service. See the implementation decision log for
  details.

## Quickstart

```bash
cd apps/barrins_identity
cp .env.example .env  # fill in DATABASE_URL, JWT_PRIVATE_KEY, ALLOWED_ORIGINS
uv sync --group dev
uv run alembic upgrade head
uv run python scripts/create_admin.py --email admin@example.com
uv run uvicorn app.main:app --reload --port 8001
```

Generate a private key for `.env`:

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048
```

## Tests

```bash
uv run pytest
uv run pytest --cov=app --cov-report=term-missing
```
