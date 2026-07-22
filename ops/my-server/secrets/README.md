# secrets/

Per-app, per-environment `.env` files, **local-only and git-ignored** —
Constitution §34 ("Secrets Management") is explicit that secrets must
never be stored inside a repository, so nothing under `secrets/` except
the `*.env.example` templates is ever committed (enforced by `.gitignore`
and `scripts/check_no_secrets_committed.sh`). `fastapi-backend`'s
`fb_env_file` (see `roles/fastapi-backend/README.md`) copies whichever of
these files exists on your machine straight to `<app_root>/.env` during
deploy, and skips the step with a note if it doesn't — "use it if
available," never a hard requirement. Nobody needs to SSH in and hand-edit
a `.env` file on the server, but each operator is responsible for having
their own local copy.

## Layout

```
secrets/
  <app>/
    production.env.example   # plaintext template, committed
    production.env           # real values, git-ignored, local-only
    staging.env.example
    staging.env
```

`*.env.example` files are plain templates (no real secrets) copied from
the app's own `.env.example` in the `barrins-project` repo — kept here so
the required keys are visible without checking out a second repo. `*.env`
(without `.example`) holds the real values and must **never** be
committed, encrypted or not.

## Creating a local `.env`

```bash
cp secrets/barrins_api/production.env.example secrets/barrins_api/production.env
# fill in secrets/barrins_api/production.env with real values
```

Optionally encrypt it at rest with `ansible-vault` for extra protection on
your own disk (`fb_env_file`/the `copy` module transparently decrypt a
vault-encrypted source given `.vault-password-file.txt`, so this is
compatible either way):

```bash
ansible-vault encrypt secrets/barrins_api/production.env
# ansible-vault edit / ansible-vault view to work with it afterward
```

This is optional, not required — the file is git-ignored either way, so
vaulting only protects it if your disk itself is compromised. Whichever
you choose, share the real values with other operators out of band (a
password manager, not git — see "Safety" below), each keeping their own
local copy at the same path.

## Safety

- **Never commit a `secrets/**/*.env` file** (`.example` files are fine).
  Run `./scripts/check_no_secrets_committed.sh` before committing to
  verify none are staged. Wire it up as a pre-commit hook with
  `ln -s ../../scripts/check_no_secrets_committed.sh .git/hooks/pre-commit`.
- If you do encrypt a file with `ansible-vault`, back up
  `.vault-password-file.txt` somewhere safe outside this repo (a password
  manager, not another git repo) — it's git-ignored and never leaves your
  machine.
- Rotating a leaked value (e.g. `SECRET_KEY`, a DB password) means editing
  the local `.env` (and every other operator's copy) *and* changing the
  value at its source (Postgres role password, SMTP account, ...).
- Because these files are never in git, a fresh checkout (new operator, new
  machine, CI) has none of them — deploys will skip the `.env` step until
  someone creates the files locally. That's intentional (§34), not a bug.

## Which keys does each app need?

Start from the app's own `.env.example`
(`../../apps/<app>/.env.example`) — that's the source of truth for what
the app reads. The `*.env.example` files here are a copy for convenience
and can drift; re-sync them by hand if the app adds/removes a setting.

For `barrins_api` specifically, see
[`../../docs/content/ops/deployment/backend.md`](../../docs/content/ops/deployment/backend.md)
for the full table of keys with deployment-specific notes (which ones
differ between production/staging, which are required only when
`REQUIRE_EMAIL_VERIFICATION=true`, etc.).
