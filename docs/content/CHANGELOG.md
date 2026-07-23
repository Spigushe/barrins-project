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
- `docs/cspell.json`: added `subdir`, introduced by the new
  `*_repo_subdir` Ansible role variable documented below (ops
  section).

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
- Ansible VPS deployment (`ops/my-server/`), moved in-repo from the
  previous separate `Spigushe/myserver` repository (now deprecated) so
  infrastructure changes land alongside the application changes that
  require them (Constitution §26.1). Playbooks: `initial.yml`,
  `setup.yml`, `barrins_api.yml`, `tamiyo_scroll.yml`,
  `tolaria_news.yml`; roles: `create_ssh_key`, `setup_base_user`,
  `setup_packages`, `register_ssl`, `backend_website`,
  `react_frontend`, `fastapi_backend`. `scripts/check_no_secrets_committed.sh`
  guards against ever staging a real secrets file. Documented under
  the new Constitution §38-mandated `docs/content/ops/` tree
  (`architecture/independence.md`, `architecture/decisions.md` for the
  ADRs below, `deployment/{backend,frontend,rollback}.md`,
  `security/secrets.md`, `operations/index.md` — the last honestly
  documenting current gaps: no health endpoint, no monitoring, no
  tested backups).
- `ops/my-server/postgresql_pgadmin.yml` and the `pgadmin` role: a
  Docker-based pgAdmin4 deployment/administration playbook (isolated
  Docker network, `pg_hba.conf`/`listen_addresses` wiring, weekly
  auto-update timer, `unattended-upgrades` for the host), porting the
  `pgadmin` role from myserver's unmerged
  `postgresql-pgadmin-playbook` branch. PostgreSQL itself is already
  installed by `setup_packages` at host bootstrap; this playbook only
  exposes it via pgAdmin. Documented at
  `docs/content/ops/deployment/database.md`.

#### Changed

- `.github/workflows/CI.yml`: translated remaining French inline comments
  and step names to English.
- Constitution §34 (Secrets Management), applied while moving
  `ops/my-server/` in-repo and decided with the user rather than
  guessed (§16.2, recorded as an ADR in
  `docs/content/ops/architecture/decisions.md`): backend `.env` files
  are local-only and git-ignored
  (`ops/my-server/secrets/**/*.env`), never committed even encrypted.
  `fastapi_backend`'s `fastapi_backend_env_file` step uses one if present on the
  operator's machine, skips gracefully otherwise.
- Constitution §25/§27/§31 (Release Policy), same ADR process:
  production deploys resolve the latest GitHub release tag by default
  (`fastapi_backend_use_release_tag`/`react_frontend_use_release_tag`, wired to
  `deploy_env == 'production'` in every playbook), or a pinned tag for
  rollback. Staging keeps deploying a branch, since it exists to
  preview code before release.
- `.gitignore` and `scripts/check_no_secrets_committed.sh`
  generalized: allow-list `secrets/**/*.example` and `README.md`
  instead of listing each secret filename individually, so a new
  secret file (e.g. pgAdmin's admin password) is caught by default
  without a new gitignore line.
- Constitution §26.1 (Infrastructure objective): added an explicit
  "one application, one playbook" rule — a frontend playbook must
  never embed a backend role invocation (or vice versa), and running
  one app's playbook must never touch another's systemd service,
  nginx vhost, or database. Decided with the user (§16.2) after
  `tolaria_news.yml`'s embedded-backend exception (see Fixed below)
  was judged to need fixing rather than being grandfathered.

#### Fixed

- `.github/workflows/CI.yml`: the `back` job never provisioned a
  Postgres service or a real `SECRET_KEY`, so any PR touching
  `apps/barrins_api` was doomed to fail — `pytest` errors out while
  `tests/conftest.py` imports `app.config.settings` (the placeholder
  `SECRET_KEY` is rejected), and even past that the session-scoped
  `test_engine` fixture needs a reachable database. This went
  unnoticed because no PR had touched `apps/barrins_api` since the CI
  pipeline was wired up. Added a `postgres:17` service container
  (`localhost:5432`, health-checked via `pg_isready`), job-level
  `DATABASE_URL`/`TEST_DATABASE_URL` env vars pointing at it, and a
  step generating an ephemeral `SECRET_KEY` via `openssl rand -hex 32`
  before `workflow_ci.py` runs.
- `ops/my-server` playbooks/roles/READMEs: `become: 'no'`/`'yes'` (and
  `gather_facts`/`update`/`force`/`recurse`/`daemon_reload`/`enabled`/
  `update_cache` using the same quoted-string pattern) are YAML
  strings, not booleans — schema/lint tools correctly flagged them as
  "Incorrect type. Expected boolean." Replaced every instance with
  real `true`/`false`.
- `.github/workflows/CI.yml`: the `ops` job ran `ansible-lint
  ops/myserver` — the original scaffold's placeholder path (marked `#
  TO UPDATE`) that nobody updated once the real Ansible deployment
  landed at `ops/my-server/` — so the job failed outright
  (`ops/myserver: File or directory not found`). Corrected the path.
  The new `docs/content/ops/**` tree also never passed the `docs`
  job's actual checks: cspell didn't know `fastapi`, `pgadmin`,
  `certbot`, `journalctl`, `frontends`, `spigushe`, `uvicorn`, `HSTS`,
  `vhosts`, `dpage`, `certonly`, `creatordate`, `nohostname`,
  `inlines`, `ciphertext`, `FQCN`, or `keypair` (added to
  `docs/cspell.json`), and `deployment/backend.md` had a code-block
  line over the 80-char `MD013` limit.
- `ops/my-server`: fixing the `ansible-lint` path above revealed the
  playbooks/roles themselves failed the same job hard — 114
  failures + 33 warnings across 38 files, none of it caught before
  since this was the first time `ansible-lint` actually reached
  `ops/my-server` (see the path bug above). Brought it to a clean
  pass at ansible-lint's `production` profile (`ops` CI only requires
  `min`):
  - **`fqcn`** (73×): every builtin module action FQCN-prefixed
    (`ansible.builtin.copy`, not `copy`).
  - **`syntax-check[unknown-module]`** (2×): `openssh_keypair` and
    `authorized_key` moved out of `ansible.builtin` — switched to
    `community.crypto.openssh_keypair`/`ansible.posix.authorized_key`
    and added `ops/my-server/requirements.yml` declaring both
    collections (`ansible-galaxy collection install -r
    requirements.yml`, also wired into the `ops` CI job before
    linting).
  - **`role-name`** (7×): renamed every hyphenated role directory to
    snake_case (`fastapi-backend` → `fastapi_backend`,
    `react-frontend` → `react_frontend`, `backend-website` →
    `backend_website`, `create-ssh-key` → `create_ssh_key`,
    `register-ssl` → `register_ssl`, `setup-base-user` →
    `setup_base_user`, `setup-packages` → `setup_packages`) and
    updated every reference across playbooks and docs.
  - **`var-naming[no-role-prefix]`** (56× once the roles above had
    valid names — the rule doesn't check unnamed roles): every
    role-input var and internal computed-config dict renamed to carry
    the *full* role name as prefix — abbreviations like `fb_repo`
    became `fastapi_backend_repo`; the bare single-letter config dicts
    (`r`, and `pgadmin`'s own `r`) became `<role>_config`
    (`fastapi_backend_config`, `pgadmin_config`, etc.).
  - **`risky-file-permissions`** (8×): explicit `mode:` added to every
    `template`/`copy` task that lacked one.
  - **`yaml[octal-values]`** (4×): `mode: 0755`/`0600` quoted
    (`"0755"`/`"0600"`).
  - **`no-changed-when`** (4×): explicit `changed_when` added to
    `command`/`shell` tasks that always reported "changed".
  - **`package-latest`** (1×): the `pip` fallback install now pins
    `state: present` instead of `latest`, consistent with installing
    from a `requirements.txt` in the first place.
  - **`name`** (9×): missing play/task names added; the one task name
    embedding a Jinja expression mid-string moved it to the end.
  - **`jinja[spacing]`** (33× warnings): `{{var}}` → `{{ var }}`
    throughout, including `.j2` templates (not part of the lint gate,
    fixed for consistency while touching the surrounding code).
  Verified with `ansible-playbook --syntax-check` on all six top-level
  playbooks (`ansible-lint` itself needs the POSIX `grp` module and
  doesn't run natively on Windows — validated from a WSL/Linux venv).
  New Constitution subsection
  (`docs/content/CLAUDE.md` §26.4, "Ansible coding standards")
  distills these rules for future playbook/role work.
- `ops/my-server/roles/fastapi_backend`, `react_frontend`:
  `fastapi_backend_repo`/`react_frontend_repo` in `barrins_api.yml`,
  `tamiyo_scroll.yml`, `tolaria_news.yml` pointed at
  `barrins-project/barrins_api`, `barrins-project/tamiyo_scroll`,
  `barrins-project/tolaria_news` — repos that don't exist; the apps
  actually live under `apps/<name>/` in this monorepo
  (`Spigushe/barrins-project`). The first deploy would have failed at
  the `git clone` step. Both roles gained a `*_repo_subdir` var: the
  full repo is still cloned to `app_root`/`site_root`, but dependency
  detection/install, the deployed `.env`, the build command, and the
  systemd `WorkingDirectory` now resolve against
  `<root>/<repo_subdir>`; the three playbooks were repointed at
  `Spigushe/barrins-project` with the matching `apps/<name>` subdir.
  Also surfaced and fixed a related latent bug: `react_frontend`'s
  `dist` symlink task only fired when `build_dir != 'dist'`, which
  would have silently served nothing once a subdir is introduced
  (build output lands at `<site_root>/<subdir>/dist`, not
  `<site_root>/dist`) — the condition now compares full resolved
  paths instead.
- `ops/my-server/roles/register_ssl/tasks/main.yml`: the role's own
  README documents templating `/etc/nginx/snippets/ssl-params.conf` as
  step 1 — shared by every HTTPS-serving role via
  `include snippets/ssl-params.conf;` (`backend_website`,
  `react_frontend`, `pgadmin`) — but the task that actually templates
  it was dropped when the Ansible deployment moved in-repo; `tasks/main.yml`
  went straight from the HTTP vhost to reload to certbot. Any HTTPS
  vhost reload on a host missing that snippet failed nginx's config
  test outright (`open() "/etc/nginx/snippets/ssl-params.conf" failed
  (2: No such file or directory)`), surfaced when deploying
  `barrins_api.yml -e deploy_env=staging` to a fresh domain. Restored
  the missing task, ordered first as the README already described.
- Two WSL-specific gotchas surfaced while diagnosing the above from a
  `/mnt/c` (DrvFs) checkout, not repo bugs but worth recording for any
  operator deploying from WSL: DrvFs mounts report their directories
  as world-writable by default, so Ansible silently ignores a
  same-directory `ansible.cfg` (`inventory`/`ansible_ssh_user` never
  applied, inventory host pattern left unmatched); and DrvFs's default
  file permissions can leave the *owner*-execute bit set even after
  narrowing `fmask`, which makes Ansible mistake
  `.vault-password-file.txt` for a vault password *script* rather than
  a plain password file. Both resolved by setting
  `metadata,umask=22,fmask=111` under `[automount]` in `/etc/wsl.conf`
  (`fmask=111` clears execute for owner/group/other alike, vs. a
  narrower `fmask=11` which left owner's execute bit set) followed by
  `wsl --shutdown`.
- `ops/my-server/tolaria_news.yml`: dropped the embedded copy of the
  `barrins_api` backend role block (previously documented as a known
  exception to "one playbook per app" — see Constitution §26.1
  above). It's frontend-only now, pointing `VITE_API_BASE_URL` at
  whatever `barrins_api.yml` already has running, the same pattern
  `tamiyo_scroll.yml` already used. Updated the SSH/Alembic path
  reminders (`~/projects/<domain>/apps/barrins_api`, not the app
  root) and every doc referencing the stray `tolaria.yml` filename
  (the file has always been `tolaria_news.yml`): `README.md`,
  `architecture/independence.md`, `deployment/frontend.md`,
  `deployment/rollback.md`.
- `ops/my-server/roles/fastapi_backend/tasks/main.yml`: no task ever
  ran `alembic upgrade head` — the role installed dependencies,
  deployed `.env`, and restarted the service, leaving any pending
  schema migration unapplied against the newly deployed code
  (Constitution §31.1/§37.1 both list migrations as a required
  deployment step). Added an "Apply database migrations" task
  (`uv run alembic upgrade head`, `chdir` at the resolved work dir)
  right after dependency installation and before the `.env`/service
  steps, gated on the same `fastapi_backend_pyproject.stat.exists`
  check as the `uv sync` task.

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
