# Backend Deployment — barrins_api

Operational guide for `ops/my-server/barrins_api.yml`, the sole playbook
that deploys/restarts the shared `barrins_api` backend used by both
Tolaria News and Tamiyo Scroll. Structured per Constitution §37.1.

| | Production | Staging |
| --- | --- | --- |
| Domain | `api.barrins-codex.org` | `api-staging.barrins-codex.org` |
| Local port (`uvicorn`) | `8011` | `8511` |
| systemd unit | `api` | `api-staging` |
| Source | latest GitHub release tag (or `-e fastapi_backend_release_tag=<tag>` to pin) | `develop` branch (or `-e fastapi_backend_git_branch=<branch>`) |
| `.env` (local, git-ignored) | `secrets/barrins_api/production.env` | `secrets/barrins_api/staging.env` |

All commands below run from `ops/my-server/`.

## Preparation

**Server requirements** — `initial.yml` and `setup.yml` must have run on
the host already (nginx, certbot, base user). One-time only.

**Dependencies** — none beyond what `fastapi_backend`/`backend_website`
install automatically (`uv`, a Python venv). The role detects
`pyproject.toml` vs `requirements.txt` and picks the right installer.

**DNS** — an A record for the target domain pointing at the server
(`146.59.146.57`). `register_ssl` (Let's Encrypt HTTP-01) fails silently
if this isn't propagated yet.

**GitHub token** — `barrins_api.yml`'s `github_token` var (vaulted) needs
`repo` scope: read access to clone the repo *and* to query the Releases
API for production deploys. See `ops/my-server/README.md`'s "GitHub
Token" section.

**Release** (production only) — `barrins_api` needs at least one GitHub
Release published before its first production deploy (ADR-2 in
[`../architecture/decisions.md`](../architecture/decisions.md)). No
release exists yet → the playbook fails with a clear message rather than
silently falling back to a branch.

**Environment variables** — create the local `.env` for the target
environment from its template:

```bash
cp secrets/barrins_api/production.env.example secrets/barrins_api/production.env
# fill in real values — see the table below
```

| Variable | Notes |
| --- | --- |
| `DATABASE_URL` | **Never the same database between production and staging** — pointing staging at production's database means staging tests corrupt real data. |
| `ENVIRONMENT` | `production` on the prod instance, `staging` on staging. |
| `ALLOWED_ORIGINS` | Must include the origin of **every** frontend calling this backend: `["https://tolaria.barrins-codex.org", "https://tamiyo.barrins-codex.org"]` in production, the `-staging` equivalents in staging. JSON format. Missing an origin → the SPA loads but every API call fails CORS in the browser console. |
| `IDENTITY_SERVICE_URL` | **Required** since the identity cutover ([ADR-20](../architecture/decisions.md#adr-20-barrins_api-trusts-barrins_identity-jwks-drops-its-users-table)). Base URL of `barrins_identity` — `barrins_api` verifies its `Bearer` tokens against `<url>/.well-known/jwks.json` and issues none of its own. `https://identity.barrins-codex.org` in production, `-staging` on staging. Replaces the old `SECRET_KEY` / `ALGORITHM` / token-TTL vars (all removed). |
| `IDENTITY_SERVICE_CLIENT_ID` / `IDENTITY_SERVICE_CLIENT_SECRET` | A `barrins_identity` service account (scope `identity:users:read`) used only for `POST /users/lookup` — team-roster / sharing display labels. Leave **both** empty to disable the directory: labels then fall back to a generic placeholder (no request fails). See [identity-cutover.md](identity-cutover.md). |

## Deployment

```bash
# Staging first
ansible-playbook barrins_api.yml -e deploy_env=staging

# Production, once staging is verified — deploys the latest release tag
ansible-playbook barrins_api.yml
```

Code-only redeploy (skip cert/nginx setup, already idempotent but
faster): add `--tags deploy`.

Apply pending database migrations (never automated — Constitution §31.3):

```bash
ssh spigushe.org
cd ~/projects/api.barrins-codex.org/apps/barrins_api   # or api-staging.barrins-codex.org/apps/barrins_api
uv run alembic upgrade head
# or: source .venv/bin/activate && alembic upgrade head
```

## Validation

- `curl -I https://api.barrins-codex.org/` → `301` to `/docs` (no
  dedicated `/health` route in `barrins_api` today — see the open item in
  [`../operations/index.md`](../operations/index.md)).
- `journalctl -u api -f` (or `api-staging`) while a frontend exercises the
  API, to confirm requests are landing and check for startup errors
  (missing `.env` values, an unreachable `IDENTITY_SERVICE_URL`, etc.).
- Exercise a real user flow through one of the frontends: log in (against
  `barrins_identity` — see [identity-cutover.md](identity-cutover.md)),
  deck creation, a match record.

## Rollback

See [`rollback.md`](rollback.md) for the full procedure. Short version:

```bash
ansible-playbook barrins_api.yml -e fastapi_backend_release_tag=<previous-tag>
```

This rolls back the *code*. It does **not** roll back the database — read
`rollback.md` before rolling back a release that included a migration.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Playbook fails before touching the server, "repo has no GitHub release yet" | Cut a release on GitHub, or pin one with `-e fastapi_backend_release_tag=<tag>`. |
| `register_ssl` fails on "certbot certonly" | DNS not propagated to `146.59.146.57`, or port 80 unreachable from the internet. |
| Service won't start (`systemctl status api`/`api-staging` failing) | Missing `IDENTITY_SERVICE_URL` (or another required var). Check `journalctl -u <app_name> -n 50`. |
| Every authenticated API call returns `401` right after a deploy | `IDENTITY_SERVICE_URL` unreachable or pointing at the wrong environment — `barrins_api` can't fetch the JWKS. `curl <IDENTITY_SERVICE_URL>/.well-known/jwks.json` from the box. |
| Team rosters / "shared with you" show a generic placeholder instead of names | `IDENTITY_SERVICE_CLIENT_ID` / `_SECRET` empty or wrong, or the service account lacks scope `identity:users:read`. Cosmetic only. |
| A frontend's SPA loads but every API call fails (CORS error in console) | That frontend's origin is missing from `ALLOWED_ORIGINS`. |
| A recent feature doesn't work even though the code is current | Migration not applied — `alembic upgrade head` is never automatic, see "Deployment" above. |

## See also

- [`identity-cutover.md`](identity-cutover.md) — the one-time `users` →
  `barrins_identity` migration + JWKS cutover (ADR-20).
- [`frontend.md`](frontend.md) — the frontends that call this backend.
- [`rollback.md`](rollback.md) — full rollback procedure.
- `ops/my-server/secrets/README.md` — the `.env` workflow in detail.
- `../../../apps/barrins_api/README.md`,
  `../../../apps/barrins_api/.env.example` — the full, authoritative list
  of backend variables, maintained in the application repo.
