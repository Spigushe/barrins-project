# react-frontend

Builds a Node.js frontend (React/Vite or anything with an `npm run
build`-style step) from a private GitHub repository and serves the static
output via nginx, with a single-page-app fallback to `index.html` for
client-side routing. Self-contained: unlike `fastapi-backend`, it does not
need pairing with `backend-website` — it templates and serves its own
HTTPS vhost directly.

## What it does

Everything runs as **root** (the play's default `become` user) so that
redeploys stay idempotent even though the last step hands ownership to
`www-data` — see the comment at the top of `tasks/main.yml` for why.

1. Ensures `/home/<username>/projects/<rf_server_name>` exists (the site
   root).
2. Resolves which ref to deploy — same rule as `fastapi-backend`:
   `rf_use_release_tag: true` (production convention) deploys
   `rf_release_tag` if pinned, else the repo's latest GitHub release tag
   (fails if none exists); `false` (default, staging convention) deploys
   `rf_git_branch`.
3. Clones/pulls `rf_repo` over HTTPS using a GitHub token embedded in the
   URL (`no_log: true`, token never logged) at the ref resolved above.
4. Installs [`nvm`](https://github.com/nvm-sh/nvm) to `/opt/nvm` if not
   already present — **shared across every `react-frontend` invocation on
   the host**, so multiple apps don't each install their own copy.
5. Installs the requested Node version via `nvm install`.
6. If `rf_build_env` is non-empty, writes it as a `.env` file in the repo
   root before building (for build-time variables baked into the bundle,
   e.g. Vite's `VITE_*`).
7. Runs `<rf_package_manager> install` then `rf_build_command`.
8. If the build output isn't literally named `dist`, symlinks
   `<site_root>/dist -> <site_root>/<rf_build_dir>` (the nginx template
   always serves `dist/`).
9. Recursively chowns the site root to `www-data` so nginx can read it —
   this is the **last** task with `tags: deploy`, done every deploy run.
10. Templates the HTTPS vhost and reloads nginx.

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `rf_repo` | yes | — | GitHub repo, `org/name` form (private, HTTPS). |
| `rf_server_name` | yes | — | Public domain; also used for the site root path. Certificate must already exist (run `register-ssl` first). |
| `rf_app_name` | no | `rf_server_name` | Currently informational only (no systemd unit — this role has no long-running process). |
| `rf_use_release_tag` | no | `false` | `true` deploys a GitHub release tag instead of a branch — the production convention. |
| `rf_release_tag` | no | unset (auto-resolve latest) | Pins a specific tag instead of "whatever's latest" — how you roll back. Only used when `rf_use_release_tag: true`. |
| `rf_git_branch` | no | `main` | Branch/ref to check out. Only used when `rf_use_release_tag: false`. |
| `rf_node_version` | no | `22` | Node version passed to `nvm install`/`nvm use`. |
| `rf_package_manager` | no | `npm` | Must support `<pm> install` (e.g. `yarn`, `pnpm`). |
| `rf_build_command` | no | `npm run build` | Full build command, run from the repo root. |
| `rf_build_dir` | no | `dist` | Where the build output lands relative to the repo root. Symlinked to `dist` if different. |
| `rf_build_env` | no | `{}` | Dict written to a `.env` file before building (build-time vars, not runtime secrets — there's no running process to pass `Environment=` to). |
| `rf_github_token` | no | the play's `github_token` | Overrides the GitHub PAT used to clone this specific app, for when it lives in a different org/repo than the shared token covers. |

## Requirements

- A GitHub Personal Access Token (repo read scope) available as the
  play-level `github_token` var (vaulted — see the root README) or passed
  per-invocation via `rf_github_token`. If `rf_use_release_tag: true`,
  that token also needs read access to the repo's Releases (the same
  `repo` scope covers this).
- If `rf_use_release_tag: true`, the repo needs at least one GitHub
  Release published — the role fails with a clear message otherwise.
- `register-ssl` must have run for `rf_server_name` first.
- The build must produce a client-side-routed SPA (or a plain static
  site) — the nginx `try_files $uri /index.html;` fallback assumes any
  unmatched path should render the app shell, not 404.

## Example

```yaml
- role: register-ssl
  tags: [frontend, certs]
  rs_server_name: my-app.barrins-codex.org

- role: react-frontend
  tags: [frontend]
  rf_repo: my-org/my-app
  rf_server_name: my-app.barrins-codex.org
```
