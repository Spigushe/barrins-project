# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Within each release, changes are grouped by sub-repo (`docs`,
`back/barrins_api`, `back/barrins_identity`, `back/karn_tablets`,
`front/tamiyo_scroll`, `front/tolaria_news`, `front/goblin_guide`, `ops`),
then by the standard Keep a Changelog categories (Added, Changed,
Deprecated, Removed, Fixed, Security). Only sub-repos with actual changes
appear in a given release.

## [Unreleased]

### docs

#### Added

- CI-runnable local scripts (`docs/package.json`): `npm run lint`,
  `npm run spellcheck`, `npm run build`, and `npm run ci`, mirroring
  the `docs` job in `.github/workflows/CI.yml` so the same checks can
  run from a terminal without waiting on CI.
- `docs/cspell.json`, a real cspell config the CLI can read (spelling
  exceptions previously only lived in `.vscode/settings.json`, which
  the standalone `cspell` CLI does not parse).
- This changelog, following Keep a Changelog and Semantic Versioning.
- `docs/hooks/sync_readmes.py`, an `on_pre_build` mkdocs hook that
  copies each `apps/<app>/README.md` into its
  `docs/content/**/<app>/index.md` page at build time, so app READMEs
  and their docs page never drift. A sibling `_links.md` file per page
  preserves the curated nav links (e.g. to `bff/tamiyo_scroll.md`,
  `bootstrap.md`, `incidents/index.md`) that used to live directly in
  `index.md`; those sidecars are excluded from the built site via
  `exclude_docs` in `mkdocs.yml`.
- Root `.gitignore`: ignores the mkdocs-generated `index.md` pages,
  the `docs/site/` build output, and Python `__pycache__`/`*.pyc`
  files (produced by the new build hook).
- `on_shutdown` hook in `docs/hooks/sync_readmes.py`: deletes the
  generated `index.md` pages when the hook shuts down, since
  `mkdocs serve` keeps rewriting them on every reload but never
  removes them on its own.
- Root `CLAUDE.md` and `CHANGELOG.md` aliases (`@docs/content/CLAUDE.md`,
  `@docs/content/CHANGELOG.md`), so both are discoverable from the repo
  root without duplicating their content.
- `docs/content/CLAUDE.md` §16.4 "Tests-first sequencing": tests must be
  planned, confirmed by the user, and implemented before the
  corresponding production logic is built.
- Frontend documentation landing pages for `tolaria_news` and
  `goblin_guide`, including the new `docs/content/front/tolaria_news/`
  and `docs/content/front/goblin_guide/` index pages and their linked
  navigation sidecars, so the docs site reflects the current app split
  between backend planning and frontend-facing experiences.
- `docs/content/CLAUDE.md` §21.3 "Relative links in app READMEs":
  documents the constraint that `apps/<app>/README.md` files render in
  two different locations with two different base paths — directly on
  GitHub, and copied by `docs/hooks/sync_readmes.py` into their
  generated `docs/content/**/<app>/index.md` page — so a single
  relative link cannot be correct in both. App READMEs must reference
  other docs pages in prose only; the sibling `_links.md` file is the
  only place raw cross-page links belong.
- `docs/content/back/karn_tablets/` docs page (`_links.md` linking to
  `front/tolaria_news/platform.md` §3 and `back/barrins_identity/`'s
  platform/tests docs, plus the corresponding `mkdocs.yml` nav entry
  and `back/index.md` listing), giving
  `docs/hooks/sync_readmes.py` a target to sync
  `apps/karn_tablets/README.md` into.

#### Changed

- `docs/content/CLAUDE.md` §40 "Authentication Future Evolution":
  replaced the earlier "wait for a second account-based app, build
  OAuth2/OIDC" guidance with the validated decision to extract
  `barrins-identity` now as a JWT RS256 + JWKS service.
- `docs/package.json`: merged `spellcheck` and `spellcheck-app` into a
  single `spellcheck` script covering both `content/**/*.md` and
  `../apps/**/*.md`.
- `.github/workflows/CI.yml`: excluded `_links.md` sidecar files from
  the `markdownlint` and `cspell` steps (they intentionally start with
  a bullet list rather than a heading).
- `docs/cspell.json`: added the technical terms and proper nouns
  introduced while translating app READMEs and wiring the README sync
  hook (`asyncpg`, `cffi`, `decklist`, `getpass`, `metagame`,
  `Moxfield`, `MTGJSON`, `mypy`, `oxlint`, `pytest`, `Resends`,
  `venv`, `winrate`/`winrates`, among others).
- `docs/cspell.json`: removed the blanket `*.yml` ignore in favor of a
  `!docs/**/*.{yml,yaml}` exception (so files like `docs/mkdocs.yml`
  are spell-checked) and added `**/*.toml` to `ignorePaths`; added
  terms surfaced by the new auth/signup documentation (`checkfirst`,
  `passlib`, `pyproject`, `Referer`, `STARTTLS`, `userrole`, `VARCHAR`,
  among others).
- `docs/hooks/sync_readmes.py`: docstring now states the relative-link
  constraint explicitly, next to the mechanism that causes it (see
  `docs/content/CLAUDE.md` §21.3).
- `docs/content/back/index.md`: added Karn Tablets to the backend app
  list.

#### Fixed

- `mkdocs.yml` had `docs_dir: content` pointing at a folder that did
  not exist; all documentation pages moved under `docs/content/` to
  match it.
- `mkdocs.yml` nav referenced `back/barrins_api/implementation.md`,
  which does not exist (the actual page is
  `back/barrins_api/bff/tamiyo_scroll.md`); also added the missing nav
  entries for `front/tamiyo_scroll/bootstrap.md` and the incidents
  pages, which were causing `mkdocs build --strict` to fail.
- Root `.gitignore`: added the missing generated-`index.md` entries for
  `front/tolaria_news` and `front/goblin_guide` (both already had doc
  pages but were absent from the ignore list) alongside the new
  `back/karn_tablets/index.md`.

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
- `docs/content/back/barrins_api/auth_roles.md`: documents the JWT
  authentication and hierarchical role-based access control system
  (role hierarchy, endpoint security matrix), replacing the ad hoc
  `X-Admin-Key` header.
- `docs/content/back/barrins_api/signup_email_verification.md`:
  documents the self-registration and email verification flow
  (`/auth/signup`, `/auth/signup/verify`, `/auth/signup/resend`).
- Nav entries (`docs/mkdocs.yml`) and `_links.md` sidecar links for the
  two pages above.

#### Changed

- Translated `README.md` from French to English.

#### Fixed

- `app/main.py`: replaced the deprecated `AsyncIterator` return-type
  annotation on the `lifespan` context manager with `AsyncGenerator`,
  per `@asynccontextmanager`'s updated typing guidance.

### back/karn_tablets

#### Added

- `README.md`: placeholder for the periodic ML/analytics calculation
  backend described in `front/tolaria_news/platform.md` §3 — reads
  tournament/decklist data from `barrins_api` and writes computed
  results back. Flags the same five open items (app name/location,
  auth mechanism, schedule, write-back payload shape, underlying data
  pipeline) as informational-only, pending confirmation.

### back/barrins_identity

#### Changed

- `platform.md` rewritten from a "future consideration" proposal
  (OAuth2/OIDC, deferred until a second account-based app existed) into
  an implementation plan: JWT RS256 + JWKS, `client_credentials`-style
  service accounts, adapted for this monorepo's existing
  `apps/barrins_identity/` scaffold (no separate repo needed). Documents
  the RS256-vs-HS256 and revocation-TTL decisions, the target
  architecture, configuration, data model (`User`, `ServiceAccount`,
  `role_c` → `moderator` rename), routes, the `barrins_api` cutover plan,
  and three open questions (shared vs. copy-per-app `identity_client/`,
  `tolaria_news` scope, final role name) that need confirming before
  implementation.
- `README.md`: corrected the stale "OAuth service" label.

#### Added

- `tests.md`: dedicated test plan (coverage targets, required negative
  cases, the `barrins_api` contract test, manual verification commands),
  kept separate from `platform.md` per the tests-first rule so it can be
  reviewed and confirmed on its own before implementation starts.

### front/tamiyo_scroll

#### Changed

- Translated `README.md` from French to English.

### front/tolaria_news

#### Added

- `platform.md`: documents `tolaria_news`'s frontend architecture — its
  two direct backend dependencies (`barrins_api` for tournament/report
  data via BFF routes, not yet built; `barrins_identity` for
  authentication) — plus, as backend-side detail the frontend never
  calls directly, the companion periodic-calculation backend (proposed
  `apps/karn_tablets/`, name unconfirmed) that reads tournament/decklist
  data from `barrins_api` and writes computed results back. Flags five
  open items on the calculation backend (app name, auth mechanism,
  schedule, write-back payload shape, missing underlying data pipeline)
  and one on the frontend (own login UI vs. embedding `goblin_guide` as
  a widget) rather than assuming answers. Originally drafted at
  `back/tolaria_news/platform.md` and moved here once it became clear
  `tolaria_news` itself is a frontend app.

### front/goblin_guide

#### Added

- `bootstrap.md`: placeholder documentation for Goblin Guide, the
  planned login/account UI for Barrin's Identity — stack,
  standalone-vs-widget shape, and pages/flows are explicitly left open.
- `apps/goblin_guide/README.md`: placeholder app scaffold (README only,
  no code), matching the convention used for `barrins_identity` and
  `tolaria_news`.
