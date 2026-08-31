<!-- cSpell:ignore JWKS keypair certbot journalctl domainkey dig rua Brevo -->
# Identity Deployment — barrins_identity

Operational guide for a future `ops/my-server/barrins_identity.yml`
playbook. Structured per Constitution §37.1; §26.1 (one application, one
playbook) — this playbook must never touch `barrins_api`'s service,
vhost, or database.

> **Status**: ⬜ Playbook not built. The **application** landed on
> `proj/v2.0.0-bump` on T10 (`apps/barrins_identity/` + the shared
> `libs/identity_client/`), but there is still no
> `ops/my-server/barrins_identity.yml` and no production or staging
> instance. Concrete values below (port, domain, systemd unit) are
> **playbook-owned** and marked as such — the one exception is the email
> setup (below), which is concrete because it is being executed now.

| | Production | Staging |
| --- | --- | --- |
| Domain | `identity.barrins-codex.org` *(playbook-owned)* | `identity-staging.barrins-codex.org` *(playbook-owned)* |
| Local port (`uvicorn`, `127.0.0.1`) | a free port in the `80NN` scheme, e.g. `8021` *(playbook-owned — `barrins_api` holds `8011`)* | `85NN`, e.g. `8521` *(playbook-owned)* |
| systemd unit | `identity` *(playbook-owned)* | `identity-staging` *(playbook-owned)* |
| Source | latest GitHub release tag (ADR-2) | `develop` branch |
| `.env` (local, git-ignored) | `secrets/barrins_identity/production.env` | `secrets/barrins_identity/staging.env` |

`8001` in `apps/barrins_identity/README.md` is the local-dev
`uvicorn --reload` default only (beside `barrins_api`'s `8000` dev
default) — it is not a deployment port.

---

## Step 0 — answers before writing the playbook

Per [New Service Checklist](new-service-checklist.md). `barrins_identity`
is a persistent web API, so it fits the §37.1 backend shape — but it is a
*new* backend, not `barrins_api`, so:

1. **Trigger** — a long-running `uvicorn` process behind nginx, same as
   `fastapi_backend`. No scheduled component.
2. **HTTP surface** — yes: `/api/v1/*` and `/.well-known/jwks.json`.
   Needs its own `register_ssl` cert and nginx vhost.
3. **Validation** — `GET /health` returns `{"status": "ok"}`, plus the
   §Validation checks below.
4. **Rollback** — redeploy the previous release tag (see
   [rollback.md](rollback.md)); the DB-migration caveat applies (this
   service owns a schema).
5. **Owns data** — **yes**, its own PostgreSQL database (`users`,
   `service_accounts`, and four `auth_*` / `app_settings` tables). Never
   shared with `barrins_api`. Not covered by `barrins_api`'s backup story
   — it needs its own entry in the backup rotation.
6. **Release-tagged** — yes, like every other production backend deploy
   (§27.1).

---

## Planned consumers

Nothing consumes the production instance yet. Expected:

- `barrins_api` — verifies user + service tokens against JWKS, and calls
  `POST /service-token`; only after the cutover
  ([platform.md §10](../../back/barrins_identity/platform.md#10-cutover)).
- The **T9 Jupyter workbench** reverse-proxy gate
  (`karn-jupyter.barrins-codex.org`) — validates a user token's `role`
  claim on every request
  ([Integration Contract §8.8](../../back/barrins_identity/integration.md#88-proxy-role-gate)).
  See `docs/project/v2.0.0-bump/t9-karn-jupyter-workbench/`.

---

## Preparation

**Server bootstrap** — `initial.yml` / `setup.yml` already run on the
host (nginx, certbot, base user). One-time.

**Runtime** — Python 3.14+ and `uv`, same as `fastapi_backend`. No extra
system packages.

**Database** — a dedicated PostgreSQL database and role,
**separate from `barrins_api`'s**. Created by hand on the VPS (like the
`postgres` superuser and `karn_tablets`'s read-only role), not by the
playbook:

```sql
CREATE DATABASE barrins_identity;
CREATE ROLE barrins_identity LOGIN PASSWORD '<hex-password>';
GRANT ALL ON DATABASE barrins_identity TO barrins_identity;
-- PostgreSQL 15+: GRANT ALL ON DATABASE does NOT grant table creation on
-- schema public. Without the next two lines, `alembic upgrade head` fails
-- with "permission denied for schema public".
ALTER DATABASE barrins_identity OWNER TO barrins_identity;
\c barrins_identity
ALTER SCHEMA public OWNER TO barrins_identity;
```

Different password per environment. **Use a hex password**
(`openssl rand -hex 32`): it keeps the DSN free of percent-encoding.
`alembic/env.py` escapes `%` before handing the URL to `ConfigParser`, so
a percent-encoded password (`==` → `%3D%3D` once the DSN is stringified)
also works now — but hex sidesteps that edge case entirely.

**Signing key** — generate an RSA private key per environment and put it
in the secrets file, never in git (Constitution §34,
[ADR-1](../architecture/decisions.md#adr-1-secrets-must-never-be-committed-even-encrypted)):

```bash
openssl genrsa 2048
# paste the PEM as JWT_PRIVATE_KEY in secrets/barrins_identity/<env>.env
# (pydantic-settings accepts a multi-line value; see its docs)
```

**DNS** — an A record for the chosen subdomain → `146.59.146.57`, added
by hand in the OVH DNS zone. `register_ssl` (Let's Encrypt HTTP-01) fails
until it propagates.

**Environment variables** — from the template:

```bash
cp secrets/barrins_identity/production.env.example \
   secrets/barrins_identity/production.env
```

| Variable | Notes |
| --- | --- |
| `DATABASE_URL` | The dedicated DB above. **Never** `barrins_api`'s. Different value per environment |
| `JWT_PRIVATE_KEY` | RSA PEM, per environment. Startup fails on a non-RSA / malformed key |
| `JWT_KID` | Bump when rotating (publish the new public key under the new `kid` in JWKS *before* switching the private key) |
| `ALLOWED_ORIGINS` | JSON array, no wildcard. Goblin Guide's origin (and any other frontend calling identity directly) — the `-staging` origins on staging. CORS already runs `allow_credentials=True`, so an allowed origin gets `Access-Control-Allow-Credentials: true` for free — nothing extra for cookie mode |
| `REFRESH_COOKIE_ENABLED` / `REFRESH_COOKIE_DOMAIN` / `REFRESH_COOKIE_SAMESITE` | Cookie mode on the token-minting endpoints (ADR-18). `ENABLED=true`, `DOMAIN=identity{,-staging}.barrins-codex.org`, `SAMESITE=none` (cross-site SPA ⇒ `Secure` is set automatically) |
| `ENVIRONMENT` | `production` / `staging`. Gates the strict SMTP/`FRONTEND_BASE_URL` startup check |
| `REQUIRE_EMAIL_VERIFICATION` | **`true` in production** (ADR-3, ADR-16). See the next section |
| `SMTP_*`, `SMTP_FROM_ADDRESS`, `FRONTEND_BASE_URL` | Filled by the email setup below |

---

## Email verification — mandatory production setup (Brevo)

This executes
[ADR-3](../architecture/decisions.md#adr-3-production-email-uses-a-transactional-provider-not-self-hosted)
for `barrins_identity`. `barrins_api`'s signup email verification has run
with `REQUIRE_EMAIL_VERIFICATION=false` in production since 2026-07-16
because no relay was ever configured; `barrins_identity` does **not**
inherit that stop-gap. Production runs with
`REQUIRE_EMAIL_VERIFICATION=true`. `false` is a dev/staging-only
emergency fallback and must never be the resting production state.

Provider: **Brevo** (transactional SMTP relay, EU-hosted). Sender:
`identity@barrins-codex.org`. Do every step; verify each before the next.

1. **Brevo account + sending domain.** Create the Brevo account. Go to
   *Senders, Domains & Dedicated IPs* → *Domains* → *Add a domain* →
   `barrins-codex.org`. Brevo shows the DNS records to publish — a DKIM
   pair (`brevo1._domainkey` / `brevo2._domainkey`, usually CNAMEs), an
   SPF entry (`include:spf.brevo.com`), an optional DMARC TXT, and a
   `brevo-code…` TXT that proves domain ownership. The DKIM selectors are
   account-specific; copy them from that screen, do not guess.

2. **Publish the records in the OVH DNS zone.** OVH Manager → *Web Cloud*
   → *Domain names* → `barrins-codex.org` → *DNS zone*. For each Brevo
   record: *Add an entry*, choose the type (`CNAME` / `TXT`), paste the
   sub-domain and target **exactly** as Brevo gives them.
   - **SPF**: if a `v=spf1 …` TXT already exists at the zone apex
     (`@`), edit it to add `include:spf.brevo.com` before the final
     `~all` / `-all`. Never publish a second SPF record — multiple SPF
     records is a hard fail.
   - **DMARC**: add a TXT at `_dmarc` with
     `v=DMARC1; p=none; rua=mailto:<the OVH redirect address from step 4>`.
     Start at `p=none` (monitor only); tighten to `quarantine` later once
     reports look clean.
   - Leave TTL at the OVH default. Allow up to a few hours to propagate.

3. **Verify propagation, then verify in Brevo.**

   ```bash
   dig +short TXT barrins-codex.org
   dig +short CNAME brevo1._domainkey.barrins-codex.org
   dig +short TXT _dmarc.barrins-codex.org
   ```

   Then in Brevo → *Domains* → *Authenticate* / *Verify* until SPF, DKIM
   and the domain all show green.

4. **OVH email redirect for the sender address.** OVH Manager →
   `barrins-codex.org` → *Email* → the mail-redirect settings → create a
   redirect from `identity@barrins-codex.org` to an existing inbox you
   read. This is a redirect, not a mailbox — nothing to maintain. It
   catches bounce notifications and any human replies. Use the same
   target address for the DMARC `rua`.

5. **Generate the Brevo SMTP key.** Brevo → *SMTP & API* → *SMTP* →
   *Generate a new SMTP key*. Note the host (`smtp-relay.brevo.com`),
   port (`587`, STARTTLS), and the login shown there. The **SMTP key** is
   the value for `SMTP_PASSWORD` — not the Brevo account password.

6. **Fill the secrets file.** In
   `secrets/barrins_identity/production.env` (git-ignored):

   ```bash
   REQUIRE_EMAIL_VERIFICATION=true
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USE_TLS=true
   SMTP_USERNAME=<Brevo SMTP login>
   SMTP_PASSWORD=<Brevo SMTP key>
   SMTP_FROM_ADDRESS=identity@barrins-codex.org
   FRONTEND_BASE_URL=https://<goblin-guide host>
   ```

   A later `noreply@barrins-codex.org` (or any other
   `@barrins-codex.org` sender) needs **no new DNS** — the domain
   authentication from steps 1–3 covers every address on the domain; only
   `SMTP_FROM_ADDRESS` changes.

7. **End-to-end check on staging first.** With staging pointed at Brevo:

   ```bash
   curl -X POST https://identity-staging.barrins-codex.org/api/v1/auth/signup \
     -H "Content-Type: application/json" \
     -d '{"email":"<a real inbox>","password":"Sufficiently-Long-1!"}'
   ```

   The code must arrive (not in spam). In Gmail, *Show original* must show
   `SPF: PASS`, `DKIM: PASS`, `DMARC: PASS`. Brevo → *Logs* / *Statistics*
   shows the message *delivered*. Then:

   ```bash
   curl -X POST \
     https://identity-staging.barrins-codex.org/api/v1/auth/signup/verify \
     -H "Content-Type: application/json" \
     -d '{"email":"<the same inbox>","code":"<6 digits>"}'
   ```

   returns a `TokenPair`. Repeat for the reset flow
   (`/auth/password-reset/request` → `/confirm`).

8. **Go live.** Only after staging passes, put the same `SMTP_*` /
   `FRONTEND_BASE_URL` / `REQUIRE_EMAIL_VERIFICATION=true` in
   `production.env` and restart the unit. The
   `_production_requires_real_smtp_and_frontend_url` startup validator
   refuses to boot if `SMTP_HOST` or `FRONTEND_BASE_URL` is unset while
   verification is on — a missing value is a failed deploy, not a silent
   fallback.

9. **Failure behavior.** A send failure during `POST /auth/signup`
   returns `502` and rolls the transaction back — no orphan unverified
   account. Emergency only: `REQUIRE_EMAIL_VERIFICATION=false` restores
   signup without email; revert it the moment SMTP is healthy again.

---

## Deployment

```bash
# staging first
ansible-playbook barrins_identity.yml -e deploy_env=staging

# production, once staging is verified (deploys the latest release tag)
ansible-playbook barrins_identity.yml
```

The playbook: clones the release tag, `uv sync`, `alembic upgrade head`,
seeds the first admin (`scripts/create_admin.py --email … --username …`,
one-time),
restarts the systemd unit. It touches nothing belonging to `barrins_api`.

---

## Validation

- `curl -fsS https://identity.barrins-codex.org/health` → `{"status": "ok"}`.
- `curl -fsS https://identity.barrins-codex.org/.well-known/jwks.json` → a
  single-key JWKS document with the expected `kid`.
- `POST /api/v1/auth/token` with the seeded admin → a token pair;
  `POST /api/v1/auth/refresh` → a new pair; `POST /api/v1/auth/logout`
  then reusing the old token → `401`.
- The §"Email verification" step-7 end-to-end check, against production
  this time (one real signup + verify).
- `journalctl -u identity -n 50` — no tracebacks; the startup log shows
  the environment and "Application started successfully".

---

## Rollback

Redeploy the previous release tag:

```bash
ansible-playbook barrins_identity.yml \
  -e barrins_identity_release_tag=<previous-tag>
```

Code and schema are separate — before rolling back across an Alembic
migration, follow the backend rules in
[rollback.md](rollback.md#backend-rollback-code-and-database-are-separate).
Take a `pg_dump` of the identity database first.

---

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Service won't start, log mentions the RSA key | `JWT_PRIVATE_KEY` missing, not PEM, or not an RSA key |
| Service won't start, log mentions SMTP / frontend URL | `REQUIRE_EMAIL_VERIFICATION=true` in production with `SMTP_HOST` or `FRONTEND_BASE_URL` unset — the startup guard |
| Every browser API call fails CORS | `ALLOWED_ORIGINS` missing the frontend origin, or a wildcard was used |
| Verification emails land in spam | SPF/DKIM not green in Brevo, or two SPF records at the zone apex, or DMARC misconfigured |
| No email arrives at all | `SMTP_PASSWORD` is the Brevo account password, not the SMTP key; or outbound `587` is blocked from the VPS |
| `register_ssl` fails on `certbot certonly` | DNS A record not propagated to `146.59.146.57`, or port 80 unreachable |

---

## See also

- [Platform Architecture](../../back/barrins_identity/platform.md),
  [Integration Contract](../../back/barrins_identity/integration.md),
  [Test Plan](../../back/barrins_identity/tests.md).
- [Backend Deployment — barrins_api](backend.md) — the §37.1 shape this
  follows.
- [New Service Checklist](new-service-checklist.md),
  [Rollback](rollback.md).
- [Signup & Email Verification](../../back/barrins_api/signup_email_verification.md)
  — the email flow's original design.
- [ADR-3](../architecture/decisions.md#adr-3-production-email-uses-a-transactional-provider-not-self-hosted),
  [ADR-16](../architecture/decisions.md#adr-16-adopt-barrins-identity-as-the-rs256-jwks-authority).
