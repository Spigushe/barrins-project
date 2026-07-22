# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Within each release, changes are grouped by sub-repo (`docs`,
`back/barrins_api`, `back/barrins_identity`, `front/tamiyo_scroll`,
`front/tolaria_news`, `ops`), then by the standard Keep a Changelog
categories (Added, Changed, Deprecated, Removed, Fixed, Security). Only
sub-repos with actual changes appear in a given release.

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

#### Changed

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

#### Fixed

- `mkdocs.yml` had `docs_dir: content` pointing at a folder that did
  not exist; all documentation pages moved under `docs/content/` to
  match it.
- `mkdocs.yml` nav referenced `back/barrins_api/implementation.md`,
  which does not exist (the actual page is
  `back/barrins_api/bff/tamiyo_scroll.md`); also added the missing nav
  entries for `front/tamiyo_scroll/bootstrap.md` and the incidents
  pages, which were causing `mkdocs build --strict` to fail.

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

### ops

#### Added

- `.github/workflows/CI.yml`: path-filtered CI pipeline
  (`dorny/paths-filter`) that runs checks only for the parts of the
  monorepo a change actually touches — `back` (lint, security, types,
  tests via `uv run scripts/workflow_ci.py` for `barrins_api`/
  `barrins_identity`), `front` (`npm run lint`/`build`/`test` for
  `tamiyo_scroll`/`tolaria_news`), `ops` (`ansible-lint` for
  `ops/my-server`), and `docs` (markdownlint, cspell, `mkdocs build
  --strict`) — on every push/PR to `staging` and `main`. A
  `ci-required` job aggregates the per-job results into a single
  fail-closed status check, so branch protection has one check to
  depend on even though the individual jobs are conditionally skipped.
- `.github/dependabot.yml`: weekly dependency update PRs for
  `apps/barrins_api` (uv), `apps/tamiyo_scroll` (npm), `docs` (npm),
  and `.github/workflows` (github-actions), all targeting `staging` so
  updates go through the same CI gate as any other change before
  reaching `main`. Dependabot only ever opens pull requests — it never
  pushes commits directly to a branch.
- `.github/workflows/deploy-docs.yml`: manual (`workflow_dispatch`)
  MkDocs build-and-deploy workflow to GitHub Pages, intentionally kept
  out of the required CI checks. The hosting target (GitHub Pages +
  custom domain `docs.barrins-codex.org`) is a placeholder pending
  confirmation.

#### Changed

- `.github/workflows/CI.yml`: translated remaining French inline comments
  and step names to English.

### front/tamiyo_scroll

#### Fixed

- `vite.config.ts`: stubbed `VITE_API_BASE_URL` via Vitest's `test.env`
  so `src/api/client.ts` doesn't build requests against `"undefined"`
  during tests. The variable was only ever supplied by a local,
  gitignored `.env` file, so every CI run (including the `front` job
  for otherwise-unrelated Dependabot bumps) failed 6 `client.test.ts`
  tests with `TypeError: Invalid URL`.

#### Added

- Initial scaffold of the Tamiyo Scroll frontend (React 19, TypeScript,
  Vite, React Router, TanStack Query, Zod, TailwindCSS, shadcn/ui
  components).
- Authentication flow: login page, self-registration email verification
  page, and a `ProtectedRoute` guard backed by a session store
  consuming the `barrins_api` `/api/v1/auth` endpoints.
- Metagame tab: personal decks list with Moxfield decklist import, a
  meta/opponent deck roster, and aggregated archetype/matchup
  statistics sections.
- Suivi BO3 tab: match journal, new-match form, and card-test feedback
  section, backed by the BO3 match log and card-test BFF endpoints.
- Decklist tab: current decklist view (colored by card-test feedback)
  and version history section.
- Read-only "viewing owner" selector (header) and `active-deck-context`
  for sharing another user's data without allowing edits, per the
  BFF's read-only sharing settings.
- App shell layout with tab navigation, and a centralized typed API
  client (`src/api/client.ts`) with Zod-validated request/response
  schemas (`src/schemas/tamiyoScroll.ts`).
- Test suite (Vitest + Testing Library) covering the API client, card
  tests, active-deck context, match form, and card-tests section.

#### Changed

- Translated `README.md` from French to English.
- Translated remaining French UI text (labels, buttons, placeholders,
  error messages) and code comments across the app — `index.css`,
  `active-deck-context.tsx`, `lib/mtg-format.ts`,
  `schemas/tamiyoScroll.ts`, `LoginPage.tsx`, `VerifyEmailPage.tsx`,
  the decklist, metagame, and Suivi BO3 sections, `AppShell.tsx`,
  `lib/store.ts`, `lib/queryClient.ts`, `api/client.ts`,
  `api/viewingOwner.ts`, and `hooks/useViewingOwner.ts` — to English.
