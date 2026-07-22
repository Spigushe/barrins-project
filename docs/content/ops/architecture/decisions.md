# Infrastructure Decision Records

Technical decisions for `ops/my-server/`, recorded in the format
Constitution §16.3 requires: Context, Alternatives, Trade-offs, Decision,
Consequences. Both decisions below were escalated to the user rather than
chosen silently, per §16.2 ("Never guess requirements... changing
deployment architecture" is explicitly listed as requiring validation).

## ADR-1: Secrets must never be committed, even encrypted

**Context.** `ops/my-server/` deploys a backend `.env` file
(`DATABASE_URL`, `SECRET_KEY`, SMTP credentials, ...) to the server on
every run. That file has to come from somewhere the playbook can read it.
An earlier iteration of this setup committed the file to git, encrypted
with `ansible-vault`, on the reasoning that ciphertext-at-rest is a
widely-accepted practice and the vault password (the actual secret) never
left the operator's machine.

**Alternatives considered.**

1. Commit the `.env`, `ansible-vault`-encrypted, to the repository.
2. Never commit the `.env` at all — local-only, git-ignored file per
   operator, per environment.
3. Store secrets in a dedicated external secrets manager (e.g. HashiCorp
   Vault, a cloud provider's secret store) and have the playbook fetch
   them at deploy time.

**Trade-offs.**

- Option 1 is convenient (one `git clone` gets everything, secrets travel
  with the repo, easy to review "what changed") but is, under a strict
  reading of Constitution §34 ("Secrets must never be stored... inside
  repositories"), still storing the secret inside the repository — the
  encryption changes the risk profile (a leaked repo doesn't immediately
  leak secrets) but doesn't change the fact of storage. It also means the
  secret's exposure window is git's entire history: rotating a value
  doesn't remove the old one from history, and the vault password becomes
  a single point of failure whose compromise retroactively exposes every
  vaulted secret ever committed.
- Option 3 is the most robust against exactly this failure mode
  (secrets never touch any repository, ever, and rotation/revocation is
  centralized) but is real infrastructure this project doesn't have and a
  single-VPS, single-operator setup doesn't currently justify standing up.
- Option 2 has no git-history exposure at all (nothing to leak from a repo
  breach) and is a small operational cost: each operator maintains their
  own local copy, and a fresh checkout deploys with no `.env` until
  someone creates one (the playbook detects this and skips the step with
  a clear message rather than failing the whole run — see
  `roles/fastapi-backend/README.md`'s "if available" behavior).

**Decision.** Option 2. `secrets/**/*.env` is git-ignored
(`ops/my-server/.gitignore`); only `*.env.example` templates are tracked.
`scripts/check_no_secrets_committed.sh` guards against ever staging one by
mistake. `ansible-vault` remains available (optional, not required) for
operators who want at-rest encryption on their own disk, but that's a
local choice, orthogonal to whether the file is ever committed — it never
is.

**Consequences.**

- No secret has ever been committed to this repository, and none can be
  without the guard script catching it first (assuming it's run — it's
  not currently wired as an enforced hook, see the open item in
  [`../security/secrets.md`](../security/secrets.md)).
- A fresh checkout, a new operator, or a CI runner has zero backend
  secrets by default. Deploys from such a machine silently skip the
  `.env` step (server keeps whatever `.env` it already had) rather than
  fail — intentional (§34 spirit: don't punish "no secret available",
  since that's the safe default), but means "the deploy succeeded" is not
  proof "the `.env` is current."
- Operators must share real values with each other out of band (a
  password manager, not git, not chat) and keep their local copies in
  sync by hand. This does not scale past a small team; if the team grows,
  revisit option 3.

## ADR-2: Production deploys only from GitHub release tags

**Context.** Constitution §§25, 27.1 and 31.1 require production
deployments to originate from released versions, never from untagged
commits or development branches. The Ansible roles that clone application
repositories (`fastapi-backend`, `react-frontend`) originally always
deployed a branch (`main` in production, `develop` in staging) via `git`
module's `version:` parameter.

**Alternatives considered.**

1. Keep deploying `main`/`develop` branches directly (status quo, not
   compliant with §§25/27/31).
2. Require a human to always pass an explicit release tag
   (`-e fb_release_tag=vX.Y.Z`) on every production deploy.
3. Auto-resolve the latest GitHub release tag by default, still allow
   pinning an explicit tag for rollback or a deliberate re-deploy of an
   older version.

**Trade-offs.**

- Option 1 is simplest but doesn't satisfy the Constitution and removes
  the safety property the release policy exists for: a bad commit merged
  to `main` would deploy to production on the very next run, with no
  human decision point.
- Option 2 maximizes intentionality (every production deploy names an
  exact version) but adds friction to the common case ("deploy whatever
  was just released") and is easy to get wrong under time pressure (typo
  a tag, or forget to update it and silently redeploy an old one).
- Option 3 keeps the common case ("ship the latest release") as simple as
  running the playbook with no extra flags, while still making rollback
  and deliberate version-pinning a first-class, explicit action rather
  than an afterthought. Staging is deliberately excluded from this
  requirement — it exists specifically to preview code before it's
  released, so it keeps deploying a branch.

**Decision.** Option 3. `fb_use_release_tag`/`rf_use_release_tag` default
to `false`; every playbook here sets them to `deploy_env == 'production'`.
When `true`, the role resolves `fb_release_tag`/`rf_release_tag` if set,
else calls `GET /repos/{repo}/releases/latest` on the GitHub API and
deploys that tag. If the repo has no release yet, the role fails with a
message telling the operator to cut one — it never silently falls back to
a branch in production.

**Consequences.**

- `barrins_api`, `tamiyo_scroll`, and `tolaria_news` must each have at
  least one GitHub Release before their first production deploy under
  this scheme. None of these repos currently has an automated release/tag
  cutting process — that's a real gap this decision creates, tracked as
  an open item (someone still has to manually create a GitHub Release,
  today via the GitHub UI/API, before every production deploy).
- Rollback becomes a one-line command
  (`-e fb_release_tag=<previous tag>`) instead of a manual git checkout on
  the server — see [`../deployment/rollback.md`](../deployment/rollback.md).
- The GitHub API call needs network egress from the control machine and a
  token with read access to Releases (the same `repo`-scoped PAT already
  used for cloning covers this).
- Database migrations are still never automated (a separate, pre-existing
  gap — see Constitution §31.3 and `ops/my-server/README.md`'s "Multiple
  frontends sharing one backend" section) — rolling back the *code* to an
  older release tag does not roll back the *database*. This is spelled
  out explicitly in the rollback runbook so it's never assumed away.
