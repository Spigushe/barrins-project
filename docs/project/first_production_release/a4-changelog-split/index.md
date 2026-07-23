# A4. Split the changelog per app, aggregate at mkdocs build time

[← Back to project index](../index.md)

## Context

Today `docs/content/CHANGELOG.md` is a single hand-maintained file,
already organized by sub-repo (`docs`, `back/barrins_api`,
`back/barrins_identity`, `front/tamiyo_scroll`, `front/tolaria_news`,
`ops`) then by Keep-a-Changelog category. This item relocates the source
of truth to one `CHANGELOG.md` per sub-repo, replaces the single
`docs/content/CHANGELOG.md` page with a `docs/content/changelog/`
section, and generates both the per-app pages and a "latest changes"
summary page at build time via a new, dedicated hook (kept separate from
`sync_readmes.py` for clarity).

## Design

- **Source of truth**: one `CHANGELOG.md` per sub-repo —
  `apps/barrins_api/CHANGELOG.md`, `apps/barrins_identity/CHANGELOG.md`,
  `apps/tamiyo_scroll/CHANGELOG.md`, `apps/tolaria_news/CHANGELOG.md`,
  `docs/CHANGELOG.md`, `ops/my-server/CHANGELOG.md` — just
  Keep-a-Changelog entries, no preamble repeated per file.
- **Docs site structure** (flat files under `changelog/`, no per-app
  subdirectory):
  - `docs/content/changelog/index.md` (generated) — "Home": a
    medium-length SemVer + Keep a Changelog explanation, followed by a
    **"Latest changes"** section aggregating, per sub-repo, only the
    entries for the last released version. "Last version" is resolved
    from the **latest git tag** (`vX.Y.Z`), not whichever section sits at
    the top of a file — avoids surfacing `[Unreleased]` notes as if
    shipped.
  - `docs/content/changelog/<subrepo>.md` (generated, flat, one per
    sub-repo) — e.g. `changelog/barrins_api.md` — a straight synced copy
    of that sub-repo's full `CHANGELOG.md` (complete history).
  - `docs/mkdocs.yml` nav:

    ```yaml
    - Changelog:
          - Home: changelog/index.md
          - Barrin's API: changelog/barrins_api.md
          - Barrin's Identity: changelog/barrins_identity.md
          - Tamiyo Scroll: changelog/tamiyo_scroll.md
          - Tolaria News: changelog/tolaria_news.md
          - Ops: changelog/ops.md
          - Docs: changelog/docs.md
    ```

- **New hook**: `docs/hooks/sync_changelogs.py`, registered alongside
  `sync_readmes.py`. `on_pre_build`: copies each sub-repo `CHANGELOG.md`
  verbatim into `changelog/<subrepo>.md`; builds `changelog/index.md`
  from a tracked intro partial (`changelog/_intro.md`, excluded from nav
  like `_links.md`) plus the tag-resolved "Latest changes" aggregation.
  `on_shutdown` removes generated files, mirroring `sync_readmes.py`.
- `docs/content/CHANGELOG.md` (old single file) is deleted; its intro
  text moves into `changelog/_intro.md`.
- `.gitignore`: add the generated `changelog/index.md` and
  `changelog/*.md` (excluding `_intro.md`).
- CI: extend the `docs` job's markdownlint/cspell exclusions to the
  generated changelog pages.

## Tasks

- [ ] Create per-sub-repo `CHANGELOG.md` files from the current content.
- [ ] Write `docs/hooks/sync_changelogs.py`.
- [ ] Write `docs/content/changelog/_intro.md`.
- [ ] Delete `docs/content/CHANGELOG.md`.
- [ ] Update `docs/mkdocs.yml` nav + hooks registration.
- [ ] Update `.gitignore` and CI lint exclusions.

## Done statement

Per-sub-repo `CHANGELOG.md` files exist; `sync_changelogs.py`
implemented; `docs/content/changelog/` builds correctly via
`mkdocs build --strict`; the old single `CHANGELOG.md` is removed.

## UAT (manual)

- [ ] Run `mkdocs serve` locally; browse to the Changelog section;
      confirm Home shows the intro text plus a "Latest changes" section
      matching the actual latest `vX.Y.Z` tag, and each app's page shows
      its full history.
- [ ] Delete a generated changelog page by hand, rerun the build, confirm
      the hook regenerates it; stop `mkdocs serve` and confirm
      `on_shutdown` removes the generated files again.

## Non-regression tests

- Automated: `docs` CI job (markdownlint/cspell/`mkdocs build --strict`)
  still passes.
- Manual: every other nav section (Backend, Frontend, Ops) still renders
  unaffected by the new hook running alongside `sync_readmes.py`.
