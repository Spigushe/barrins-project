# fastapi-backend

Deploys a Python/FastAPI application from a private GitHub repository and
runs it under systemd via `uvicorn`, bound to `127.0.0.1:<port>` only —
pair it with `backend-website` (nginx reverse proxy + TLS) to expose it
publicly.

## What it does

1. Ensures `/home/<username>/projects/<fb_server_name>` exists (the app
   root).
2. Resolves which ref to deploy:
   - **`fb_use_release_tag: true`** (the production convention — see the
     Constitution's release policy) — uses `fb_release_tag` if pinned, else
     queries the GitHub API for the repo's latest release and deploys that
     tag. Fails loudly if the repo has no release yet.
   - **`fb_use_release_tag: false`** (default, the staging convention) —
     deploys `fb_git_branch` as before.
3. Clones/pulls `fb_repo` over HTTPS using a GitHub token embedded in the
   URL (`no_log: true` on this task so the token never appears in
   Ansible output/logs) at the ref resolved above.
4. Installs [`uv`](https://docs.astral.sh/uv/) via its official installer
   if not already present (`~/.local/bin/uv`, idempotent via `creates`).
5. Detects the dependency manager by checking for `pyproject.toml` at the
   repo root:
   - **present** → `uv sync` (creates and populates `.venv` automatically).
   - **absent** → falls back to `pip install -r requirements.txt` into a
     `.venv` created with `python3 -m venv` (Debian's system pip refuses
     to install outside a venv — PEP 668 — so this is the only supported
     path).
6. If `fb_env_file` is set **and exists on the control machine**, copies
   it to `<app_root>/.env` (mode `0600`, owned by `username`). If it
   doesn't exist, the step is skipped with a note — this file is meant to
   be a local, git-ignored `.env` (optionally `ansible-vault`-encrypted at
   rest), never committed, so it's normal for it to be absent on a machine
   that hasn't been given it. See the root repo's `secrets/README.md`.
7. Templates a systemd unit (`/etc/systemd/system/<fb_app_name>.service`)
   that runs, as `username`:

   ```bash
   source .venv/bin/activate && uvicorn <fb_entrypoint> --host 127.0.0.1 --port <fb_port>
   ```

   with any `fb_env` entries as `Environment=` lines.
8. Reloads systemd and (re)starts the service — picking up both the
   `.env` file from step 6 (if the app loads `.env` itself, e.g. via
   `pydantic-settings`) and any `fb_env` entries baked into the unit file.

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `fb_repo` | yes | — | GitHub repo, `org/name` form (private, HTTPS). |
| `fb_server_name` | yes | — | Used to build the app root path (`/home/<username>/projects/<fb_server_name>`) and, unless `fb_app_name` is set, the service name. Usually the API's domain. |
| `fb_port` | yes | — | Local port `uvicorn` binds to. Pick one not already in use (see the root README for a per-app port ledger). |
| `fb_entrypoint` | yes | — | `module:app` uvicorn target, e.g. `my_api.main:app`. |
| `fb_app_name` | no | `fb_server_name` | systemd service name; also used as `WorkingDirectory` label. |
| `fb_use_release_tag` | no | `false` | `true` deploys a GitHub release tag instead of a branch — the production convention (see "Release-tag deploys" in the root README). |
| `fb_release_tag` | no | unset (auto-resolve latest) | Pins a specific tag instead of "whatever's latest" — how you roll back: pass a previous tag. Only used when `fb_use_release_tag: true`. |
| `fb_git_branch` | no | `main` | Branch/ref to check out. Only used when `fb_use_release_tag: false`. |
| `fb_env` | no | `{}` | Dict of environment variables written as `Environment=KEY=VALUE` in the unit file (visible via `systemctl show`/`journalctl`). Fine for non-secret toggles; for actual secrets prefer `fb_env_file` below. |
| `fb_env_file` | no | unset (no `.env` deployed) | Local path to a git-ignored `.env` file, copied to `<app_root>/.env` on every deploy if present on the control machine. This is the recommended way to manage an app's full secret configuration (`DATABASE_URL`, `SECRET_KEY`, SMTP creds, ...) — see the root repo's `secrets/README.md`. Never committed to git. |
| `fb_github_token` | no | the play's `github_token` | Overrides the GitHub PAT used to clone this specific app, for when it lives in a different org/repo than the shared token covers. |

## Requirements

- A GitHub Personal Access Token (repo read scope) available as the
  play-level `github_token` var (vaulted — see the root README's "GitHub
  Token" section) or passed per-invocation via `fb_github_token`. If
  `fb_use_release_tag: true`, that token also needs read access to the
  repo's Releases (the same `repo` scope covers this).
- The repo must contain either a `pyproject.toml` (uv-managed) or a
  `requirements.txt` (pip-managed) at its root.
- If `fb_use_release_tag: true`, the repo needs at least one GitHub
  Release published — the role fails with a clear message otherwise.
- Pair with `backend-website` (and `register-ssl` for the domain) to make
  the API reachable over HTTPS.

## Example

```yaml
- role: fastapi-backend
  tags: [backend]
  fb_repo: my-org/my-api
  fb_server_name: my-api.barrins-codex.org
  fb_port: 8012
  fb_entrypoint: "my_api.main:app"
  fb_use_release_tag: true              # production: deploy the latest release
  fb_env_file: "{{ playbook_dir }}/secrets/my-api/production.env"
```
