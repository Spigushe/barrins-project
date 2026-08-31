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
Phase 3     Add HttpOnly-cookie auth mode to barrins_identity
Phase 4     Wire libs/goblin_guide to identity (direct + cookie)
Phase 4bis  Application directory (identity table + endpoint + SPA screen)
Phase 5     Deploy goblin_guide SPA
Phase 6     Live UAT T11-T15
Phase 7     Mount in tamiyo_scroll + tolaria_news
Phase 8     barrins_api cutover                                 <- DO LAST
```

Phases 2 → 4bis all land on staging before Phase 5; production (identity
Phase 1D + Goblin Guide Phase 5-prod) is promoted only once staging is
complete (user, 2026-08-31).

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

- `POST /api/v1/auth/token`, `/auth/refresh`, `/auth/logout` gain cookie
  behaviour when the caller opts in (header `X-Client: web`, or a
  dedicated `/auth/token?cookie=1` — decide in the ADR):
  - `token` → sets `refresh_token` cookie
    `HttpOnly; Secure; SameSite=None; Domain=<REFRESH_COOKIE_DOMAIN>;
    Path=/api/v1/auth`; response body omits `refresh_token`.
  - `refresh` → reads the cookie, rotates it, returns a new access token.
  - `logout` → clears the cookie.
- Non-cookie callers (no opt-in header) keep today's body-only behaviour.
- Config: `REFRESH_COOKIE_ENABLED` (default `false`),
  `REFRESH_COOKIE_DOMAIN`, `REFRESH_COOKIE_SAMESITE` (default `none`),
  and `ACCESS_CONTROL_ALLOW_CREDENTIALS` wired into the CORS middleware.
- Tests (`app/tests`) — cookie set / rotated / cleared, body still carries
  `refresh_token` without the opt-in, CORS credentials header present for
  an allowed origin only. Coverage ≥ the repo bar.
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

## Phase 4bis — Application directory

A role-aware cross-app launcher in Goblin Guide. **"Which apps can this
user open" is a business rule → backend** (§4.1: identity returns the
list + a computed access state per app; the SPA only renders cards).
Ships with Phase 5 so the UX lands in the same deploy (user, 2026-08-31).

### `barrins_identity`

- **New table `applications`** (Alembic migration + seed):

  | column | type | notes |
  | --- | --- | --- |
  | `id` | UUID PK | |
  | `key` | str, unique | slug — `tamiyo_scroll`, `tolaria_news`, … |
  | `name` | str | card title |
  | `description` | str | one-liner |
  | `url` | str | where the card links |
  | `logo_key` | str | maps to a SPA-bundled asset |
  | `needs_authentication` | bool, default `true` | |
  | `is_role_restricted` | bool, default `false` | implies `needs_authentication` |
  | `min_role` | `Enum(UserRole)` nullable | required iff `is_role_restricted` |
  | `sort_order` | int, default `0` | |
  | `is_active` | bool, default `true` | |
  | `created_at` / `updated_at` | tz-aware | |

  CHECK / validator: `is_role_restricted` ⇒ `min_role IS NOT NULL` and
  `needs_authentication = true`.

- **Seed** (user-approved 2026-08-31):

  | key | name | policy |
  | --- | --- | --- |
  | `goblin_guide` | Goblin Guide | `needs_authentication` |
  | `tamiyo_scroll` | Tamiyo Scroll | `needs_authentication` |
  | `tolaria_news` | Tolaria News | public |
  | `karn_jupyter` | Karn Tablets | `is_role_restricted`, `min_role = ml_developer` |
  | `docs` | Barrin's Codex (docs) | public |

- **Endpoint `GET /api/v1/applications`** — optional bearer. Returns every
  `is_active` app ordered by `sort_order`, each as
  `{ key, name, description, url, logo_key, access }` where the backend
  computes `access`:
  - `!needs_authentication` → `open`
  - `needs_authentication && !is_role_restricted` → `open` if
    authenticated, else `login_required`
  - `is_role_restricted` → `open` if authenticated and
    `user.role.level >= min_role.level`; `role_denied` if authenticated
    and below; `login_required` if anonymous
  - the endpoint does **not** filter the current app — the SPA does.
- Schema + service + tests (anon / `user` / `ml_developer` / `admin`);
  API doc per §21.1; **ADR-19** for the registry design.

### `libs/goblin_guide`

- `src/api/applications.ts` — `getApplications()` + Zod `ApplicationSchema`
  (`access` ∈ `open | login_required | role_denied`).
- `src/components/ApplicationsScreen.tsx` — prop `currentAppKey?: string`;
  fetches, drops the row whose `key === currentAppKey`, groups by access
  ("Ouvert à tous" / "Connexion requise" / "Réservé — rôle ≥ X"), renders
  cards (logo, name, description, access badge).
- `src/assets/app-logos/` — **copies** of each frontend's logo
  (`tamiyo_scroll.*`, `tolaria_news.*`, `karn_jupyter.*`, `docs.*`,
  `goblin_guide.*`); a `logo_key` → import map.
- Tests: three groups render, current app filtered, badge states.

### `apps/goblin_guide`

- Route (`/apps`, or the home) mounted in the Shell, passing
  `currentAppKey="goblin_guide"` from `config.ts`.

**Gate 4bis:** `uv run pytest` (identity) green; `npm test` + `tsc` + lint
green; anon / user / `ml_developer` / admin each render the right cards
with the right badges; `goblin_guide` absent from its own list.

---

## Phase 5 — Goblin Guide deploy playbook (SPA only)

Claude authors, operator runs.

- **New file** `ops/my-server/goblin_guide.yml` — **one playbook, one app**
  (the SPA; §26.1). No backend role, no systemd unit, **never touches
  identity or `barrins_api`**.
  - `register_ssl` for `goblin{{ env_suffix }}.barrins-codex.org`.
  - `react_frontend` for `apps/goblin_guide`; set its build env
    `VITE_IDENTITY_SERVICE_URL` to
    `https://identity{{ env_suffix }}.barrins-codex.org` (SPA routing /
    `index.html` fallback via that role's `https.conf.j2`).
- **Operator:**
  - DNS A records `goblin` + `goblin-staging` → `146.59.146.57`.
  - In `secrets/barrins_identity/{staging,production}.env`: set
    `REFRESH_COOKIE_ENABLED=true`, `REFRESH_COOKIE_DOMAIN`,
    `ACCESS_CONTROL_ALLOW_CREDENTIALS=true`, and confirm the Goblin
    origin is in `ALLOWED_ORIGINS`. Then **redeploy identity** from a ref
    carrying Phases 3 + 4bis (`ansible-playbook barrins_identity.yml` —
    its own playbook, no cross-touch).
  - Deploy the SPA: staging → prod, each release-tagged.

**Gate 5:** `https://goblin-staging.barrins-codex.org` loads; login sets
an `HttpOnly; SameSite=None` cookie on `identity-staging…` (DevTools →
Application → Cookies); cross-site refresh works; closing and reopening
the tab keeps you logged in; the app directory renders; `ansible-lint`
clean.

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
  with the in-memory store (re-login on tab close) or opt into identity
  cookie mode (Phase 3) later, once their origin is in identity's
  `ALLOWED_ORIGINS`. Note it in each app's tracker; don't block Phase 7
  on it.
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
   `target_engine.begin()` transaction. **Dedup on `email`:** when a
   `barrins_api` user's email already exists in identity, do **not**
   insert a second account — keep the identity account and only bump its
   `role` to the higher of the two (by `UserRole.level`:
   `user` < `moderator` < `ml_developer` < `admin`); all other identity
   fields stay untouched. Non-colliding users are inserted normally.
   Username collisions (same username, different email) are written to a
   collisions report and resolved by hand before the cutover.
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
