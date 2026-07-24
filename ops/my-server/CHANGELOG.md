# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [Unreleased]

### Added

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
- `ops/my-server/secrets/tamiyo_scroll/{staging,production}.env.example`:
  documentation templates mirroring `apps/tamiyo_scroll/.env.example`,
  for parity with `barrins_api`'s per-app `secrets/` layout. Unlike
  `fastapi_backend_env_file`, `react_frontend` has no `env_file`
  mechanism — `tamiyo_scroll.yml` does not read these; `VITE_API_BASE_URL`
  is already computed automatically by the playbook and isn't secret.

### Changed

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
- `ops/my-server/ansible.cfg`: normalized `key=value` spacing under
  `[defaults]` — `inventory`, `vault_password_file`, `timeout`, and
  `ansible_ssh_user` had stray spaces around `=` that every other key
  in the file didn't.
- Production email sending (ADR-3): decided to go through a
  transactional email provider's SMTP relay for
  `identity@barrins-codex.org`, rather than self-hosting a mail server
  or keeping the temporary personal Gmail relay long-term. No code
  change required — `SMTPEmailSender` already speaks generic SMTP.

### Fixed

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
  (`uv run alembic upgrade head`, `chdir` at the resolved work dir),
  gated on the same `fastapi_backend_pyproject.stat.exists` check as
  the `uv sync` task.
- `ops/my-server/roles/fastapi_backend/tasks/main.yml`: the migrations
  task above initially ran right after dependency installation, before
  the `.env` deploy step — so `alembic upgrade head` connected using
  whatever `.env` (if any) was already sitting on the server from a
  previous deploy, not the one this run just copied. Surfaced while
  deploying `barrins_api.yml -e deploy_env=staging`: migrations failed
  with `password authentication failed for user "REPLACE_USER"` even
  after the local `secrets/barrins_api/staging.env` was fixed, because
  the corrected file hadn't been copied to the server yet at the point
  migrations ran. Reordered so "Deploy the local .env file" (and its
  "no local .env found" fallback) runs before "Apply database
  migrations".
- `ops/my-server/barrins_api.yml`, `tamiyo_scroll.yml`,
  `tolaria_news.yml`: `env_branch` defaulted staging deploys to a
  `develop` branch that doesn't exist in this repo (the actual branch
  is `staging`) — any `-e deploy_env=staging` run would have failed at
  the `git clone`/checkout step. Also populated the three playbooks'
  `github_token` vault block, still a `REPLACE_WITH_...` placeholder
  ciphertext since the ops migration in-repo, with the real
  `ansible-vault encrypt_string` output.
- `ops/my-server/README.md`: the venv setup instructions created a
  bare `venv/` directory, which nothing but a stale,
  since-superseded `.gitignore` line covers — every role actually
  uses `uv`'s `.venv` convention (caught by the repo-wide
  `**/.venv/` pattern). Renamed to `.venv`, and added `--force` to
  the `ansible-galaxy collection install` step so it actually
  reinstalls collections pinned in `requirements.yml` instead of
  silently skipping already-installed ones.
- `ops/my-server/roles/fastapi_backend/README.md`: documented the
  `uv python install 3.14` step the role already performs before
  `uv sync` (idempotent, a no-op when already installed) — the
  README previously only mentioned `uv sync` itself.
- `ops/my-server/roles/react_frontend/tasks/main.yml`: the "Ensure nvm
  is installed" task set `NVM_DIR=/opt/nvm` (shared across apps) but
  never created that directory first; nvm's `install.sh` only
  auto-creates `$NVM_DIR` when it matches its own default
  (`$HOME/.nvm`), so it exited with "You have $NVM_DIR set... but that
  directory does not exist" on a fresh host. Surfaced while deploying
  `tamiyo_scroll.yml -e deploy_env=staging` to a fresh server. Added a
  task creating `/opt/nvm` before the install step.
- `ops/my-server/roles/react_frontend/tasks/main.yml`: the "Clone/update
  application repository" task runs as root (the play's `become: true`
  default), but the role's last task hands `site_root` to `www-data`
  recursively — including the `.git/` directory — so on the next run root
  no longer owns the repo and git refuses it outright (`detected dubious
  ownership in repository at ...`, Git's CVE-2022-24765 protection).
  Surfaced on a redeploy of `tamiyo_scroll.yml -e deploy_env=staging`
  after the initial deploy had already flipped ownership to `www-data`.
  Added a task setting `safe.directory` in root's global gitconfig (as
  root) before the clone/update step, so every future run is immune to
  the ownership check regardless of who last owned the checkout. First
  written as an `ansible.builtin.command: git config --global --add
  safe.directory ...` task, which passed locally but failed PR #17's
  `ops` CI job under `ansible-lint`'s `command-instead-of-module` rule;
  switched to `community.general.git_config` (`add_mode: add`, which
  maps to `git config --add` and is idempotent — it skips when the
  value is already present), adding `community.general` to
  `ops/my-server/requirements.yml`.
- `ops/my-server/roles/react_frontend/tasks/main.yml`: with the ownership
  check above resolved, the same "Clone/update application repository"
  task then failed with `Local modifications exist in the destination
  ... (force=no)` on a second deploy — the build step (`npm install`/
  build command) can leave the working tree dirty (e.g. a regenerated
  lockfile), and Ansible's `git` module refuses to update over local
  modifications unless told to. Since this checkout exists solely to be
  rebuilt from source control on every deploy, added `force: true` so it
  always resets cleanly to the target ref. Verified with a full
  `tamiyo_scroll.yml -e deploy_env=staging` redeploy, which completed
  successfully end to end.
