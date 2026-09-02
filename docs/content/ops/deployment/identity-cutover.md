<!-- cSpell:ignore pg_dump barrins Alembic JWKS asyncpg psycopg pgpass -->
# Identity Cutover — `barrins_api` → `barrins_identity` JWKS

Operator runbook for the one live, gated step of rollout Phase 7+8
([ADR-20](../architecture/decisions.md#adr-20-barrins_api-trusts-barrins_identity-jwks-drops-its-users-table)):
copy `barrins_api`'s `users` rows into `barrins_identity`'s database, then
deploy the `barrins_api` release that verifies identity JWTs and has no
local `users` table.

Everything **Claude** could do is done and CI-tested on
`feat/goblin-guide-login` (the migration script, the JWKS cutover, the
Alembic drop migration, `POST /users/lookup`, the frontend swap, the
playbook edits). This page is only the parts that touch **live data** and
therefore need a human and a maintenance window (Constitution §31.3).

Structured per Constitution §37.1.

---

## What changes

| Before | After |
| --- | --- |
| `barrins_api` mints + verifies its own HS256 JWTs against a local `users` table | `barrins_api` verifies `barrins_identity` RS256 tokens against its JWKS (`libs/identity_client`) |
| `users`, `auth_email_verifications`, `userrole` enum, 12 `users.id` FKs | all dropped (Alembic `d9e1a2c3b4f5`) |
| `owner_id` / `user_id` columns are FKs into `users` | FK-less opaque references to `barrins_identity` user ids (**same UUIDs** — the migration preserves them) |
| Admin "total accounts" metric | removed (no data source) — decks / matches / sessions metrics unchanged |
| `SECRET_KEY` in `barrins_api`'s env | `IDENTITY_SERVICE_URL` + `IDENTITY_SERVICE_CLIENT_ID` / `_SECRET` |

---

## Preparation

1. **Identity is live and healthy** for the target environment
   (`curl -fsS https://identity{,-staging}.barrins-codex.org/health`,
   `/.well-known/jwks.json` returns one key). See [`identity.md`](identity.md).

2. **A `barrins_identity` service account for `barrins_api`** — scope
   **`identity:users:read`** only (used solely for `POST /users/lookup`
   team-roster / sharing labels). Create it on the VPS:

   ```bash
   ssh spigushe@146.59.146.57
   cd ~/projects/identity{,-staging}.barrins-codex.org/apps/barrins_identity
   uv run python - <<'PY'
   # or use POST /api/v1/service-accounts as an admin — see
   # back/barrins_identity/service-accounts.md
   PY
   ```

   Record the `client_id` and the once-shown `client_secret`.

3. **`barrins_api` env** — in
   `ops/my-server/secrets/barrins_api/<deploy_env>.env` (templates
   already carry the keys):

   - remove `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
     `REFRESH_TOKEN_EXPIRE_DAYS`, `ALGORITHM`
   - `IDENTITY_SERVICE_URL=https://identity{,-staging}.barrins-codex.org`
   - `IDENTITY_SERVICE_CLIENT_ID=<from step 2>`
   - `IDENTITY_SERVICE_CLIENT_SECRET=<from step 2>`

4. **Identity `ALLOWED_ORIGINS`** — add the Tamiyo origins
   (`https://tamiyo{,-staging}.barrins-codex.org`) if not already present,
   then **redeploy identity** (`ansible-playbook barrins_identity.yml …` —
   its own playbook, no cross-touch). This is what makes cookie-mode auth
   work for the Tamiyo SPA.

5. **Release tag** — production deploys only from a release tag
   (§27.1). Cut one on `proj/v2.0.0-bump` after `feat/goblin-guide-login`
   is merged. Staging can deploy the branch directly
   (`-e fastapi_backend_git_branch=feat/goblin-guide-login`).

**Gate:** identity healthy; service account created; env swapped;
identity redeployed with the Tamiyo origins; (prod) release tag cut.

---

## Deployment

Run from `ops/my-server/`. **Announce a maintenance window** — between the
`pg_dump` and the `barrins_api` restart, logins are briefly inconsistent.

1. **Back up both databases.**

   ```bash
   ssh spigushe@146.59.146.57
   pg_dump -Fc barrins_api_<env>       -f ~/backups/barrins_api_<env>_pre-cutover.dump
   pg_dump -Fc barrins_identity_<env>  -f ~/backups/barrins_identity_<env>_pre-cutover.dump
   ```

2. **Dry-run the user migration.** From a machine with `uv` and the repo
   checked out at the cutover ref (or on the VPS in the `barrins_api`
   project dir):

   ```bash
   cd apps/barrins_api
   # DB host omitted for width — it is 146.59.146.57:5432.
   uv run python scripts/migrate_users_to_identity.py \
     --source-url "postgresql://USER:PW@$HOST/barrins_api_<env>" \
     --target-url "postgresql://USER:PW@$HOST/barrins_identity_<env>" \
     --report ~/users-migration-report.txt \
     --dry-run
   ```

   Read `~/users-migration-report.txt`:

   - **synthesised usernames** — `barrins_api` had no `username`; each is
     derived from the email local part. Sanity-check they look reasonable.
   - **`-N` suffixed usernames** — a synthesised handle collided; the
     script disambiguated. If a real person should own the un-suffixed
     handle, fix it by hand in `barrins_identity` *after* the run.
   - **emails already in identity** — those `barrins_api` accounts are
     **not** re-inserted; identity's row is kept and its `role` raised to
     the higher of the two. Confirm that is what you want for each.

3. **Run the migration for real** (drop `--dry-run`). It is one
   transaction on the target — a failure rolls `barrins_identity` back
   completely and exits non-zero. Re-running after a fix is safe: already
   migrated emails are treated as the dedup case.

4. **Deploy `barrins_api`.** This applies Alembic `d9e1a2c3b4f5`
   (drops the FKs, `users`, `auth_email_verifications`, `userrole`) and
   restarts the service.

   ```bash
   # staging
   ansible-playbook barrins_api.yml -e deploy_env=staging \
     -e fastapi_backend_git_branch=feat/goblin-guide-login
   # production (from the release tag)
   ansible-playbook barrins_api.yml
   ```

5. **Deploy `tamiyo_scroll`** (its own playbook — it only *reads*
   `VITE_IDENTITY_SERVICE_URL` at build time, never touches `barrins_api`
   or identity):

   ```bash
   ansible-playbook tamiyo_scroll.yml -e deploy_env=staging \
     -e react_frontend_git_branch=feat/goblin-guide-login
   ```

---

## Validation

- `curl -fsS https://api{,-staging}.barrins-codex.org/health` → `{"status":"ok"}`
- `journalctl -u barrins-api{,-staging} -n 80` — no tracebacks; a startup
  line logs the configured `IDENTITY_SERVICE_URL`.
- On `https://tamiyo{,-staging}.barrins-codex.org`:
  1. Log in through the Goblin Guide `<LoginScreen>` against identity.
  2. Reload / reopen the tab → still logged in (cookie mode).
  3. Data calls succeed (personal decks, matches, meta decks load) —
     `barrins_api` is verifying the identity JWT.
  4. `AdminMetricsPage` loads with **no** accounts tile; decks / matches
     metrics intact.
  5. Team rosters show usernames (no email column); the "shared with you"
     banner shows a display name or a generic label.
  6. Signup + email verify, password reset, account settings
     (display-name, email-change, delete) all work.
  7. `/demo` still works with no session; logout returns to the login
     screen.
- `alembic current` on the `barrins_api` DB → `d9e1a2c3b4f5 (head)`;
  `\dt` shows no `users` / `auth_email_verifications`, `\dT` no `userrole`.

---

## Rollback

1. Redeploy the **previous** `barrins_api` release tag
   (`ansible-playbook barrins_api.yml -e fastapi_backend_release_tag=<prev>`).
   Its Alembic downgrade recreates `users` / `auth_email_verifications` /
   `userrole` + the FK constraints (structure only, no data).
2. Restore both dumps:

   ```bash
   pg_restore --clean --if-exists -d barrins_api_<env>      ~/backups/barrins_api_<env>_pre-cutover.dump
   pg_restore --clean --if-exists -d barrins_identity_<env> ~/backups/barrins_identity_<env>_pre-cutover.dump
   ```

3. Redeploy the previous `tamiyo_scroll` release tag.
4. Identity's `ALLOWED_ORIGINS` change is harmless to leave in place.

A restore is only needed if the migration or the new release
misbehaved — the migration itself never mutates the **source**
(`barrins_api`) database.

---

## See also

- [ADR-20](../architecture/decisions.md#adr-20-barrins_api-trusts-barrins_identity-jwks-drops-its-users-table)
- [`back/barrins_identity/platform.md` §10](../../back/barrins_identity/platform.md)
- [`back/barrins_identity/integration.md` §4.9](../../back/barrins_identity/integration.md)
- [`rollback.md`](rollback.md)
- [`identity.md`](identity.md), [`goblin-guide.md`](goblin-guide.md)
