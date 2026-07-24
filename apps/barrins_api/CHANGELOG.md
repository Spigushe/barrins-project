# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [1.0.0] "WorldWake" - 2026-07-24

### Added

- Initial scaffold of the Barrin's API backend (FastAPI, Python 3.14,
  PostgreSQL via async SQLAlchemy 2 + asyncpg, Alembic migrations,
  Pydantic v2 settings).
- Authentication (`/api/v1/auth`): JWT (HS256) login/refresh/logout,
  self-registration with email verification (`/auth/signup`,
  `/auth/signup/verify`, `/auth/signup/resend`), admin-only direct
  account creation, Argon2id password hashing, and a 5-level
  hierarchical role system (`anonymous` → `user` → `role_c` →
  `ml_developer` → `admin`) enforced via a `require_role(min_role)`
  dependency.
- Tamiyo Scroll BFF (`/bff/tamiyo-scroll`), a competitive MTG tracking
  API: user settings (read-only sharing), personal decks and
  versioned decklists (with Moxfield import), a metagame/opponent
  deck roster, a BO3 match log, card-test feedback, decklist coloring
  by test feedback, and aggregated archetype/matchup statistics.
- Email delivery service with a console sender for local development
  and an SMTP sender for production.
- `scripts/create_admin.py` to bootstrap the first admin account, and
  `scripts/workflow_ci.py` to run the full local CI pipeline (ruff,
  ty, pytest) outside of GitHub Actions.
- Alembic migrations: users/roles/tokens, auth email verifications,
  and the Tamiyo Scroll tracker tables.
- Test suite (pytest + pytest-asyncio + httpx) with a 90% global / 100%
  `app/models/` coverage floor.
- `docs/content/back/barrins_api/auth_roles.md`: documents the JWT
  authentication and hierarchical role-based access control system
  (role hierarchy, endpoint security matrix), replacing the ad hoc
  `X-Admin-Key` header.
- `docs/content/back/barrins_api/signup_email_verification.md`:
  documents the self-registration and email verification flow
  (`/auth/signup`, `/auth/signup/verify`, `/auth/signup/resend`).
- Nav entries (`docs/mkdocs.yml`) and `_links.md` sidecar links for the
  two pages above.
- `GET /health`: reports database connectivity (`200`/`503`), for
  external uptime monitoring — `503` covers both a failed query and a
  fully unreachable database (e.g. connection refused/rejected).
  Registered after `GET /` in `general/router.py` so `/docs` lists
  routes in that order.
- External uptime monitoring (HetrixTools) is live against `barrins_api`
  prod + staging `/health`, plus certificate-expiry alerting — see
  `docs/content/ops/operations/index.md`.
- Real Moxfield deck import (`app/services/moxfield/`): fetches a public
  deck from Moxfield's API, rate-limited to 1 request/second, replacing
  the earlier placeholder that only stored the given URL as text.
- API routes reorganized into one `app/api/<domain>/` package per domain
  (`general/`, `tamiyo_scroll/`), each owning its own router aggregator —
  replaced the previous `ts_router.py`/`bff/ts_router/` and
  `v1_router.py`/`v1/` split, which had a file and a differently-scoped
  directory sharing the same name.

### Changed

- Translated `README.md` from French to English.
