# ops/my-server — Ansible deployment

Ansible-based deployment for the Barrin's ecosystem's VPS. Lives inside
this monorepo (`ops/my-server/`) so infrastructure evolves in lockstep with
the applications it deploys — see
[`../../docs/content/ops/architecture/independence.md`](../../docs/content/ops/architecture/independence.md)
for why this replaced the previous separate `myserver` repo, and
[`../../docs/content/CLAUDE.md`](../../docs/content/CLAUDE.md) (the
Development Constitution) §§25–38 for the rules this setup follows.

All commands below assume your shell is `cd`'d into this directory
(`ops/my-server/`) — `ansible.cfg` resolves `hosts.ini`, the vault password
file, and `secrets/` relative to it.

## First Steps

Create a venv in this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ansible
ansible-galaxy collection install -r requirements.yml --force
```

Create a `.vault-password-file.txt` in this directory (only needed if you
choose to encrypt your local `.env` files at rest — see "Secrets" below):

```bash
touch .vault-password-file.txt
```

Generate a strong password and put it in there.

## Initial Setup

Use the user and password you received by e-mail after your server setup.

```bash
ansible-playbook --user <provided_user> initial.yml -k
```

### Setup Packages

```bash
ansible-playbook setup.yml
```

### Specific Commands

#### GitHub Deploy Key

Get the public RSA key from the server:

```bash
ssh spigushe.org
$> cd ~/.ssh
$> cat id_rsa.pub
```

And add it to the Deploy Keys (Settings > Deploy Keys) of the Github repository.

#### GitHub Token (private repo checkout)

`fastapi_backend` and `react_frontend` clone their repo over HTTPS using a
GitHub Personal Access Token (`repo` read scope is enough), instead of the
server's SSH deploy key. Generate one on GitHub and vault it:

```bash
ansible-vault encrypt_string '<ghp_token>' --name 'github_token'
```

Copy the resulting string into the playbook's `github_token` var (see
`tolaria_news.yml`). Every `fastapi_backend`/`react_frontend` role invocation uses
that same token by default; pass `fastapi_backend_github_token`/`react_frontend_github_token` on a
specific role invocation if one app lives in a different org and needs its
own token. Tokens expire and must be renewed periodically: repeat the
`encrypt_string` step and redeploy (`ansible-playbook <playbook>.yml --tags
deploy` to skip the certificate/nginx setup steps and just redeploy code).

## Applications

| App | Playbook | Production (release tag) | Staging (`-e deploy_env=staging`, branch) |
| --- | -------- | ------------------------- | ------------------------------------------ |
| barrins_api (shared backend) | `barrins_api.yml` (canonical — see "Multiple frontends sharing one backend" below) | `api.barrins-codex.org` (`:8011`) | `api-staging.barrins-codex.org` (`:8511`) |
| Tolaria News (frontend) | `tolaria_news.yml` | `tolaria.barrins-codex.org` | `tolaria-staging.barrins-codex.org` |
| Tamiyo Scroll (frontend) | `tamiyo_scroll.yml` | `tamiyo.barrins-codex.org` | `tamiyo-staging.barrins-codex.org` |

One playbook per application: each of the three files above deploys
exactly one app and nothing else — deploying Tamiyo Scroll (or Tolaria
News) never restarts `barrins_api`, and vice versa (Constitution §26.1,
"Deployment Independence") — see "Multiple frontends sharing one backend"
below for how they still call the same shared backend without deploying it.

Production always deploys the latest GitHub release tag (or a pinned one —
see "Release-tag deploys" below); staging always deploys a branch. Full
step-by-step deployment guides — DNS, secrets, staging → production
promotion, rollback, troubleshooting — live at
[`../../docs/content/ops/deployment/backend.md`](../../docs/content/ops/deployment/backend.md)
and
[`../../docs/content/ops/deployment/frontend.md`](../../docs/content/ops/deployment/frontend.md)
(also published at docs.barrins-codex.org).

## Adding a new application

Every app gets one top-level playbook (see `barrins_api.yml` for a backend,
`tamiyo_scroll.yml` for a frontend) that assembles roles from `roles/`. Pick
the roles that match your app:

| Role | Use case | Key variables |
| --- | --- | --- |
| `register_ssl` | Let's Encrypt certificate for a domain (needed by every publicly reachable role below) | `register_ssl_server_name` |
| `react_frontend` | Node/React (or any `npm run build`-based) static frontend, served by nginx with SPA fallback | `react_frontend_repo`, `react_frontend_server_name`, `react_frontend_build_dir`, `react_frontend_use_release_tag` |
| `fastapi_backend` | Python/FastAPI API, git-cloned, `uv`/`pip` venv, run via `uvicorn` under systemd | `fastapi_backend_repo`, `fastapi_backend_server_name`, `fastapi_backend_port`, `fastapi_backend_entrypoint`, `fastapi_backend_use_release_tag`, `fastapi_backend_env_file` (secrets, see below) |
| `backend_website` | nginx vhost that serves `dist/` and reverse-proxies everything else to a backend port (pair with `fastapi_backend`) | `backend_website_server_name`, `backend_website_port` |

Other roles (`setup_base_user`, `setup_packages`, `create_ssh_key`) are host
bootstrap, not app-specific — see `setup.yml`/`initial.yml`. Roles for stacks
not currently in use (Flask, PHP, plain background workers, public-repo
static sites) were removed; check `git log -- ops/my-server/roles/` if one
of them needs resurrecting later.

**This monorepo, not a dedicated app repo.** Every app deployed today
(`barrins_api`, `tamiyo_scroll`, `tolaria_news`) lives inside this same
repository (`Spigushe/barrins-project`) under `apps/<name>/`, not in its own
GitHub repo — so every playbook sets `fastapi_backend_repo`/
`react_frontend_repo` to `Spigushe/barrins-project` plus
`fastapi_backend_repo_subdir`/`react_frontend_repo_subdir: apps/<name>`
(see `barrins_api.yml`/`tamiyo_scroll.yml` for the pattern). The role still
clones the whole repo to `app_root`/`site_root`, but resolves
`pyproject.toml`/`requirements.txt`/the build command/the systemd
`WorkingDirectory` relative to the subdirectory. If a future app *does* get
its own dedicated repo, just omit `*_repo_subdir` — the repo root is used
as the app root by default, same as before.

Minimal template for a new API playbook (`my_api.yml`):

```yaml
---
- hosts: spigushe
  become: true
  gather_facts: false
  vars:
    username: spigushe
    deploy_env: production
    backend_env_file: "{{ playbook_dir }}/secrets/my_api/{{ deploy_env }}.env"

  roles:
    - role: register_ssl
      tags: [backend, certs]
      register_ssl_server_name: my-api.barrins-codex.org

    - role: fastapi_backend
      tags: [backend]
      fastapi_backend_repo: my-org/my-api
      fastapi_backend_server_name: my-api.barrins-codex.org
      fastapi_backend_port: 8012
      fastapi_backend_entrypoint: "my_api.main:app"
      fastapi_backend_use_release_tag: "{{ deploy_env == 'production' }}"
      fastapi_backend_env_file: "{{ backend_env_file }}"

    - role: backend_website
      tags: [backend]
      backend_website_server_name: my-api.barrins-codex.org
      backend_website_port: 8012
```

And a separate frontend playbook (`my_app.yml`):

```yaml
---
- hosts: spigushe
  become: true
  gather_facts: false
  vars:
    username: spigushe
    deploy_env: production

  roles:
    - role: register_ssl
      tags: [frontend, certs]
      register_ssl_server_name: my-app.barrins-codex.org

    - role: react_frontend
      tags: [frontend]
      react_frontend_repo: my-org/my-app
      react_frontend_server_name: my-app.barrins-codex.org
      react_frontend_use_release_tag: "{{ deploy_env == 'production' }}"
      react_frontend_build_env:
        VITE_API_BASE_URL: "https://my-api.barrins-codex.org"
```

Both need the play-level `github_token` var too — see "GitHub Token" above.
Add a `secrets/my_api/production.env.example` template (see "Secrets"
below) documenting the keys the new app needs.

Ports already in use: `8011`/`8511` (`api.barrins-codex.org`, production/staging — see `barrins_api.yml`) — pick a free pair for the next app's `fastapi_backend_port`/staging port (production port +500 is the convention below).

### Staging

`barrins_api.yml`, `tolaria_news.yml` and `tamiyo_scroll.yml` all accept
`-e deploy_env=staging`:

```bash
ansible-playbook barrins_api.yml -e deploy_env=staging
ansible-playbook tamiyo_scroll.yml -e deploy_env=staging
# preview a specific branch instead of the staging default (develop):
ansible-playbook tamiyo_scroll.yml -e deploy_env=staging \
  -e react_frontend_git_branch=my-feature
```

This deploys a fully side-by-side stack, isolated from production:
`-staging`-suffixed subdomains (`api-staging.barrins-codex.org`,
`tamiyo-staging.barrins-codex.org`), its own backend port (`8511`,
production port `8011` + `500` — follow that convention for future apps) and
systemd unit (`api-staging`), and the `develop` branch by default instead of
a release tag. Nothing is shared with production except the physical
server, so a bad staging deploy can't touch the production service, nginx
vhost, or database.

The staging backend's `.env` (with its own, *never-shared-with-production*
`DATABASE_URL`) uses the same local, git-ignored file mechanism as
production's — see "Secrets" below.

Once a change is verified on staging, cut a GitHub release from the
validated commit and run the playbook again *without* `-e
deploy_env=staging` (the default) to ship it — that's the "don't push
straight to prod" gate this is meant to provide (Constitution §27.1).

To add staging to a new app's playbook, copy the `deploy_env`/`env_suffix`/
`env_branch`/`backend_port`/`*_domain` vars block from `barrins_api.yml` (or
`tamiyo_scroll.yml` for a frontend) and reference those computed vars in the
role invocations instead of literal domains/ports.

### Release-tag deploys

Constitution §§25/27/31 require production to deploy released versions
only, never a branch head. Every role that clones a repo
(`fastapi_backend`, `react_frontend`) implements this via
`fastapi_backend_use_release_tag`/`react_frontend_use_release_tag`:

- **`true`** (production, wired automatically as `deploy_env == 'production'`
  in every playbook here) — deploys `fastapi_backend_release_tag`/`react_frontend_release_tag` if
  pinned, else queries the GitHub API for the repo's latest release and
  deploys that tag. Fails with a clear message if the repo has no release
  yet — cut one on GitHub first.
- **`false`** (staging, the default) — deploys `fastapi_backend_git_branch`/
  `react_frontend_git_branch` as before, since staging exists specifically to preview
  code that hasn't been released yet.

**Rollback**: pass the previous tag explicitly to redeploy it —

```bash
ansible-playbook barrins_api.yml -e fastapi_backend_release_tag=v1.2.3
ansible-playbook tamiyo_scroll.yml -e react_frontend_release_tag=v0.9.0
```

See
[`../../docs/content/ops/deployment/rollback.md`](../../docs/content/ops/deployment/rollback.md)
for the full rollback procedure, including the database-migration caveat.

### Multiple frontends sharing one backend

Not every app needs its own `fastapi_backend`. Two frontends —
`tolaria.barrins-codex.org` and `tamiyo.barrins-codex.org` — call the
*same* `barrins_api` backend. `barrins_api.yml` is the canonical, single
place that deploys it (one playbook per application — see "Applications"
above); `tamiyo_scroll.yml` just points its `VITE_API_BASE_URL` at whatever
`barrins_api.yml` already has running and never redeploys/restarts the
backend itself, so deploying the frontend can never take the backend (or
the other frontend) down.

`tolaria_news.yml` used to embed its own copy of the backend role block too
(a leftover from before this split) but has since been migrated the same
way `tamiyo_scroll.yml` was: it only points its `VITE_API_BASE_URL` at
whatever `barrins_api.yml` already has running, and never redeploys or
restarts the backend itself.

One backend-level thing this repo still does **not** automate: **Alembic
migrations**. `fastapi_backend` never runs it — run it by hand over SSH
after every deploy that changes the schema:

```bash
ssh spigushe.org
cd ~/projects/api.barrins-codex.org/apps/barrins_api   # or api-staging.barrins-codex.org/apps/barrins_api
uv run alembic upgrade head                            # or: source .venv/bin/activate && alembic upgrade head
```

## Secrets — backend `.env` files

Constitution §34: secrets must never be stored inside a repository. So
unlike code, an app's backend `.env` is **never committed** — see
[`secrets/README.md`](secrets/README.md) for the full local-only
create/edit/rotate workflow, and the "Secrets in git" decision record in
[`../../docs/content/ops/architecture/decisions.md`](../../docs/content/ops/architecture/decisions.md)
for why.

In short: `barrins_api.yml` deploys `secrets/barrins_api/<deploy_env>.env`
(a local file each operator creates on their own machine, from the
`.env.example` template next to it) straight to the server on every run,
*if that file exists on the machine running the playbook* — if it doesn't,
the step is skipped with a note and the server's existing `.env` (if any)
is left untouched. No more hand-editing `.env` over SSH, but also no
secret ever touches this git history.

Quick start for a fresh checkout:

```bash
cp secrets/barrins_api/production.env.example secrets/barrins_api/production.env
cp secrets/barrins_api/staging.env.example secrets/barrins_api/staging.env
# fill in both with real values, then:
ansible-playbook barrins_api.yml
ansible-playbook barrins_api.yml -e deploy_env=staging
```

This mechanism (`fastapi_backend_env_file` on the `fastapi_backend` role) is generic —
any future backend app can use the same pattern, see the role's README.

## Database administration — pgAdmin

`postgresql_pgadmin.yml` deploys [pgAdmin4](https://www.pgadmin.org/) (in
Docker, reverse-proxied by nginx) for the PostgreSQL server `setup_packages`
already installs on the host — it does not install PostgreSQL itself, only
exposes a web UI for it and wires the two together (isolated Docker
network, `pg_hba.conf`/`listen_addresses` updated to accept password auth
from that network only — never from the internet). It also enables
`unattended-upgrades` for the whole host, keeping the OS-level PostgreSQL
package patched automatically.

```bash
echo -n '<strong password>' > secrets/postgresql_pgadmin/admin_password.txt
chmod 600 secrets/postgresql_pgadmin/admin_password.txt
ansible-playbook postgresql_pgadmin.yml
```

Same secrets policy as backend `.env` files: the admin password is a local,
git-ignored file (`secrets/postgresql_pgadmin/admin_password.txt`), never
committed — see [`secrets/README.md`](secrets/README.md). Creating an
actual PostgreSQL role/password to connect *to* is a deliberate manual step
(no secret is ever generated silently) — see
[`../../docs/content/ops/deployment/database.md`](../../docs/content/ops/deployment/database.md)
and `roles/pgadmin/README.md` for the full guide.
