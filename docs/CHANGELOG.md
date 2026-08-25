# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [2.0.0-alpha.2] - 2026-08-25

### Added

- `docs/cspell.json`: technical terms introduced by S8's MTGJSON
  pipeline, F10's roster-scope migration, and this cut's ops/deployment
  doc updates (`Barrin`, `checkpointing`, `datname`, `dawidd`, `ILIKE`,
  `lookback`, `lsclusters`, `macrotype`, `mainboard`, `ondelete`,
  `pipefail`, among others).

### Changed

- `docs/content/CLAUDE.md`: new §11.8 ("Deletion & archival semantics")
  — every user-triggered delete defaults to an archive, not a physical
  removal (Constitution Amendment Proposal 8, accepted 2026-08-24, S17/
  S18 fallout); cross-referenced from §51's data-retention section so
  the two don't read as contradictory.
- `docs/content/back/barrins_api/auth_roles.md`: endpoint-security
  matrix updated for S8's MTGJSON routes (`POST /mtgjson/import`
  now also accepting the scheduled-refresh service token, `GET
  /mtgjson/import/status`, `GET /mtgjson/status`, `GET /sets/*`, `GET
  /cards/*`) and S4's Scryfall image proxy (`GET
  /cards/{scryfall_id}/image`).
- `docs/content/back/barrins_api/bff/tamiyo_scroll.md`: decklist-coloring
  section updated for S4's structured `ResponseDecklistView` (commander/
  library split, card-type sort/grouping shared with `tolaria_news`),
  superseding the old flat line-array description.
- `docs/content/front/tamiyo_scroll/bootstrap.md`: route-map table and
  option-A comparison updated for the `/app` prefix flattening
  (2026-08-24), with a note pointing to `App.tsx` as the authoritative
  current route list rather than this (partial, original-scope) table.
- `docs/content/ops/deployment/backend.md`: documents the new
  `MTGJSON_IMPORT_TOKEN` production secret and adds health-check/
  troubleshooting steps for the daily MTGJSON-refresh timer.

## [2.0.0-alpha] - 2026-08-03

### Added

- `docs/mkdocs.yml`: nav entry for the new Tamiyo Scroll feature roadmap
  page (`front/tamiyo_scroll/roadmap.md`), the source of S12's bundled
  UI/UX polish items.
- `docs/cspell.json`: technical terms and proper nouns introduced while
  planning/documenting v2.0.0 (`banlist`, `consitution`, `deploiement`,
  `flowable`, `Karn`, `métrique`, `MTGO`, `paraparser`, `signups`,
  `skillset`, `unvalidated`, `Weasy`/`weasyprint`, `workstreams`, among
  others).

## [1.0.0] "WorldWake" - 2026-07-24

### Added

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
- `docs/hooks/sync_readmes.py` extended to also sync each
  `ops/my-server/roles/<role>/README.md` into
  `docs/content/ops/roles/<role>/index.md` (target directories created
  and cleaned up on demand, since — unlike the app pages — no
  `_links.md` sidecar pre-creates them). New **Ops → Roles** nav
  section (`docs/mkdocs.yml`, placed after Deployment) and
  `docs/content/ops/roles/index.md` overview page link the eight
  generated role pages; `.gitignore` and the generated-marker comment
  in the hook itself were generalized to cover both README sources.
- `on_shutdown` hook in `docs/hooks/sync_readmes.py`: deletes the
  generated `index.md` pages when the hook shuts down, since
  `mkdocs serve` keeps rewriting them on every reload but never
  removes them on its own.
- `docs/hooks/sync_changelogs.py`: a second `on_pre_build` hook, mirroring
  `sync_readmes.py`'s pattern, that copies each sub-repo's own
  `CHANGELOG.md` into `docs/content/changelog/<subrepo>.md` and builds
  `docs/content/changelog/index.md` (a tracked `_intro.md` partial plus a
  "Latest changes" section aggregated from whichever `[X.Y.Z]` section
  matches the latest `vX.Y.Z` git tag). Replaces the single hand-maintained
  `docs/content/CHANGELOG.md` this entry itself used to live in.

### Changed

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
- `docs/cspell.json`: added `subdir`, introduced by the new
  `*_repo_subdir` Ansible role variable documented below (ops
  section).

### Fixed

- `mkdocs.yml` had `docs_dir: content` pointing at a folder that did
  not exist; all documentation pages moved under `docs/content/` to
  match it.
- `mkdocs.yml` nav referenced `back/barrins_api/implementation.md`,
  which does not exist (the actual page is
  `back/barrins_api/bff/tamiyo_scroll.md`); also added the missing nav
  entries for `front/tamiyo_scroll/bootstrap.md` and the incidents
  pages, which were causing `mkdocs build --strict` to fail.
