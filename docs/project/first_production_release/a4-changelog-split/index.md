# A4. Split the changelog per app, aggregate at mkdocs build time

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/` | (all 6 sub-repos' `CHANGELOG.md`) |
| **Initial date** | 2026-07-23 | / |
| **Status** | ✅ Implemented | one UAT item blocked until `v1.0.0` is tagged (B5) |
| **Source** | Docs maintenance | single hand-maintained `CHANGELOG.md` became unwieldy across 6 sub-repos |
| **Dependency** | B5 (tag) | for the "Latest changes" UAT check only, not the implementation |

---

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
- CI/local lint: generated pages don't exist yet when markdownlint/cspell
  run (they run *before* the `mkdocs build` step, same as the pre-existing
  README-sync generated `index.md` pages — no exclusion needed for them).
  `_intro.md` itself, however, **is** a tracked fragment (no H1, not a
  standalone page) — excluded from both tools exactly like `_links.md`
  already is, in `docs/package.json` and `.github/workflows/CI.yml`.

## Tasks

- [x] Create per-sub-repo `CHANGELOG.md` files from the current content
      (`apps/{barrins_api,barrins_identity,tamiyo_scroll,tolaria_news}/CHANGELOG.md`,
      `docs/CHANGELOG.md`, `ops/my-server/CHANGELOG.md`).
- [x] Write `docs/hooks/sync_changelogs.py`.
- [x] Write `docs/content/changelog/_intro.md`.
- [x] Delete `docs/content/CHANGELOG.md`.
- [x] Update `docs/mkdocs.yml` nav + hooks registration.
- [x] Update `.gitignore`; exclude `_intro.md` from markdownlint/cspell in
      both `docs/package.json` and `.github/workflows/CI.yml`.
- [x] Added 5 missing dictionary words to `docs/cspell.json` surfaced by
      the new/relocated content (`Brevo`, `DMARC`, `Hetrix`, `automount`,
      `chdir`, `fmask`).
- [x] Verified: `mkdocs build --strict` clean, generated pages contain
      the expected content (spot-checked `changelog/index.md`'s "no tag
      yet" fallback and `changelog/barrins_api.md`'s real entries),
      `npm run lint`/`spellcheck` clean on all new files.

## Done statement

Per-sub-repo `CHANGELOG.md` files exist; `sync_changelogs.py`
implemented; `docs/content/changelog/` builds correctly via
`mkdocs build --strict`; the old single `CHANGELOG.md` is removed.

## UAT (manual)

- [ ] **Blocked until the `v1.0.0` tag exists** (no tag exists yet — cf.
      "ça reste 1.0.0 tant que le commit n'est pas tag"; `git tag -l` is
      currently empty). Before that, "Latest changes" only has the
      "no tag yet" fallback to check, not the real aggregation. Run
      `mkdocs serve` locally; browse to the Changelog section; confirm
      Home shows the intro text plus a "Latest changes" section
      matching the actual latest `vX.Y.Z` tag, and each app's page shows
      its full history.
- [X] Delete a generated changelog page by hand, rerun the build, confirm
      the hook regenerates it; stop `mkdocs serve` and confirm
      `on_shutdown` removes the generated files again.

## Non-regression tests

- Automated: `docs` CI job (markdownlint/cspell/`mkdocs build --strict`)
  still passes.
- Manual: every other nav section (Backend, Frontend, Ops) still renders
  unaffected by the new hook running alongside `sync_readmes.py`.
