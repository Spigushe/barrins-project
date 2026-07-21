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

#### Fixed

- `mkdocs.yml` had `docs_dir: content` pointing at a folder that did
  not exist; all documentation pages moved under `docs/content/` to
  match it.
- `mkdocs.yml` nav referenced `back/barrins_api/implementation.md`,
  which does not exist (the actual page is
  `back/barrins_api/bff/tamiyo_scroll.md`); also added the missing nav
  entries for `front/tamiyo_scroll/bootstrap.md` and the incidents
  pages, which were causing `mkdocs build --strict` to fail.
