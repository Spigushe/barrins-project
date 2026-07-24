# docs_site

Builds the mkdocs documentation site from a private GitHub repository and
serves the static output via nginx. Structurally mirrors `react_frontend`
(clone at a ref, build, symlink output, hand ownership to `www-data`), but
the build toolchain is `uv`/`uvx` (matching `fastapi_backend`), not
Node/npm — there's no `nvm`/package-manager step here, and no SPA
fallback in the nginx vhost, since a mkdocs site is a plain static
multi-page site, not a client-side-routed app.

## What it does

Everything runs as **root** (the play's default `become` user) so that
redeploys stay idempotent even though the last step hands ownership to
`www-data` — see `react_frontend/tasks/main.yml`'s comment for why the
same pattern is used here.

1. Ensures `/home/<username>/projects/<docs_site_server_name>` exists
   (the site root).
2. Resolves which ref to deploy — same rule as `fastapi_backend`/
   `react_frontend`: `docs_site_use_release_tag: true` (production
   convention) deploys `docs_site_release_tag` if pinned, else the
   repo's latest GitHub release tag (fails if none exists); `false`
   (default, staging convention) deploys `docs_site_git_branch`.
3. Clones/pulls `docs_site_repo` over HTTPS using a GitHub token embedded
   in the URL (`no_log: true`, token never logged) at the ref resolved
   above.
4. Installs [`uv`](https://astral.sh/uv) to `~/.local/bin` if not
   already present (idempotent — `creates:` skips it if `fastapi_backend`
   already installed it on this host).
5. Runs `uvx --with mkdocs-material mkdocs build --strict -f mkdocs.yml`
   from `docs_site_repo_subdir` within the clone (default `docs`, this
   monorepo's actual docs directory).
6. Symlinks `<site_root>/site -> <build_root>/<docs_site_build_dir>`
   whenever that doesn't already resolve to `<site_root>/site` on its
   own — the nginx template always serves `<site_root>/site`.
7. Recursively chowns the site root to `www-data` so nginx can read it —
   this is the **last** task with `tags: deploy`, done every deploy run.
8. Templates the HTTPS vhost (plain static-file serving, `try_files $uri
   $uri/ =404;` — mkdocs' "pretty URL" pages are already real
   `<page>/index.html` files on disk, no rewrite needed) and reloads
   nginx.

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `docs_site_repo` | yes | — | GitHub repo, `org/name` form (private, HTTPS). |
| `docs_site_repo_subdir` | no | `docs` | Path within the cloned repo where the mkdocs project lives. The build command and the `site` symlink both resolve against `<site_root>/<repo_subdir>`. |
| `docs_site_server_name` | yes | — | Public domain; also used for the site root path. Certificate must already exist (run `register_ssl` first). |
| `docs_site_app_name` | no | `docs_site_server_name` | Currently informational only (no systemd unit — this role has no long-running process). |
| `docs_site_use_release_tag` | no | `false` | `true` deploys a GitHub release tag instead of a branch — the production convention. |
| `docs_site_release_tag` | no | unset (auto-resolve latest) | Pins a specific tag instead of "whatever's latest" — how you roll back. Only used when `docs_site_use_release_tag: true`. |
| `docs_site_git_branch` | no | `main` | Branch/ref to check out. Only used when `docs_site_use_release_tag: false`. |
| `docs_site_build_dir` | no | `site` | Where `mkdocs build` writes its output, relative to the mkdocs project root — must match `mkdocs.yml`'s own `site_dir`. |
| `docs_site_github_token` | no | the play's `github_token` | Overrides the GitHub PAT used to clone this specific app, for when it lives in a different org/repo than the shared token covers. |

## Requirements

- A GitHub Personal Access Token (repo read scope) available as the
  play-level `github_token` var or passed per-invocation via
  `docs_site_github_token`. If `docs_site_use_release_tag: true`, that
  token also needs read access to the repo's Releases (the same `repo`
  scope covers this).
- If `docs_site_use_release_tag: true`, the repo needs at least one
  GitHub Release published — the role fails with a clear message
  otherwise.
- `register_ssl` must have run for `docs_site_server_name` first.

## Example

```yaml
- role: register_ssl
  tags: [docs, certs]
  register_ssl_server_name: docs.barrins-codex.org
  register_ssl_contact_name: admin@example.com

- role: docs_site
  tags: [docs, deploy]
  docs_site_repo: my-org/my-monorepo
  docs_site_server_name: docs.barrins-codex.org
```
