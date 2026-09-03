# Barrin's API: Backend

FastAPI backend serving the **Tamiyo Scroll** BFF (Backend-For-Frontend) (competitive MTG
tracking: personal decks, opponent roster, match log, card test feedback) as well as
shared authentication (self-registration, email verification, JWT).

## Tech stack

| Component | Technology |
| --------- | ----------- |
| Framework | FastAPI (Python 3.14) |
| Database | PostgreSQL (asyncpg) |
| ORM | SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Authentication | JWT HS256 (`python-jose`) |
| Password hashing | Argon2id (`argon2-cffi`) |
| Validation | Pydantic v2 |
| Tests | pytest + pytest-asyncio + httpx |

## Endpoints

### Authentication (`/api/v1/auth`)

| Method | Path | Required role | Description |
| ------- | ------ | ----------- | ----------- |
| `POST` | `/auth/token` | — | Login — returns `access_token` + `refresh_token` |
| `POST` | `/auth/signup` | — | Self-registration — sends a verification code by email |
| `POST` | `/auth/signup/verify` | — | Validates the received code, activates the account and logs in |
| `POST` | `/auth/signup/resend` | — | Resends a new verification code |
| `POST` | `/auth/register` | `admin` | Direct account creation (already verified) |
| `GET` | `/auth/me` | `user` | Current user's profile |
| `POST` | `/auth/refresh` | — | Exchanges a refresh token for a new pair |
| `POST` | `/auth/logout` | `user` | Instant revocation of all tokens |

### Tamiyo Scroll — competitive MTG tracking BFF (`/bff/tamiyo-scroll`)

All routes require an authenticated user (`user`).

| Method | Path | Description |
| ------- | ------ | ----------- |
| `GET`/`PATCH` | `/tamiyo-scroll/me/settings` | User preferences (read-only sharing, active personal deck) |
| `GET` | `/tamiyo-scroll/shared-users` | Users who have shared their data as read-only |
| `GET`/`POST` | `/tamiyo-scroll/personal-decks` | List / creation of personal decks |
| `DELETE` | `/tamiyo-scroll/personal-decks/{id}` | Archives a personal deck |
| `GET`/`POST` | `/tamiyo-scroll/personal-decks/{id}/versions` | History / addition of decklist versions |
| `POST` | `/tamiyo-scroll/personal-decks/{id}/versions/import-moxfield` | Import a Moxfield decklist |
| `DELETE` | `/tamiyo-scroll/personal-decks/{id}/versions/{versionId}` | Deletes a version |
| `GET` | `/tamiyo-scroll/personal-decks/{id}/decklist-view` | Current decklist colored by test feedback |
| `GET` | `/tamiyo-scroll/personal-decks/{id}/versions/{versionId}` | Structured content of one specific past version |
| `GET` | `/tamiyo-scroll/personal-decks/{id}/versions/{versionId}/diff` | Card-level diff against the immediately-prior version |
| `GET`/`POST` | `/tamiyo-scroll/meta-decks` | Opponent roster (tracked metagame decks) |
| `PUT`/`DELETE` | `/tamiyo-scroll/meta-decks/{id}` | Update / archive a metagame deck |
| `GET`/`POST` | `/tamiyo-scroll/matches` | Match log (BO3) |
| `PUT`/`DELETE` | `/tamiyo-scroll/matches/{id}` | Update / delete a match |
| `GET`/`POST` | `/tamiyo-scroll/card-tests` | Card test feedback |
| `PUT`/`DELETE` | `/tamiyo-scroll/card-tests/{id}` | Update / delete a feedback entry |
| `GET` | `/tamiyo-scroll/archetype-summary` | Aggregated statistics by opponent archetype |
| `GET` | `/tamiyo-scroll/matchup-summary` | Matchup statistics (winrate, conversion) |

## Installation

```bash
# Clone and install (editable mode)
git clone https://github.com/spigushe/barrins-project.git
cd ./apps/barrins_api
uv sync --all-groups
```

## Configuration

Copy `.env.example` to `.env` and fill in the variables:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/barrins
IDENTITY_SERVICE_URL=http://localhost:8001
ENVIRONMENT=development
```

> Since the identity cutover (ADR-20) `barrins_api` no longer issues or
> decodes its own JWTs, has no `users` table, and sends no email —
> authentication, signup, verification and admin bootstrap all live in
> `apps/barrins_identity`. `barrins_api` verifies the `Bearer` locally
> against `IDENTITY_SERVICE_URL`'s JWKS (`libs/identity_client`).

## Migrations

```bash
# Apply all migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

## Tests

```bash
# Full suite with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Unit tests only (no PostgreSQL)
pytest tests/ -m "not integration"
```

The minimum coverage threshold is set at **90%** (global) and **100%** on `app/models/`.

## Project structure

```text
app/
  api/general/               # health, mtgjson, card-images, karn-internal
  api/tamiyo_scroll/         # Tamiyo Scroll BFF: settings, personal_decks,
                             # meta_decks, matches, card_tests, stats, teams
  config/             # Pydantic Settings (BaseAppSettings, AppSettings)
  core/               # roles (StrEnum), error handling, logging
  database/           # SQLAlchemy connection, session
  dependencies/       # get_current_user (identity JWKS), require_role
  models/             # ORM: TS* (Tamiyo Scroll), bs_*, mj_*, kt_*
  schemas/            # Pydantic response/request models
  services/
    identity_directory.py  # batch {username, display_name} lookup vs barrins_identity
    tamiyo_scroll/          # ownership (read-only sharing), stats, decklist coloring
alembic/versions/     # Migrations
scripts/
  migrate_users_to_identity.py  # one-shot users -> barrins_identity copy (ADR-20)
  workflow_ci.py                # Local CI pipeline (ruff, ty, pytest)
tests/
```

## Roles and access levels

| Level | Role | Scope |
| ------ | ---- | --------- |
| 0 | `anonymous` | Public read (sets, cards, prices) |
| 1 | `user` | + personal profile, logout |
| 2 | `role_c` | Placeholder — to be defined |
| 3 | `ml_developer` | Read access to DB statistics (`/db-stats`) + raw ML feature matrix |
| 4 | `admin` | Everything, including MTGJSON import and account creation |

The `require_role(min_role)` factory compares ordinal levels — a role of level N satisfies
any constraint of level ≤ N.
