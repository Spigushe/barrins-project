# Secrets Management

How `ops/my-server/` satisfies Constitution §34 ("Secrets must never be
stored inside repositories") — see ADR-1 in
[`../architecture/decisions.md`](../architecture/decisions.md) for how
this was decided, and `ops/my-server/secrets/README.md` for the day-to-day
operator workflow (creating/editing local `.env` files).

## What's never in git

- `ops/my-server/secrets/**/*.env` — real backend configuration values.
  Git-ignored. Only `*.env.example` templates (no real values) are
  tracked.
- `ops/my-server/.vault-password-file.txt` — the optional local
  `ansible-vault` password, if an operator chooses to encrypt their
  `.env` files at rest. Git-ignored, never shared via any channel this
  document endorses other than a password manager.
- The `github_token` var in each playbook is `ansible-vault`-encrypted
  **in the playbook itself** (an exception with a different risk profile
  than a `.env` file — see "Why `github_token` is different" below).

## Enforcement

`ops/my-server/scripts/check_no_secrets_committed.sh` fails if any
`secrets/**/*.env` (other than `.env.example`) is ever staged. Run it
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
