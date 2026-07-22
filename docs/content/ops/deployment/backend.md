# Backend Deployment — barrins_api

Operational guide for `ops/my-server/barrins_api.yml`, the sole playbook
that deploys/restarts the shared `barrins_api` backend used by both
Tolaria News and Tamiyo Scroll. Structured per Constitution §37.1.

| | Production | Staging |
| --- | --- | --- |
| Domain | `api.barrins-codex.org` | `api-staging.barrins-codex.org` |
| Local port (`uvicorn`) | `8011` | `8511` |
| systemd unit | `api` | `api-staging` |
| Source | latest GitHub release tag (or `-e fb_release_tag=<tag>` to pin) | `develop` branch (or `-e fb_git_branch=<branch>`) |
| `.env` (local, git-ignored) | `secrets/barrins_api/production.env` | `secrets/barrins_api/staging.env` |

All commands below run from `ops/my-server/`.

## Preparation

**Server requirements** — `initial.yml` and `setup.yml` must have run on
the host already (nginx, certbot, base user). One-time only.

**Dependencies** — none beyond what `fastapi-backend`/`backend-website`
install automatically (`uv`, a Python venv). The role detects
`pyproject.toml` vs `requirements.txt` and picks the right installer.

**DNS** — an A record for the target domain pointing at the server
(`146.59.146.57`). `register-ssl` (Let's Encrypt HTTP-01) fails silently
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
| `ENVIRONMENT` | `production` on the prod instance, `staging` on staging. Gates whether `SMTP_HOST`/`FRONTEND_BASE_URL` are required (production only). |
| `ALLOWED_ORIGINS` | Must include the origin of **every** frontend calling this backend: `["https://tolaria.barrins-codex.org", "https://tamiyo.barrins-codex.org"]` in production, the `-staging` equivalents in staging. JSON format. Missing an origin → the SPA loads but every API call fails CORS in the browser console. |
| `REQUIRE_EMAIL_VERIFICATION` | `true` by default. `false` skips SMTP/`FRONTEND_BASE_URL` requirements — a temporary workaround while SMTP isn't configured. |
| `FRONTEND_BASE_URL` | Single value used for the `{FRONTEND_BASE_URL}/verify-email` link. The backend serves multiple frontends but this can only point at one — decide which. Required (non-default) when `ENVIRONMENT=production` and `REQUIRE_EMAIL_VERIFICATION=true`. |
| `SMTP_HOST`/`SMTP_USERNAME`/`SMTP_PASSWORD` | Required under the same condition as `FRONTEND_BASE_URL`. Empty `SMTP_HOST` (with verification on) logs the code to the service's journal instead of sending email — useful on staging. |
| `SECRET_KEY` | `openssl rand -hex 32`. Refuses to start on a placeholder value. Use a different key per environment. |

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
cd ~/projects/api.barrins-codex.org   # or api-staging.barrins-codex.org
uv run alembic upgrade head
# or: source .venv/bin/activate && alembic upgrade head
```

## Validation

- `curl -I https://api.barrins-codex.org/` → `301` to `/docs` (no
  dedicated `/health` route in `barrins_api` today — see the open item in
  [`../operations/index.md`](../operations/index.md)).
- `journalctl -u api -f` (or `api-staging`) while a frontend exercises the
  API, to confirm requests are landing and check for startup errors
  (missing `.env` values, placeholder `SECRET_KEY`, etc.).
- Exercise a real user flow through one of the frontends: signup (check
  the verification code lands somewhere — email or, if `SMTP_HOST` is
  empty, the service log), deck creation, a match record.

## Rollback

See [`rollback.md`](rollback.md) for the full procedure. Short version:

```bash
ansible-playbook barrins_api.yml -e fb_release_tag=<previous-tag>
```

This rolls back the *code*. It does **not** roll back the database — read
`rollback.md` before rolling back a release that included a migration.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Playbook fails before touching the server, "repo has no GitHub release yet" | Cut a release on GitHub, or pin one with `-e fb_release_tag=<tag>`. |
| `register-ssl` fails on "certbot certonly" | DNS not propagated to `146.59.146.57`, or port 80 unreachable from the internet. |
| Service won't start (`systemctl status api`/`api-staging` failing) | Placeholder `SECRET_KEY`, or (production only) missing `SMTP_HOST`/`FRONTEND_BASE_URL`. Check `journalctl -u <app_name> -n 50`. |
| A frontend's SPA loads but every API call fails (CORS error in console) | That frontend's origin is missing from `ALLOWED_ORIGINS`. |
| Email verification links point at the wrong frontend | `FRONTEND_BASE_URL` is shared across every frontend this backend serves — only one can be correct until this becomes per-app aware. |
| A recent feature doesn't work even though the code is current | Migration not applied — `alembic upgrade head` is never automatic, see "Deployment" above. |

## See also

- [`frontend.md`](frontend.md) — the frontends that call this backend.
- [`rollback.md`](rollback.md) — full rollback procedure.
- `ops/my-server/secrets/README.md` — the `.env` workflow in detail.
- `../../../apps/barrins_api/README.md`,
  `../../../apps/barrins_api/.env.example` — the full, authoritative list
  of backend variables, maintained in the application repo.
