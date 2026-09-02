# Frontend Deployment — Goblin Guide

Operational guide for `ops/my-server/goblin_guide.yml`. Structured per
Constitution §37.2. Goblin Guide is the standalone login and
account-management SPA for **Barrin's Identity** — it calls
[`barrins_identity`](identity.md) directly, **not** `barrins_api`. Deploy
identity first.

| | Goblin Guide |
| --- | --- |
| Playbook | `goblin_guide.yml` |
| Production domain | `goblin.barrins-codex.org` |
| Staging domain | `goblin-staging.barrins-codex.org` |
| Source | latest GitHub release tag (or `-e react_frontend_release_tag=<tag>`) |
| Talks to | `barrins_identity` (`identity{,-staging}.barrins-codex.org`) in cookie mode (ADR-18) |
| Deploys identity too? | **No** — frontend-only, one playbook per application (§26.1, [`../architecture/independence.md`](../architecture/independence.md)) |

All commands below run from `ops/my-server/`.

## Preparation

**Server requirements** — `initial.yml`/`setup.yml` must already have run.

**Identity deployed** — `barrins_identity.yml` must have been run for the
target `deploy_env` (see [`identity.md`](identity.md)) before this SPA has
anything to authenticate against.

**Identity in cookie mode for this origin** — in
`secrets/barrins_identity/<deploy_env>.env` (the templates already carry
these keys):

- `REFRESH_COOKIE_ENABLED=true`
- `REFRESH_COOKIE_DOMAIN=identity{,-staging}.barrins-codex.org`
- `REFRESH_COOKIE_SAMESITE=none` (SPA and identity are on different
  sub-domains ⇒ cross-site cookie)
- `https://goblin{,-staging}.barrins-codex.org` present in
  `ALLOWED_ORIGINS` **and** `FRONTEND_BASE_URL`

After changing that file, **redeploy identity** (`ansible-playbook
barrins_identity.yml …` — its own playbook, no cross-touch).

**DNS** — an A record for `goblin{,-staging}.barrins-codex.org` pointing
at the server, before `register_ssl` can issue its certificate.

**GitHub token** — same `github_token` var as every other playbook
(`repo` scope covers cloning and, for production, the Releases API).

**Release** (production only) — the monorepo needs at least one GitHub
Release published (ADR-2).

**Configuration** — `VITE_IDENTITY_SERVICE_URL` is set automatically by
the playbook (`react_frontend_build_env`, pointed at
`https://identity{,-staging}.barrins-codex.org` matching `deploy_env`) —
nothing to configure by hand. It is a **build-time** variable (Vite
inlines it into the bundle), so changing it needs a new build
(`--tags deploy`), not just an nginx reload.

**Shared-library build** — `apps/goblin_guide` depends on
`libs/goblin_guide` (`@barrins/goblin-guide`) as a `file:` path dependency
whose `dist/` is git-ignored. The playbook's
`react_frontend_build_command` installs and builds that library before
building the shell — no manual step, but it is why the build command is
overridden rather than the default `npm run build`.

## Deployment

```bash
# Staging first
ansible-playbook goblin_guide.yml -e deploy_env=staging
# During the v2.0.0 rollout, until Goblin Guide reaches the staging branch:
ansible-playbook goblin_guide.yml -e deploy_env=staging \
  -e react_frontend_git_branch=proj/v2.0.0-bump

# Production, once staging is verified — deploys the latest release tag
ansible-playbook goblin_guide.yml
```

## Validation

- Open `https://goblin-staging.barrins-codex.org`; confirm the app shell
  loads (`try_files $uri /index.html` SPA fallback — a hard refresh on a
  deep route like `/service-accounts` should still render the app, not
  404).
- Log in with a seeded identity account. In DevTools → Application →
  Cookies, confirm a `refresh_token` cookie is set on
  `identity-staging.barrins-codex.org` with `HttpOnly`, `Secure`,
  `SameSite=None`.
- Leave the tab idle past the access-token lifetime (10 min) or close and
  reopen it — you should still be logged in (silent cross-site refresh via
  the cookie).
- The home page renders two columns: the account panel and the
  application directory (ADR-19). Goblin Guide does not list itself.
- If auth calls fail with a CORS error, this origin is missing from
  identity's `ALLOWED_ORIGINS`, or `Access-Control-Allow-Credentials` is
  not being returned — see [`identity.md`](identity.md).
- If auth calls fail with a network error (not CORS), `barrins_identity`
  for this `deploy_env` likely isn't deployed — run `barrins_identity.yml`.
- If login succeeds but no cookie appears, identity is missing
  `REFRESH_COOKIE_ENABLED=true` / `REFRESH_COOKIE_DOMAIN` — fix the `.env`
  and redeploy identity.

## Rollback

See [`rollback.md`](rollback.md) for the full procedure. Short version:

```bash
ansible-playbook goblin_guide.yml -e react_frontend_release_tag=<previous-tag>
```

A frontend-only rollback is simpler than a backend one: there is no
database migration to reason about, just a rebuild from the older tag.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Playbook fails before touching the server, "repo has no GitHub release yet" | Cut a release on GitHub, or pin one with `-e react_frontend_release_tag=<tag>`. |
| `register_ssl` fails on "certbot certonly" | DNS not propagated for `goblin{,-staging}.barrins-codex.org`, or port 80 unreachable from the internet. |
| Build fails resolving `@barrins/goblin-guide` | The library build step inside `react_frontend_build_command` failed — check the build log for the `npm --prefix ../../libs/goblin_guide` lines. |
| SPA loads but every auth call fails (CORS error) | This origin missing from identity's `ALLOWED_ORIGINS`, or credentials not allowed — see [`identity.md`](identity.md). |
| Login works but no `refresh_token` cookie, logged out on tab reopen | Identity not in cookie mode: `REFRESH_COOKIE_ENABLED` / `REFRESH_COOKIE_DOMAIN` unset — fix `.env` and redeploy identity. |
| New code not reflected after a run | Confirm you targeted the right `deploy_env`; `--tags deploy` skips the idempotent `register_ssl` (expected). |

## See also

- [`identity.md`](identity.md) — the identity service this SPA
  authenticates against, and its cookie-mode env vars.
- [`frontend.md`](frontend.md) — the other frontends (Tamiyo Scroll /
  Tolaria News), which call `barrins_api` instead.
- [`rollback.md`](rollback.md) — full rollback procedure.
- `docs/project/v2.0.0-bump/identity-goblin-guide-rollout.md` — the
  rollout runbook (Phase 5 is this playbook).
