# Barrin's Identity: RS256 JWT identity & service-account authority

Shared authentication for the Barrin's ecosystem (`barrins_api` today;
`tolaria_news`, `tamiyo_scroll` and the `goblin_guide` frontend once the
cutover lands). One Barrin's account per person (constitution §13.1),
issued and signed here, verified everywhere else against a cached public
key — no shared signing secret.

> **Status**: 🟨 Built on branches `feat/barrins-identity` and
> `claude/barrins-identity-lifecycle-settings-4g2lyh`; not yet merged to
> the `proj/v2.0.0-bump` release line. See the Platform doc (linked
> below) for what that means for each section.

## Tech stack

| Component | Technology |
| --------- | ---------- |
| Language | Python 3.14+ |
| Framework | FastAPI (own process, own port — `8001` in local dev) |
| Database | PostgreSQL (own database, never shared with `barrins_api`) |
| ORM / migrations | SQLAlchemy 2.x async (`asyncpg`) + Alembic (hand-written) |
| Schemas | Pydantic v2 (`extra="forbid"` on every input schema) |
| JWT | `PyJWT`, RS256, `kid` header for rotation |
| Password / secret hashing | `argon2-cffi` (Argon2id) |
| Rate limiting | `slowapi` (per-IP, on `/auth/token` and password reset) |
| Email | stdlib `smtplib` behind an `EmailSender` protocol |
| Tooling | `uv`, `ty`, `ruff`, `bandit` |

## What's implemented

- **Human login** — `POST /api/v1/auth/token`, `/auth/refresh`,
  `/auth/logout`, `/auth/register` (admin), `GET /auth/me`.
- **Self-registration + email verification**, gated by
  `REQUIRE_EMAIL_VERIFICATION` (default `true`) — `POST /auth/signup`,
  `/auth/signup/verify`, `/auth/signup/resend`. When `false` (no SMTP
  configured), signup creates an already-verified account and returns
  tokens immediately.
- **Password reset** — `POST /auth/password-reset/request` (generic
  `202`, per-IP rate limited), `/auth/password-reset/confirm` (sets the
  new password, revokes every existing session, returns a fresh token
  pair).
- **Account management** — `PATCH /users/me` (display name / email
  change), `POST /users/me/email-change/verify`, `/users/me/email-change/resend`,
  `DELETE /users/me` (soft-delete + anonymize, password re-auth).
- **Per-app settings** — `GET`/`PUT /users/me/settings/{app_key}`, an
  opaque per-user JSON blob keyed by app (`tamiyo_scroll`,
  `tolaria_news`), size-capped.
- **Service accounts** (machine-to-machine, `client_credentials`-style) —
  `POST /api/v1/service-accounts` (create, admin), `GET /service-accounts`
  (list, admin), `POST /service-accounts/{client_id}/revoke` (admin),
  `POST /service-token` (public, `client_id`/`client_secret` exchange).
- **Discovery** — `GET /.well-known/jwks.json` (public key, for
  consumers), `GET /health` (liveness).

RS256 signing, Argon2id hashing, per-IP rate limiting, uniform
anti-enumeration responses, and the standard Barrin's error envelope.

## What's NOT in this app yet

- **The `barrins_api` cutover** — migrating its local `users` table here
  and replacing its local JWT auth with token verification against this
  service. Highest-risk phase; needs a user-confirmed maintenance window.
- **The `identity_client/` verification module** consumers would embed.
- **`tolaria_news` routes and their scope checks** — the frontend is
  still under specification.
- **The service-account path for per-app settings** — documented, wired
  for human tokens only for now.

## Quickstart

```bash
cd apps/barrins_identity
cp .env.example .env  # fill DATABASE_URL, JWT_PRIVATE_KEY, ALLOWED_ORIGINS
uv sync --group dev
uv run alembic upgrade head
uv run python scripts/create_admin.py --email admin@example.com
uv run uvicorn app.main:app --reload --port 8001
```

Generate a signing key for `.env`:

```bash
openssl genrsa 2048
```

## Tests

```bash
uv run pytest
uv run pytest --cov=app --cov-report=term-missing
```

Coverage gate: ≥ 92% overall, 100% on `app/models/` and `app/schemas/`.
