# Barrin's Identity + Goblin Guide — rollout runbook

[← Back to project index](./index.md)

| | |
| --- | --- |
| **Purpose** | Close the two deferred T10 phases (deploy playbook + email, then the `barrins_api` cutover) and get Goblin Guide mounted and deployed. |
| **Created** | 2026-08-30 |
| **Release line** | `proj/v2.0.0-bump` — same as [T10](./t10-barrins-identity/index.md). Work each phase on a short `feat/*` branch off it, one logical commit per phase (Constitution §18.3). |
| **Locked decision** | Goblin Guide persistent sessions → **`barrins_identity` itself** issues the refresh token as an `HttpOnly` cookie; the SPA calls identity directly and only ever handles short-lived access tokens. **No separate BFF app** (user, 2026-08-31 — supersedes the 2026-08-30 "dedicated auth BFF" decision). SPA and identity are on different sub-domains ⇒ the cookie is `HttpOnly; Secure; SameSite=None` and identity returns `Access-Control-Allow-Credentials: true` for the SPA origin. |

**Critical fact:** Phases 3–8 are all blocked until a real `barrins_identity`
is running. Phase 1 is the keystone — do it first, do it fully.

---

## One-glance sequence

```text
Phase 1     Deploy barrins_identity (staging -> prod + email)   <- DO FIRST
Phase 2     ADR-18 + docs (identity cookie mode, no BFF app)    (parallel with 1B)
Phase 3     Add HttpOnly-cookie auth mode to barrins_identity   [committed]
Phase 4     Wire libs/goblin_guide to identity (direct + cookie) [committed]
Phase 4bis  Application directory (identity table + endpoint + screen) [built, uncommitted]
Phase 5     Deploy goblin_guide SPA (staging done + smoke-tested; PROD LAST)
Phase 6     Live UAT T11-T15                          [validated 2026-09-01]
Phase 7+8   tamiyo_scroll swap + barrins_api cutover  [code complete 2026-09-02]
            (merged; tolaria_news deferred, Q-02 open; operator migration pending)
```

Phases 2 → 4bis all land on staging before Phase 5; production (identity
Phase 1D + Goblin Guide Phase 5-prod) is promoted only once staging is
complete (user, 2026-08-31).

**Goblin Guide's production deploy (Phase 5-prod) is done last of all**
(user, 2026-09-01) — after Phases 6–8, as the final step of the rollout.
Staging carries everything until then.

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

### 0.2 — Auth persistence: BFF app vs identity-native cookie

**Decision (user, 2026-08-31): identity-native cookie, no BFF app.**
`barrins_identity` itself grows an opt-in cookie mode on `/auth/token`,
`/auth/refresh`, `/auth/logout` (Phase 3); every other flow (signup,
reset, settings, delete, service-accounts) already goes SPA → identity
directly, so identity's `ALLOWED_ORIGINS` must list the SPA origin and
CORS must allow credentials. Supersedes the 2026-08-30 "dedicated auth
BFF app" decision; recorded in ADR-18.

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
- [X] **Secrets files** — from the templates already in the repo:

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
ansible-playbook barrins_identity.yml   # production + latest release tag
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

## Phase 2 — ADR + docs for identity cookie mode

Can run in parallel with Phase 1B.

- **New** `### ADR-18: barrins_identity issues the refresh token as an
  HttpOnly cookie (no separate BFF app)` in
  [decisions.md](../../content/ops/architecture/decisions.md) — Context /
  Alternatives (in-memory only; `localStorage`; dedicated BFF app;
  identity-native cookie) / Trade-offs / Decision / Consequences (§16.3).
  Record: identity-native cookie chosen; supersedes the 2026-08-30
  "dedicated auth BFF" decision. Cross-site (SPA on
  `goblin{-staging}.barrins-codex.org`, identity on
  `identity{-staging}.barrins-codex.org`) ⇒ `SameSite=None; Secure` +
  `Access-Control-Allow-Credentials: true` for the exact SPA origin (no
  wildcard, §33).
- **Update:**
  - [bootstrap.md](../../content/front/goblin_guide/bootstrap.md) —
    session-persistence section (cookie from identity, not a BFF)
  - [platform.md §5](../../content/back/barrins_identity/platform.md) —
    the SPA calls identity directly; note the refresh cookie
  - [integration.md](../../content/back/barrins_identity/integration.md) —
    the browser SPA as a first-party cookie consumer
  - [identity.md](../../content/ops/deployment/identity.md) —
    `ALLOWED_ORIGINS` includes the SPA origin; add
    `Access-Control-Allow-Credentials` and the cookie-mode env vars

**Gate 2:** `mkdocs build --strict` + `markdownlint` + `cspell` clean.

---

## Phase 3 — Add HttpOnly-cookie auth mode to `barrins_identity`

Agent 1. A backward-compatible extension of the existing auth contract
(§4.4) — the JSON `refresh_token` stays in the body by default; cookie
mode is opt-in per request so other consumers are untouched.

- **All five endpoints that mint a `TokenPair`** — `/auth/token`,
  `/auth/refresh`, `/auth/signup` (the `REQUIRE_EMAIL_VERIFICATION=false`
  branch), `/auth/signup/verify`, `/auth/password-reset/confirm` — plus
  `/auth/logout`, route through one helper (`app/core/cookies.py`) and
  gain cookie behaviour when the caller opts in (`X-Client: web`):
  - the token-minters set the `refresh_token` cookie
    (`HttpOnly; Secure; SameSite=<REFRESH_COOKIE_SAMESITE>;
    Domain=<REFRESH_COOKIE_DOMAIN>; Path=/api/v1/auth`) and omit
    `refresh_token` from the body (`response_model_exclude_none=True`).
  - `refresh` reads the cookie (body still accepted), rotates it.
  - `logout` clears the cookie.
- Non-cookie callers (no opt-in header) keep today's body-only behaviour.
- Config: `REFRESH_COOKIE_ENABLED` (default `false`),
  `REFRESH_COOKIE_DOMAIN`, `REFRESH_COOKIE_SAMESITE` (default `none`). The
  CORS side needs nothing new — `app/main.py` already runs
  `CORSMiddleware` with `allow_credentials=True` against a concrete
  `ALLOWED_ORIGINS`.
- Tests (`tests/test_routes_auth.py` + signup / reset flows) — cookie set
  / rotated / cleared, body still carries `refresh_token` without the
  opt-in, opt-in ignored when the feature is off, `/refresh` by cookie and
  by body, CORS credentials header present for an allowed origin only.
  Coverage ≥ the repo bar.
- **Docs:** extend the auth section of
  [platform.md](../../content/back/barrins_identity/platform.md) /
  [integration.md](../../content/back/barrins_identity/integration.md)
  per §21.1.
- **CI:** the existing `identity` job covers it — no new job.

**Gate 3:** `uv run pytest` green; `ruff` / `ty` clean; `identity` CI job
passing.

---

## Phase 4 — Wire `libs/goblin_guide` to identity (direct + cookie)

- In `libs/goblin_guide/src/auth/client.ts` /
  `libs/goblin_guide/src/auth/IdentityProvider.tsx`: add a "cookie mode"
  where auth calls go straight to `IDENTITY_SERVICE_URL` with
  `credentials: 'include'` and the `X-Client: web` opt-in header, and
  refresh relies on the identity cookie rather than a stored refresh
  token.
- Keep `createMemoryTokenStore()` as the default for host apps not in
  cookie mode; cookie mode needs no store for the refresh token.
- Update `apps/goblin_guide/src/config.ts` to cookie mode; the shell
  `.env.example` gets `VITE_IDENTITY_SERVICE_URL`.
- Tests: `libs/goblin_guide/src/auth/client.test.ts` + shell tests for
  the cookie flow.

**Gate 4:** `npm test` + `tsc` + lint green in both `libs/goblin_guide`
and `apps/goblin_guide`. (A CRLF checkout can break local
`prettier --check` — CI is authoritative.)

---

## Phase 4bis — Application directory ✅ (built 2026-08-31, uncommitted)

A role-aware cross-app launcher in Goblin Guide. **"Which apps can this
user open" is a business rule → backend** (§4.1: identity returns the
list + a computed access state per app; the SPA only renders cards).
Ships with Phase 5 so the UX lands in the same deploy (user, 2026-08-31).
Design locked as [ADR-19](../../content/ops/architecture/decisions.md#adr-19-barrins_identity-owns-the-cross-app-directory).

### `barrins_identity` — done

- **New table `applications`** — migration `a7b8c9d0e1f2` (create + seed).
  Columns: `key` (unique slug), `name`, `description`, `url`, `logo_svg`
  (`TEXT`, inline SVG — see below), `needs_authentication` (default
  `true`), `is_role_restricted` (default `false`), `min_role`
  (`Enum userrole`, nullable, reuses `users.role`'s type), `sort_order`,
  `is_active`, timestamps. DB `CHECK`: `is_role_restricted ⇒ min_role IS
  NOT NULL AND needs_authentication`.
- **Logos in the DB, not duplicated asset files** (revises decision B of
  2026-08-31 — "store in DB", user). `logo_svg` holds inline SVG markup;
  the SPA renders it as an `<img>` `data:` URI, so untrusted markup still
  can't run scripts. Migration seeds small house-style marks.
- **Seed** (user-approved 2026-08-31; `docs` deliberately excluded —
  "ne pas afficher docs dans goblin guide", user):

  | key | name | policy |
  | --- | --- | --- |
  | `goblin_guide` | Goblin Guide | `needs_authentication` |
  | `tamiyo_scroll` | Tamiyo Scroll | `needs_authentication` |
  | `tolaria_news` | Tolaria News | public |
  | `karn_jupyter` | Karn Tablets | `is_role_restricted`, `min_role = ml_developer` |

- **Endpoint `GET /api/v1/applications`** — optional bearer
  (`get_optional_current_user`: absent header ⇒ anonymous; present-but-
  invalid ⇒ `401`). Returns every `is_active` app ordered by
  `sort_order` then `name`, as
  `{ key, name, description, url, logo_svg, access, min_role }`. Backend
  computes `access`:
  - `!needs_authentication` → `open`
  - `needs_authentication && !is_role_restricted` → `open` if
    authenticated, else `login_required`
  - `is_role_restricted` → `open` if `role.level >= min_role.level`;
    `role_denied` if authenticated and below; `login_required` if anon
  - does **not** filter the current app — the SPA does.
- `app/models/application.py`, `app/schemas/applications.py`,
  `app/services/applications.py` (`compute_access` + `list_applications`),
  `app/api/v1/applications.py`; router wired. Tests: `test_models`,
  `test_services_applications`, `test_routes_applications`,
  `test_dependencies` (optional-user). Full suite **349 passed, 98.83%**.
  API doc: [integration.md §4.7](../../content/back/barrins_identity/integration.md#47-application-directory-adr-19),
  [platform.md §7 `applications`](../../content/back/barrins_identity/platform.md).

### `libs/goblin_guide` — done

- `applicationSchema` / `applicationListSchema` in `auth/schemas.ts`
  (`access` ∈ `open | login_required | role_denied`); `listApplications()`
  on `IdentityClient` (via `authed` — works signed out); `useApplications()`
  hook (always enabled, re-keyed on auth state).
- `components/ApplicationsScreen.tsx` — prop `currentAppKey?: string`;
  drops the row whose `key === currentAppKey`, groups by `access`
  (**Available** / **Sign in to open** / **Restricted**), renders cards
  (logo `<img>` data URI, name, description, badge — "Sign in" /
  "Needs `<role>`").
- Tests: `ApplicationsScreen.test.tsx` (groups, current-app filter, badge
  states, error/empty), `client.test.ts` (`listApplications` signed-out /
  signed-in / error). Lib `npm test` **103 passed**.

### `apps/goblin_guide` — done

- The home page (`/` → `Shell`) is now **two columns**: `<AccountScreen>`
  and `<ApplicationsScreen currentAppKey={CURRENT_APP_KEY} />` in a
  responsive grid (stacks on narrow screens). No separate route (user,
  2026-08-31). `CURRENT_APP_KEY = 'goblin_guide'` in `config.ts`. Shell
  `npm test` **16 passed**, `tsc` + lint clean.

**Gate 4bis:** ✅ `uv run pytest` (identity) green (349, 98.83%);
`npm test` + `tsc` + lint green in lib and shell; anon / user /
`ml_developer` / admin each render the right cards with the right badges;
`goblin_guide` absent from its own list.

---

## Phase 5 — Goblin Guide deploy playbook (SPA only)

Claude authors, operator runs. **Authoring done & committed:**
`ops/my-server/goblin_guide.yml` + the
[Goblin Guide deployment guide](../../content/ops/deployment/goblin-guide.md)
(wired into the docs nav, deployment index and `rollback.md`).
**Staging deployed and smoke-tested 2026-09-01** (SPA loads, cross-site
`HttpOnly` cookie set, reload keeps the session — the cookie-mode
session-restore gap found here is fixed, see Phase 6 T11). **Production
deploy is deferred to the very end of the rollout** (after Phases 6–8 —
user, 2026-09-01); staging carries all remaining work.

- **New file** `ops/my-server/goblin_guide.yml` ✅ — **one playbook, one
  app** (the SPA; §26.1). No backend role, no systemd unit, **never
  touches identity or `barrins_api`**.
  - `register_ssl` for `goblin{{ env_suffix }}.barrins-codex.org`.
  - `react_frontend` for `apps/goblin_guide`; build env
    `VITE_IDENTITY_SERVICE_URL` = `https://identity{{ env_suffix
    }}.barrins-codex.org` (SPA routing / `index.html` fallback via that
    role's `https.conf.j2`).
  - `react_frontend_build_command` overridden: `apps/goblin_guide` pulls
    `libs/goblin_guide` (`@barrins/goblin-guide`) as a `file:` dep whose
    `dist/` is git-ignored, so the command runs
    `npm --prefix ../../libs/goblin_guide install && … run build` before
    `npm run build` for the shell.
- **Operator:**
  - DNS A records `goblin` + `goblin-staging` → `146.59.146.57`.
  - In `secrets/barrins_identity/{staging,production}.env`: set
    `REFRESH_COOKIE_ENABLED=true`, `REFRESH_COOKIE_DOMAIN`
    (`identity{,-staging}.barrins-codex.org`), and confirm the Goblin
    origin is in `ALLOWED_ORIGINS`. Then **redeploy identity** from a ref
    carrying Phases 3 + 4bis (`ansible-playbook barrins_identity.yml` —
    its own playbook, no cross-touch).
  - Deploy the SPA: staging → prod, each release-tagged.

**Gate 5:** ✅ staging (2026-09-01) —
`https://goblin-staging.barrins-codex.org` loads; login sets an
`HttpOnly; SameSite=None` cookie on `identity-staging…` (DevTools →
Application → Cookies); cross-site refresh works; closing and reopening
the tab keeps you logged in; the app directory renders; `ansible-lint`
clean. **Production deploy deferred to the end of the rollout (after
Phases 6–8).**

---

## Phase 6 — Live UAT for T11–T15

Against `goblin-staging`, walk each tracker's unchecked "run against a
live barrins_identity" box:

- [X] **T11** login — bad creds, good creds, token refresh after 10 min,
      **reload / reopen tab keeps you logged in** (cookie-mode session
      restore on load — Phase 4 shipped the cookie plumbing but not the
      on-load restore; fixed after UAT, `libs/goblin_guide`
      `IdentityProvider` + `useIdentity().isBootstrapping`)
- [X] **T12** signup + email verification — real inbox, resend cooldown,
      wrong code
- [X] **T13** password reset — request → email → confirm → old token `401`
- [X] **T14** account settings + delete — display-name change,
      email-change (verify at the new address), soft-delete then
      handle / email reuse
- [X] **T15** admin service accounts — create (secret shown once), list,
      revoke

Tick the boxes in each `docs/project/v2.0.0-bump/t1{1..5}-*/index.md`.

**Gate 6:** ✅ closed 2026-09-01 — all five flows exercised against
`https://goblin-staging.barrins-codex.org` + `identity-staging`; every
T11–T15 tracker's "run against a live `barrins_identity`" box ticked.

---

## Phase 7 + 8 — `tamiyo_scroll` swap + `barrins_api` cutover (merged)

**Merged** (user, 2026-09-01): a `tamiyo_scroll` access token is the
`Bearer` on every `barrins_api` data call, so the frontend swap and the
backend JWKS cutover ship as one change on `feat/goblin-guide-login`.
`tolaria_news` is **deferred entirely** (no auth today — `Q-02` open).
Cookie mode, like Goblin Guide. Full plan +
[ADR-20](../../content/ops/architecture/decisions.md#adr-20-barrins_api-trusts-barrins_identity-jwks-drops-its-users-table).

**Code complete 2026-09-02** on `feat/goblin-guide-login`:

- `barrins_api`: JWKS verification (`app/dependencies/auth.py` +
  `service_auth.py` on `libs/identity_client`), `app/core/roles.py`
  (`placeholder` → `moderator`), local auth surface deleted, Alembic
  `d9e1a2c3b4f5` (drops 12 FKs + `auth_email_verifications` + `users` +
  `userrole`), `app/services/identity_directory.py` (batch label lookup,
  TTL cache), `resolve_owner` → opaque `ts_user_settings` key,
  `ResponseTeamMember.email` → `username`, admin "total accounts" metric
  dropped, config + `pyproject.toml` swap. Full suite green (530,
  95.4%). `scripts/migrate_users_to_identity.py` + tests (7, two
  throwaway DBs).
- `barrins_identity`: `POST /api/v1/users/lookup` (service token, scope
  `identity:users:read`) + tests (9).
- `apps/tamiyo_scroll`: `@barrins/goblin-guide` mounted — `IdentityProvider`
  (cookie mode), library `<LoginScreen>` / `<SignupScreen>` /
  `<VerifyEmailScreen>` / `<ForgotPasswordScreen>` / `<ResetPasswordScreen>` /
  `<AccountScreen>` with the "Try the demo" entry point, `api/client.ts`
  on `identityTokenStore` + `identityClient.refresh()`, `AdminMetricsPage`
  without the accounts tile.
- Ops: `tamiyo_scroll.yml` gains `VITE_IDENTITY_SERVICE_URL` +
  `libs/goblin_guide` prebuild; `barrins_api.yml` / secrets swap
  `SECRET_KEY` → `IDENTITY_SERVICE_URL` + the service-account pair.

**Operator, in a maintenance window** — see the
[identity-cutover runbook](../../content/ops/deployment/identity-cutover.md):
add the Tamiyo origins to identity `ALLOWED_ORIGINS` + redeploy identity;
`pg_dump` both DBs; run `migrate_users_to_identity.py` (`--dry-run`, then
real); deploy `barrins_api.yml` + `tamiyo_scroll.yml` for staging from
the branch; validate every auth path + Tamiyo login; rollback = restore
both dumps + redeploy the previous `barrins_api` release tag.

**Gate 7+8:** `barrins_api` authenticates purely via identity JWKS; the
local `users` table is gone; `tamiyo_scroll` logs in through the Goblin
Guide screens in cookie mode; `/demo` still works. **T10 closed once the
operator migration + Goblin Guide prod deploy land.**

> **Phase 8** (the standalone `barrins_api` cutover) was **merged into
> Phase 7** above for `tamiyo_scroll` (user, 2026-09-01). The operator
> data-migration checklist that used to live here is now the
> [identity-cutover runbook](../../content/ops/deployment/identity-cutover.md).
