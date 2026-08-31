# Barrin's Identity + Goblin Guide — rollout runbook

[← Back to project index](./index.md)

| | |
| --- | --- |
| **Purpose** | Close the two deferred T10 phases (deploy playbook + email, then the `barrins_api` cutover) and get Goblin Guide mounted and deployed. |
| **Created** | 2026-08-30 |
| **Release line** | `proj/v2.0.0-bump` — same as [T10](./t10-barrins-identity/index.md). Work each phase on a short `feat/*` branch off it, one logical commit per phase (Constitution §18.3). |
| **Locked decision** | Goblin Guide persistent sessions → a **dedicated auth BFF** holding the refresh token in an `HttpOnly` cookie (user, 2026-08-30). The SPA only ever handles short-lived access tokens. |

**Critical fact:** Phases 3–8 are all blocked until a real `barrins_identity`
is running. Phase 1 is the keystone — do it first, do it fully.

---

## One-glance sequence

```text
Phase 1  Deploy barrins_identity (staging -> prod + email)   <- DO FIRST
Phase 2  ADR-18 + BFF docs                                    (parallel with 1B)
Phase 3  Build apps/goblin_guide_bff
Phase 4  Wire libs/goblin_guide to the BFF
Phase 5  Deploy goblin_guide (SPA + BFF playbook)
Phase 6  Live UAT T11-T15
Phase 7  Mount in tamiyo_scroll + tolaria_news
Phase 8  barrins_api cutover                                  <- DO LAST
```

Deferred, **not** on this path: `Q-02` (tolaria_news scope), `Q-05`
(username-as-credential), [integration.md](../../content/back/barrins_identity/integration.md)
§4.5 service-account settings path.

---

## Phase 0 — Lock two decisions (no code)

### 0.1 — Identity playbook: new role or reuse?

**Decision: reuse.** `fastapi_backend` is already generic (clone release
tag → `uv sync` → `alembic upgrade head` → systemd unit → `.env` deploy).
The identity playbook invokes `github_token` + `register_ssl` +
`fastapi_backend` + `backend_website` with identity parameters, exactly
like `barrins_api.yml`. The only gap is the one-time `create_admin.py`
seed — a `post_tasks` reminder, run by hand on the VPS (needs a TTY).
No new role.

### 0.2 — BFF endpoint scope (decide at Phase 3, not now)

| Option | Effect |
| --- | --- |
| (a) BFF proxies **all** identity endpoints | SPA has one origin; BFF grows |
| (b) BFF exposes **only** `/auth/token`, `/auth/refresh`, `/auth/logout` | Smallest BFF; signup/reset/settings/delete/service-accounts go SPA → identity directly, so identity `ALLOWED_ORIGINS` must list the SPA origin |

Leaning **(b)**. Record the choice in ADR-18 (Phase 2).

---

## Phase 1 — Deploy `barrins_identity` 🔑

### 1A — Manual infra prep (operator — cannot be automated)

Work through [identity.md](../../content/ops/deployment/identity.md)
"Preparation" + "Email verification".

- [X] **DNS** — OVH DNS zone for `barrins-codex.org`, add A records:
  - `identity-staging` → `146.59.146.57`
  - `identity` → `146.59.146.57`
  - Verify: `dig +short identity-staging.barrins-codex.org` returns the IP.
- [X] **PostgreSQL** — on the VPS, as the `postgres` superuser:

  ```sql
  CREATE DATABASE barrins_identity_staging;
  CREATE ROLE barrins_identity_staging LOGIN PASSWORD '<pw-staging>';
  GRANT ALL ON DATABASE barrins_identity_staging TO barrins_identity_staging;
  -- repeat with the _prod_ suffix for production, different password
  ```

- [X] **Signing keys** — one RSA key per environment:

  ```bash
  openssl genrsa 2048     # staging  — capture the full PEM
  openssl genrsa 2048     # production — capture the full PEM
  ```

- [X] **Brevo** — [identity.md](../../content/ops/deployment/identity.md)
  "Email verification" steps 1–6:
  - Create the Brevo account → add sending domain `barrins-codex.org`.
  - Publish DKIM (2× CNAME), SPF `include:spf.brevo.com` (**edit** the
    existing apex SPF — never add a 2nd SPF record), DMARC TXT at
    `_dmarc` (`p=none`), and the `brevo-code…` ownership TXT — all in the
    OVH DNS zone.
  - Verify green in Brevo
    (`dig +short CNAME brevo1._domainkey.barrins-codex.org`).
  - OVH → Email → redirect `identity@barrins-codex.org` → an inbox you read.
  - Brevo → SMTP & API → generate an SMTP key. Note the login +
    `smtp-relay.brevo.com:587`. The **SMTP key** is `SMTP_PASSWORD`, not
    the account password.
- [X
] **Secrets files** — from the templates already in the repo:

  ```bash
  cd ops/my-server/secrets/barrins_identity
  cp staging.env.example    staging.env
  cp production.env.example  production.env
  ```

  Fill each (git-ignored — §34):

  | Var | staging | production |
  | --- | --- | --- |
  | `DATABASE_URL` | staging DB above | prod DB above |
  | `JWT_PRIVATE_KEY` | staging PEM | prod PEM |
  | `JWT_KID` | `2026-08` | `2026-08` |
  | `ALLOWED_ORIGINS` | `["https://goblin-staging.barrins-codex.org"]` | `["https://goblin.barrins-codex.org"]` |
  | `ENVIRONMENT` | `staging` | `production` |
  | `REQUIRE_EMAIL_VERIFICATION` | `false`, then `true` for the email test | **`true`** |
  | `SMTP_HOST` / `_PORT` / `_USERNAME` / `_PASSWORD` / `_USE_TLS` | Brevo values | Brevo values |
  | `SMTP_FROM_ADDRESS` | `identity@barrins-codex.org` | same |
  | `FRONTEND_BASE_URL` | `https://goblin-staging.barrins-codex.org` | `https://goblin.barrins-codex.org` |

  Goblin Guide is not deployed until Phase 5 — these origin / URL values
  are the targets that phase will create. Identity boots fine before
  Goblin Guide exists; only the email links won't resolve yet.

**Gate 1A:** `dig` resolves both subdomains; both `.env` files filled;
Brevo shows SPF + DKIM green.

### 1B — Author the playbook

- **New file** `ops/my-server/barrins_identity.yml` — modelled on
  `barrins_api.yml`; **one application, one playbook** (§26.1): no
  `barrins_api` role, no shared-backend restart.
  - `vars`: `deploy_env` (default `production`), `env_suffix`,
    `env_branch`, `identity_port` (`8021` prod / `8521` staging),
    `identity_domain` = `identity{{ env_suffix }}.barrins-codex.org`,
    `identity_env_file` = `secrets/barrins_identity/{{ deploy_env }}.env`.
  - `roles:`
    - `github_token`
    - `register_ssl` — `register_ssl_server_name: "{{ identity_domain }}"`,
      `register_ssl_contact_name: martin.cuchet@gmail.com`
    - `fastapi_backend`:

      ```yaml
      fastapi_backend_repo: Spigushe/barrins-project
      fastapi_backend_repo_subdir: apps/barrins_identity
      fastapi_backend_server_name: "{{ identity_domain }}"
      fastapi_backend_app_name: "identity{{ env_suffix }}"
      fastapi_backend_port: "{{ identity_port }}"
      fastapi_backend_use_release_tag: "{{ deploy_env == 'production' }}"
      fastapi_backend_git_branch: "{{ env_branch }}"
      fastapi_backend_entrypoint: "app.main:app"
      fastapi_backend_env_file: "{{ identity_env_file }}"
      ```

      (the role already runs `uv sync` + `alembic upgrade head` and writes
      the systemd unit `identity{{ env_suffix }}`)
    - `backend_website` —
      `backend_website_server_name: "{{ identity_domain }}"`,
      `backend_website_port: "{{ identity_port }}"`,
      `backend_website_rate_limited_paths: []`
  - `post_tasks:` — a `debug` reminder that
    `scripts/create_admin.py --email … --username …` must be run once by
    hand on the VPS (interactive, needs a TTY — same pattern as
    `barrins_api.yml`'s Alembic reminder), and a reminder that
    `ALLOWED_ORIGINS` / `FRONTEND_BASE_URL` must list the Goblin Guide
    origin.
- **Verify** the two `secrets/barrins_identity/*.env.example` files carry
  every var from [platform.md §8](../../content/back/barrins_identity/platform.md);
  add any missing.
- **Lint:** from the repo root, `ansible-lint ops/my-server` must stay
  clean (§26.4 — run in WSL/Linux; if WSL is unreliable, do the manual
  §26.4 checklist review and let CI confirm).

**Gate 1B:** `ansible-lint ops/my-server` clean (or CI green); playbook
reviewed against `barrins_api.yml` for §26.1 independence.

### 1C — Deploy staging + validate

```bash
cd ops/my-server
# proj/v2.0.0-bump is not on the `staging` branch yet — point staging at
# the rollout branch explicitly (the playbook's default env_branch is
# `staging`).
ansible-playbook barrins_identity.yml -e deploy_env=staging \
  -e fastapi_backend_git_branch=proj/v2.0.0-bump

# then, one-time, on the VPS:
ssh spigushe@146.59.146.57
cd ~/projects/identity-staging.barrins-codex.org/apps/barrins_identity
uv run python scripts/create_admin.py --email you@… --username admin
```

**Two prerequisites that bit us on the first staging run (do them before
the prod run too — see also 1A):**

1. **DB password must be `%`-free.** `alembic/env.py` feeds the DSN through
   `configparser` (`set_main_option`), which treats `%` as interpolation —
   a URL-encoded password (`==` → `%3D%3D`) makes `alembic upgrade head`
   die with `invalid interpolation syntax`. Use a hex password
   (`openssl rand -hex 32`) until `env.py` is patched to escape `%`.
2. **PostgreSQL 15+ `public` schema grant.** `GRANT ALL ON DATABASE` does
   *not* grant table-creation on schema `public` on PG15+. After creating
   the DB + role, run (as `postgres`):

   ```sql
   ALTER DATABASE barrins_identity_staging OWNER TO barrins_identity_staging;
   \c barrins_identity_staging
   ALTER SCHEMA public OWNER TO barrins_identity_staging;
   ```

   Otherwise the migration fails with `permission denied for schema public`.

Validation ([identity.md](../../content/ops/deployment/identity.md)
"Validation"):

- [x] `curl -fsS https://identity-staging.barrins-codex.org/health` →
      `{"status":"ok"}`
- [x] `curl -fsS https://identity-staging.barrins-codex.org/.well-known/jwks.json`
      → single key, `kid` = `2026-08`
- [x] `POST /api/v1/auth/token` with the seeded admin → token pair;
      `/auth/refresh` → new pair; `/auth/logout` then reuse the old token
      → `401`
- [x] Set `REQUIRE_EMAIL_VERIFICATION=true` + real `SMTP_*` on staging,
      restart, run the [identity.md](../../content/ops/deployment/identity.md)
      step-7 signup → email → verify against a real inbox. Gmail "Show
      original" → SPF / DKIM / DMARC all PASS. Repeat for
      `/auth/password-reset/request` → `/confirm`.
      *(2026-08-31: password-reset exercised end-to-end — code delivered,
      SPF+DKIM+DMARC all `pass`. Signup-verify uses the same SMTP path.)*
- [x] `journalctl -u identity-staging -n 50` — no tracebacks.

**Gate 1C:** every box above checked. **Do not proceed to production
until the email round-trip works on staging.** ✅ closed 2026-08-31.

### 1D — Deploy production + validate

Cut a `proj/v2.0.0-bump` release tag first (§27.1 — production only
deploys releases), then:

```bash
ansible-playbook barrins_identity.yml      # defaults to production + latest release tag
# one-time create_admin on ~/projects/identity.barrins-codex.org/... as above
```

- [ ] Same four validation checks against `https://identity.barrins-codex.org`
- [ ] One real signup + verify against production
- [ ] `journalctl -u identity -n 50` clean

**Gate 1D:** production identity live and email-verified. **The T10
"playbook + email" phase is closed.** Flip the status banners in
[identity.md](../../content/ops/deployment/identity.md) and
[platform.md](../../content/back/barrins_identity/platform.md); add a note
to [the T10 tracker](./t10-barrins-identity/index.md).

---

## Phase 2 — ADR + docs for the Goblin Guide BFF

Can run in parallel with Phase 1B.

- **New** `### ADR-18: Goblin Guide auth BFF holds the refresh token in an
  HttpOnly cookie` in
  [decisions.md](../../content/ops/architecture/decisions.md) — Context /
  Alternatives (in-memory only; `localStorage`; BFF) / Trade-offs /
  Decision / Consequences (§16.3). Resolve decision 0.2 here and record it.
- **Update:**
  - [bootstrap.md](../../content/front/goblin_guide/bootstrap.md) —
    session-persistence section
  - [platform.md §5](../../content/back/barrins_identity/platform.md) —
    add the BFF hop to the diagram
  - [integration.md](../../content/back/barrins_identity/integration.md) —
    note the BFF as a consumer
  - [identity.md](../../content/ops/deployment/identity.md) —
    `ALLOWED_ORIGINS` includes the SPA origin (if 0.2 = option b)

**Gate 2:** `mkdocs build --strict` + `markdownlint` + `cspell` clean.

---

## Phase 3 — Build the Goblin Guide auth BFF

- **New app** `apps/goblin_guide_bff/` — FastAPI, stack per §11.2 (`uv`,
  `ty`, `ruff`). Structure mirrors `apps/barrins_identity/app/`.
  - Endpoints (scope per decision 0.2):
    - `POST /auth/token` → forwards credentials to
      `IDENTITY_SERVICE_URL/api/v1/auth/token`; on success sets
      `refresh_token` as `HttpOnly; Secure; SameSite=Lax` cookie (path
      `/auth`), returns only `{access_token, expires_in}` to the SPA.
    - `POST /auth/refresh` → reads the cookie, calls identity
      `/auth/refresh`, rotates the cookie, returns the new access token.
    - `POST /auth/logout` → calls identity `/auth/logout`, clears the
      cookie.
    - (option a only) transparent proxy for the lifecycle routes.
  - Config: `IDENTITY_SERVICE_URL`, `ALLOWED_ORIGINS` (the SPA origin),
    `COOKIE_DOMAIN`, `COOKIE_SECURE=true`.
  - `GET /health` → `{"status":"ok"}`.
  - Tests with `respx` mocking identity (≥ the repo's coverage bar).
- **CI:** add a `goblin_guide_bff` job + paths-filter entry in
  `.github/workflows/CI.yml`, wire it into `ci-required` (same pattern as
  the `identity` job added in T10).
- **Docs:** new `docs/content/front/goblin_guide/bff.md` — every endpoint
  per §21.1 (method, path, purpose, auth, request, response, errors).

**Gate 3:** `uv run pytest` green; `ruff` / `ty` clean; CI job passing.

---

## Phase 4 — Wire `libs/goblin_guide` to the BFF

- In `libs/goblin_guide/src/auth/client.ts` /
  `libs/goblin_guide/src/auth/IdentityProvider.tsx`: add a "BFF mode"
  where the base URL points at the BFF, `credentials: 'include'` on
  fetches, and refresh is driven by the BFF cookie rather than a stored
  refresh token.
- Keep `createMemoryTokenStore()` as the default for host apps that don't
  run a BFF; BFF mode simply doesn't need a token store for the refresh
  token.
- Update `apps/goblin_guide/src/config.ts` to BFF mode; the shell
  `.env.example` gets `VITE_BFF_BASE_URL`.
- Tests: `libs/goblin_guide/src/auth/client.test.ts` + shell tests for
  the cookie flow.

**Gate 4:** `npm test` + `tsc` + lint green in both `libs/goblin_guide`
and `apps/goblin_guide`. (A CRLF checkout can break local
`prettier --check` — CI is authoritative.)

---

## Phase 5 — Goblin Guide deploy playbook

Claude authors, operator runs.

- **New file** `ops/my-server/goblin_guide.yml` — **one playbook for the
  app** (SPA + its BFF = one application, §26.1); never touches identity
  or `barrins_api`.
  - `register_ssl` for `goblin{{ env_suffix }}.barrins-codex.org`.
  - `fastapi_backend` for `apps/goblin_guide_bff` → systemd unit
    `goblin-bff{{ env_suffix }}`, port e.g. `8022` / `8522`,
    `env_file: secrets/goblin_guide_bff/{{ deploy_env }}.env`.
  - `react_frontend` for `apps/goblin_guide` with
    `react_frontend_build_env: { VITE_BFF_BASE_URL: "https://goblin{{ env_suffix }}.barrins-codex.org" }`
    (SPA routing / `index.html` fallback via that role's `https.conf.j2`).
  - nginx: `/auth` (or `/api`) → BFF port, `/` → static build. May need a
    small vhost tweak or the `backend_website` role alongside
    `react_frontend` — decide when authoring.
- **Operator:** DNS A records `goblin` + `goblin-staging` →
  `146.59.146.57`; `cp` + fill
  `secrets/goblin_guide_bff/{staging,production}.env`; add both Goblin
  origins to identity's `ALLOWED_ORIGINS` and redeploy identity
  (`ansible-playbook barrins_identity.yml` — its own playbook, no
  cross-touch).
- Deploy staging → prod, each release-tagged.

**Gate 5:** `https://goblin-staging.barrins-codex.org` loads; login sets
an `HttpOnly` cookie (DevTools → Application → Cookies); closing and
reopening the tab keeps you logged in; `ansible-lint` clean.

---

## Phase 6 — Live UAT for T11–T15

Against `goblin-staging`, walk each tracker's unchecked "run against a
live barrins_identity" box:

- [ ] **T11** login — bad creds, good creds, token refresh after 10 min
- [ ] **T12** signup + email verification — real inbox, resend cooldown,
      wrong code
- [ ] **T13** password reset — request → email → confirm → old token `401`
- [ ] **T14** account settings + delete — display-name change,
      email-change (verify at the new address), soft-delete then
      handle / email reuse
- [ ] **T15** admin service accounts — create (secret shown once), list,
      revoke

Tick the boxes in each `docs/project/v2.0.0-bump/t1{1..5}-*/index.md`.

**Gate 6:** all five trackers fully checked.

---

## Phase 7 — Mount Goblin Guide in the two frontends

- `apps/tamiyo_scroll` + `apps/tolaria_news`: add the
  `@barrins/goblin-guide` dependency, mount its `IdentityProvider` +
  screens, replace any local auth UI.
- Session persistence per app is a **separate decision** — they can start
  with the in-memory store (re-login on tab close) or get their own BFF
  later. Note it in each app's tracker; don't block Phase 7 on it.
- Update `tamiyo_scroll.yml` / `tolaria_news.yml` build env if they need
  `VITE_IDENTITY_BASE_URL`.

**Gate 7:** both apps build + test green; login works against production
identity.

---

## Phase 8 — `barrins_api` cutover (highest risk)

Only after Phases 1–7 are done and identity has run clean in production
for a while. Full checklist in
[platform.md §10](../../content/back/barrins_identity/platform.md):

1. **Claude:** `apps/barrins_api/scripts/migrate_users_to_identity.py` —
   copies `users` rows into identity's database inside a single
   `target_engine.begin()` transaction.
2. **Claude:** add `libs/identity_client` as a `[tool.uv.sources]` path
   dep; rewrite `app/dependencies/auth.py` to JWKS verification; delete
   `app/models/user.py`, `app/schemas/auth.py`, `app/core/security.py`,
   `app/api/v1/routers/auth.py`, `scripts/create_admin.py`; Alembic
   migration dropping the local `users` table; swap `python-jose` /
   `argon2-cffi` → `pyjwt` + `respx` (test-only); config swap in
   `app/config/base.py`.
3. **Test** the migration script against two throwaway databases in
   CI / dev (no confirmation needed there).
4. **Operator:** declare a maintenance window. `pg_dump` both databases.
   Run the migration against production data. Deploy the cutover release.
   Validate every `barrins_api` auth path + the Tolaria News / Tamiyo
   Scroll logins.
5. **Rollback:** restore the `pg_dump` + redeploy the previous
   `barrins_api` release tag.

**Gate 8:** `barrins_api` authenticates purely via identity JWKS; the
local `users` table is gone; both frontends still log in. **T10 fully
closed.**
