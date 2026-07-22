# Frontend Deployment — Tamiyo Scroll / Tolaria News

Operational guide for `ops/my-server/tamiyo_scroll.yml` and `tolaria.yml`.
Structured per Constitution §37.2. Both frontends call the shared
`barrins_api` backend — see [`backend.md`](backend.md) for deploying that
first.

| | Tamiyo Scroll | Tolaria News |
| --- | --- | --- |
| Playbook | `tamiyo_scroll.yml` | `tolaria.yml` |
| Production domain | `tamiyo.barrins-codex.org` | `tolaria.barrins-codex.org` |
| Staging domain | `tamiyo-staging.barrins-codex.org` | `tolaria-staging.barrins-codex.org` |
| Source | latest GitHub release tag (or `-e rf_release_tag=<tag>`) | same |
| Deploys the backend too? | No — frontend-only, see [`../architecture/independence.md`](../architecture/independence.md) | Yes — a known, documented exception (embeds its own `barrins_api` copy) |

All commands below run from `ops/my-server/`.

## Preparation

**Server requirements** — `initial.yml`/`setup.yml` must already have run
(same host as the backend). **Backend deployed** — for `tamiyo_scroll.yml`
specifically, `barrins_api.yml` must have been run at least once for the
target `deploy_env` (production or staging) before this frontend has
anything to call.

**DNS** — an A record for the frontend's domain pointing at the server.

**GitHub token** — same `github_token` var as the backend (`repo` scope
covers cloning and, for production, the Releases API).

**Release** (production only) — the app repo needs at least one GitHub
Release published (ADR-2 in
[`../architecture/decisions.md`](../architecture/decisions.md)).

**Configuration** — `VITE_API_BASE_URL` is set automatically by the
playbook (`rf_build_env`, pointed at the backend domain matching
`deploy_env`) — nothing to configure by hand. It's a **build-time**
variable (Vite inlines it into the JS bundle), so changing it needs a new
build (`--tags deploy`), not just a service restart — though note neither
frontend runs a service; "restart" here means re-running the build and
reloading nginx.

## Deployment

```bash
# Staging first
ansible-playbook tamiyo_scroll.yml -e deploy_env=staging
# preview a specific branch instead of the staging default (develop):
ansible-playbook tamiyo_scroll.yml -e deploy_env=staging -e rf_git_branch=my-feature

# Production, once staging is verified — deploys the latest release tag
ansible-playbook tamiyo_scroll.yml
```

Same pattern for `tolaria.yml`.

## Validation

- Open the deployed domain in a browser; confirm the app shell loads
  (`try_files $uri /index.html` SPA fallback — a hard refresh on a deep
  route should still render the app, not 404).
- Exercise a real user flow: signup (verification code lands in email, or
  the backend's service log if `SMTP_HOST` is empty), then whatever the
  app's core action is (deck creation for Tamiyo Scroll, etc.).
- If API calls fail with a CORS error in the browser console, the
  frontend's origin is missing from the backend's `ALLOWED_ORIGINS` — see
  [`backend.md`](backend.md).
- If API calls fail with a network error (not CORS), the backend for this
  `deploy_env` likely hasn't been deployed yet — run `barrins_api.yml`.

## Rollback

See [`rollback.md`](rollback.md) for the full procedure. Short version:

```bash
ansible-playbook tamiyo_scroll.yml -e rf_release_tag=<previous-tag>
```

A frontend-only rollback is simpler than a backend one: there's no
database migration to reason about, just a rebuild from the older tag.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Playbook fails before touching the server, "repo has no GitHub release yet" | Cut a release on GitHub, or pin one with `-e rf_release_tag=<tag>`. |
| `register-ssl` fails on "certbot certonly" | DNS not propagated, or port 80 unreachable from the internet. |
| SPA loads but every API call fails (CORS error) | This frontend's origin missing from the backend's `ALLOWED_ORIGINS` — see [`backend.md`](backend.md). |
| API calls fail with a network error (not CORS) | Backend not deployed yet for this `deploy_env` — run `barrins_api.yml` first. |
| New code not reflected after a run | `--tags deploy` alone doesn't re-run `register-ssl` (idempotent, skips completed work — expected) — confirm you targeted the right `deploy_env`. |

## See also

- [`backend.md`](backend.md) — the shared backend these frontends call.
- [`rollback.md`](rollback.md) — full rollback procedure.
- `ops/my-server/README.md` — "Multiple frontends sharing one backend"
  for why `tolaria.yml` still embeds its own backend copy.
