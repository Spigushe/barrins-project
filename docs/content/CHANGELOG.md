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

### front/tamiyo_scroll

#### Changed

- Translated `README.md` from French to English.
