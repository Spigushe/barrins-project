<!--
  Changelog fragment for feat/barrins_api.
  Not a standalone changelog — merge this section into the "back/barrins_api"
  part of docs/content/CHANGELOG.md's [Unreleased] block once all feature
  branches (this one, feat/docs, etc.) have landed. Delete this file after merging.
-->

### back/barrins_api

#### Added

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
- `.github/workflows/CI.yml`: path-filtered CI that only runs the
  `back` job (lint, security, type-check, tests via
  `scripts/workflow_ci.py`) when `apps/barrins_api/**` changes.
