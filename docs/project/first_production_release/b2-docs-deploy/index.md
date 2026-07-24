# B2. Docs site deployment playbook

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `ops/my-server` (new playbook + role) | / |
| **Initial date** | 2026-07-24 | / |
| **Status** | 🟡 Implemented, staging UAT confirmed, `ansible-lint` clean | production UAT (release-tag deploy) deferred to B6, not a blocker for B3 |
| **Source** | User request | GitHub Pages already hosts other, unrelated projects on this account — deploying this repo's docs there isn't isolated to this project alone |
| **Dependency** | none | standalone infra, like B1 — sequenced before B3 (release content/merge) by choice, not a hard dependency |

---

## Context

`docs/` (the mkdocs site) has no deployment mechanism on this repo's own
infrastructure today. An earlier `.github/workflows/deploy-docs.yml`
(manual GitHub Pages build-and-deploy, see `ops/my-server/CHANGELOG.md`'s
`[1.0.0]` "Added" section) was scaffolded early on but never actually
committed to this checkout, and its hosting target was always flagged
as "a placeholder pending confirmation" — this item resolves that.

**Decision: self-host on the same VPS as everything else, not GitHub
Pages.** The user already uses GitHub Pages for other, unrelated
projects on this account — GitHub Pages is one site per *repository*,
but deploying via a shared account workflow/action risks touching
those other projects' pages too, and isn't worth untangling when this
repo already has its own VPS and an established Ansible pattern for
exactly this shape of deploy (`barrins_api.yml`, `tamiyo_scroll.yml`).

## Design

- New playbook `ops/my-server/docs.yml`, domain
  `docs{{ env_suffix }}.barrins-codex.org` — same `env_suffix`/
  `deploy_env` pattern as every other playbook:
  `docs.barrins-codex.org` (production) /
  `docs-staging.barrins-codex.org` (staging).
- **Same options as `barrins_api.yml`/`tamiyo_scroll.yml`**:
  `-e deploy_env=staging|production`, plus either a branch
  (`-e docs_site_git_branch=...`) or a pinned release tag
  (`-e docs_site_release_tag=...`), production defaulting to the
  latest GitHub release tag (Constitution §25/§27).
- **New role, not a reuse of `react_frontend`.** The docs site's build
  toolchain is `uvx --with mkdocs-material mkdocs build --strict`
  (Python/`uv`, matching `barrins_api`'s toolchain) — nothing like
  `react_frontend`'s Node/`nvm`/`npm` pipeline. Forcing the mkdocs build
  through a Node-shaped role would mean stripping out most of what that
  role does and bolting on unrelated tooling; a small dedicated role
  (working name `docs_site`) mirroring `react_frontend`'s *structure*
  (clone at ref, build, symlink output, nginx vhost, `register_ssl`)
  but with a `uv`-based build step is more honest than forcing a fit.
  Static output (`docs/site/`) is served by nginx exactly like
  `react_frontend`'s `dist/` — no runtime process needed either way.
- DNS: A records for both `docs.barrins-codex.org` and
  `docs-staging.barrins-codex.org` → `146.59.146.57` (none exist yet,
  same pre-flight gap as every other domain added this release).

## Tasks

- [x] Build the `docs_site` role (clone at branch/tag, `uv`-based
      mkdocs build, static output served by nginx, `register_ssl`
      integration).
- [x] Write `ops/my-server/docs.yml` (same `deploy_env`/branch-or-tag
      option shape as `barrins_api.yml`/`tamiyo_scroll.yml`).
- [x] Add DNS A record for `docs-staging.barrins-codex.org` (confirmed
      working — `register_ssl` issued a certificate and the site is
      live). `docs.barrins-codex.org` (production) still needed.
- [x] Decide the fate of the never-committed `deploy-docs.yml` GitHub
      Actions workflow reference in `ops/my-server/CHANGELOG.md` — this
      item supersedes it; note that explicitly rather than leaving a
      dangling mention.
- [x] `ansible-lint ops/my-server` clean (`production` profile, run
      from the repo root via WSL — see the CI-vs-local discrepancy note
      below).
- [x] Document at `docs/content/ops/deployment/` (new page, following
      `backend.md`/`frontend.md`'s structure) and update
      `docs/content/ops/operations/index.md`'s open items.

Drive-by: extracted the shared GitHub PAT `pre_tasks` block into a
`github_token` role (this playbook became its fourth identical copy) —
see `ops/my-server/CHANGELOG.md`'s Added/Changed entries.

Drive-by bug found via CI, not local `ansible-lint`: the new
`github_token` role's shared, intentionally-unprefixed `github_token`
fact tripped `var-naming[no-role-prefix]` — fixed with a targeted
`noqa` (see `ops/my-server/CHANGELOG.md`'s Fixed entry). Also surfaced
a local-verification gotcha: running `ansible-lint .` from inside
`ops/my-server` silently processes 0 files ("0 files processed of 2
encountered") — `ansible-lint` must be run from the repo root as
`ansible-lint ops/my-server`, exactly matching
`.github/workflows/CI.yml`'s invocation, or it does not actually lint
anything despite reporting "Passed".

## Done statement

`docs.yml` deploys the mkdocs site to staging and production on this
repo's own VPS, with the same environment/branch/tag options as the
app playbooks; `ansible-lint` clean; documented.

## UAT (manual)

- [X] Deploy to staging; confirm `https://docs-staging.barrins-codex.org`
      serves the built site and reflects the current branch's content.
      *(Bug found on first attempt: the "Build the docs site" task
      carried a stray `become: false` copied from `fastapi_backend`'s
      `uv`-install pattern — but `docs_site` clones/builds as root like
      `react_frontend` and only hands ownership to `www-data` at the
      end, so the unprivileged user couldn't write into the root-owned
      checkout (`docs/hooks/sync_readmes.py`'s mkdocs pre-build hook
      regenerating `docs/content/back/barrins_api/index.md`).
      `PermissionError`, task failed outright. Fixed by dropping the
      stray `become: false`; confirmed on retest — `docs.yml -e
      deploy_env=staging -e docs_site_git_branch=proj/v1.0.0-bump` ran
      clean end to end, site live at
      `https://docs-staging.barrins-codex.org/`.)*
- [ ] Deploy to production from a release tag; confirm
      `https://docs.barrins-codex.org` serves that tag's content.
      **Deferred to B6**: needs a GitHub release tag, which doesn't
      exist until B5 (tag/cut the release) — B5/B6 both run after this
      item merges (B3/B4), so this can't complete now. Not required for
      B3; folded into B6's final production regression pass alongside
      `barrins_api.yml`/`tamiyo_scroll.yml`.

## Non-regression tests

- Automated: `ansible-lint ops/my-server` clean (existing CI gate).
- Manual: every other playbook (`barrins_api.yml`, `tamiyo_scroll.yml`,
  `tolaria_news.yml`, `postgresql_pgadmin.yml`) still runs unaffected —
  this is a net-new playbook/role, no shared file touched beyond
  `register_ssl` (already designed to be called once per domain,
  independently).
