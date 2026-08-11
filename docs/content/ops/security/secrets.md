# Secrets Management

How `ops/my-server/` satisfies Constitution §34 ("Secrets must never be
stored inside repositories") — see ADR-1 in
[`../architecture/decisions.md`](../architecture/decisions.md) for how
this was decided, and `ops/my-server/secrets/README.md` for the day-to-day
operator workflow (creating/editing local `.env` files).

## What's never in git

- `ops/my-server/secrets/**` — real configuration values, whether a
  backend's full `.env` (`barrins_api`) or a single value (`postgresql_pgadmin`'s
  admin password). Git-ignored by an allow-list rule (everything under
  `secrets/` is ignored except `*.example` templates and `README.md`), so
  a new secret file is safe by default regardless of what it's named.
- `ops/my-server/.vault-password-file.txt` — the optional local
  `ansible-vault` password, if an operator chooses to encrypt their
  `.env` files at rest. Git-ignored, never shared via any channel this
  document endorses other than a password manager.
- The `github_token` var in each playbook is `ansible-vault`-encrypted
  **in the playbook itself** (an exception with a different risk profile
  than a `.env` file — see "Why `github_token` is different" below).

## Enforcement

`ops/my-server/scripts/check_no_secrets_committed.sh` fails if any file
under `secrets/` other than `*.example`/`README.md` is ever staged. Run it
before committing, or symlink it as a pre-commit hook:

```bash
ln -s ../../scripts/check_no_secrets_committed.sh .git/hooks/pre-commit
```

**Open item**: this hook is not currently enforced automatically for
every contributor — it's opt-in per developer machine. There is no
repository-side (CI/server) secret-scanning gate in this project today.
If that changes (e.g. a GitHub secret-scanning or pre-receive check is
added), this page should be updated to reflect it.

## Why `github_token` is different

`github_token` is a single, narrow-scope (`repo` read-only) credential
needed to clone private repositories, embedded — vault-encrypted — inside
each playbook. This is a smaller-blast-radius exception to the
never-in-git rule than a full `.env`:

- It's one credential, not an app's entire secret configuration.
- It's scoped to read-only repository access, not database/SMTP/session
  credentials.
- It rotates on a known cadence (documented in `ops/my-server/README.md`'s
  "GitHub Token" section) independent of any application release.

This is a deliberate, narrower exception — not a precedent for reverting
ADR-1 for `.env` files generally. If this token's exposure becomes a
concern, moving it to the same local-file pattern as `.env` (a
`github_token` file per operator, referenced via `lookup('file', ...)`
instead of embedded `!vault` in the playbook) is the natural next step.

## Service-to-service credentials: `SCRIPTURE_INGEST_TOKEN`

Barrin's Scripture's sweep authenticates to `barrins_api` with an
`X-Scripture-Token` header on `POST /internal/scripture/ingest`. The
shared secret behind that header is `SCRIPTURE_INGEST_TOKEN`, and it
follows a third pattern in `ops/my-server/` — distinct from both a
per-app `.env` and `github_token`'s vault-in-playbook exception.

**One role, consumed by two playbooks.** The `scripture_ingest_token`
role (`ops/my-server/roles/scripture_ingest_token/`) reads the raw value
from a local, git-ignored file and exposes it as a fact. Both
`barrins_api.yml` and `barrins_scripture.yml` run this role, then inject
the resulting fact into their own already-deployed `.env` via a
`post_tasks` `ansible.builtin.lineinfile` step (`no_log: true`) —
**after** `fastapi_backend`/`scripture_scraper` have templated the rest
of the file, not as part of that templating. `SCRIPTURE_INGEST_TOKEN` is
deliberately absent from `secrets/barrins_api/*.env` and
`secrets/barrins_scripture/*.env` themselves.

**Per-environment, unlike `github_token`.** `github_token` is one value
shared across every environment because it only grants read-only repo
access. `SCRIPTURE_INGEST_TOKEN` authenticates production traffic
against production data (same reasoning as `SECRET_KEY`), so staging and
production must never share a value:

```text
secrets/scripture/
  staging_ingest_token.txt.example     # plaintext template, committed
  staging_ingest_token.txt             # real value, git-ignored, local-only
  production_ingest_token.txt.example
  production_ingest_token.txt
```

The role resolves which file to read from `deploy_env` (already defined
by both consuming playbooks), so pointing `barrins_scripture.yml` at
staging vs. production automatically picks the matching token — no
separate flag to keep in sync with `deploy_env`.

**Creating a local copy**, same generation pattern as any other
high-entropy secret in this project:

```bash
openssl rand -hex 32 | tr -d '\n' > secrets/scripture/staging_ingest_token.txt
openssl rand -hex 32 | tr -d '\n' > secrets/scripture/production_ingest_token.txt
ansible-vault encrypt secrets/scripture/staging_ingest_token.txt \
  secrets/scripture/production_ingest_token.txt  # optional
```

**Why centralized instead of duplicated.** The original 2026-08-08
decision (T8) was to hand-copy the same value into both
`secrets/barrins_api/*.env` and `secrets/barrins_scripture/*.env`, with
no automated sync between the two copies. That was superseded the same
day, before it shipped to any real environment: a mismatched copy would
fail silently (every ingest call rejected with no obvious cause), so the
`scripture_ingest_token` role removes the duplication at the source
instead of documenting a manual-sync requirement. See
`ops/my-server/roles/scripture_ingest_token/README.md` and
`ops/my-server/secrets/README.md` for the operator-facing detail; see
`docs/project/v2.0.0-bump/t8-scripture-karn-playbooks/index.md` for the
full decision history.

## CORS and network boundaries

Constitution §33 requires CORS to be restrictive and explicitly
configured — never `Access-Control-Allow-Origin: *` for an authenticated
production API. `barrins_api`'s `ALLOWED_ORIGINS` (set via the local
`.env`, see [`../deployment/backend.md`](../deployment/backend.md)) is the
enforcement point; it must list every frontend origin that legitimately
calls the backend, and nothing else.

## See also

- [`../architecture/decisions.md`](../architecture/decisions.md) — ADR-1,
  the full context/alternatives/trade-offs for this policy.
- `ops/my-server/secrets/README.md` — operator workflow.
- [`../deployment/backend.md`](../deployment/backend.md) — the specific
  `.env` keys `barrins_api` needs and their security implications
  (`SECRET_KEY`, `SMTP_PASSWORD`, ...).
