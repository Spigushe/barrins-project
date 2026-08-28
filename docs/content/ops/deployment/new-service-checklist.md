# New Service Checklist — Beyond `fastapi_backend`/`react_frontend`

Constitution §37 documents two playbook shapes: a backend (§37.1, a
persistent web API with an HTTP health check) and a frontend (§37.2, a
static SPA build). Every service in production today fits one of those
two — but not every future one will. This page generalizes §26.1 ("one
application, one playbook") and §37's Preparation/Deployment/Validation/
Rollback structure for a service that is **neither**: a scheduled job, a
background worker, or a small inference/results-serving service.

It is a template/checklist, not a finished playbook — per request item 4
(`docs/project/v2.0.0-bump/d1-playbook-template/`), the concrete shapes
needed this release (Barrin's Scripture, Karn Tablets) get their own
playbooks under their own work items (T8), written by following this
page, not by this page itself.

## Step 0 — answer these before writing a single task

A `fastapi_backend`/`react_frontend` playbook can skip these because the
answer is always the same (long-running process behind nginx; static
build served by nginx). A new shape can't assume that — write down the
answer for *this* service before drafting Preparation/Deployment/
Validation/Rollback below.

1. **What triggers a run?** A `systemd` timer on the VPS (the
   `postgres_backup`/`scripture_scraper` pattern — see "Precedents"
   below), a GitHub Actions schedule (the pattern `mtg_scraper` used
   before its VPS migration), or an on-demand/admin-triggered HTTP
   route (e.g. S8's `POST /mtgjson/import`)? A service can combine a
   scheduled trigger with an on-demand one — decide both, not just one.
2. **Does it have an HTTP surface at all?** If not (a pure scheduled
   job), skip `register_ssl`/DNS/nginx entirely — there is nothing to
   put a certificate on. `scripture_scraper` is the existing proof this
   is a legitimate shape, not a workaround.
3. **What does "Validation" mean without a `GET /health`?** Pick a real
   signal up front: a systemd unit's last exit code
   (`systemctl status <unit>`), a "last successful run" timestamp
   somewhere inspectable, or — if the service does expose a narrow
   read/status route — that route. Don't leave this as "check the logs
   and hope," which is what happens if it isn't decided before
   deployment day.
4. **What does "Rollback" mean for this artifact?** Code rollback
   (redeploy an older commit/tag — see [`rollback.md`](rollback.md)) is
   usually still the right first answer, but a service that produces its
   own non-code artifact (a trained model checkpoint, a computed
   clustering result) needs a second, explicit answer: is the artifact
   itself versioned/retained across redeploys, or just regenerated on
   the next scheduled run? Don't guess this per Constitution §16.2 —
   decide it per service, in that service's own playbook item.
5. **Does it own data, and if so, whose backup/restore story covers
   it?** Per §1.2's precedent (Barrin's Scripture never gets its own
   `DATABASE_URL`; it calls a `barrins_api`-owned ingestion route
   instead), most new services should **not** need their own database —
   if one seems to, that's an architecture decision to escalate (§16.2),
   not something this checklist should paper over. A pure JSON-archive
   or checkpoint-file artifact isn't covered by [`database.md`](database.md)'s
   Postgres backup story at all — say explicitly whether it needs its
   own retention/rotation (`postgres_backup_retention_days`'s pattern,
   applied to files instead of `pg_dump` output) or is disposable/
   replayable from elsewhere (Barrin's Scripture's JSON archive, per
   §1.3, is disposable in this sense — the database can be rebuilt from
   it, not the other way around).
6. **Is this release-tagged, like production backend/frontend deploys
   (§27.1), or does "release" not mean anything for it?** A scheduled
   job with no user-facing version can reasonably deploy from a branch
   even in production (see `scripture_scraper`'s current
   `deploy_branch`-driven default, staged that way deliberately until
   proven equivalent to what it replaces) — but say so explicitly rather
   than silently diverging from every other production playbook's
   release-tag convention.

## Preparation / Deployment / Validation / Rollback

The same four headings `backend.md`/`frontend.md` use, generalized:

### Preparation

- Server bootstrap (`initial.yml`/`setup.yml`) already done — same as
  every other playbook, not shape-specific.
- Runtime/dependencies: whatever the service needs (a `uv`-managed
  Python venv, same as `fastapi_backend`, is the default unless there's
  a reason otherwise).
- Credentials: the shared `github_token` role for a private clone (same
  pattern every app-deploying role uses), plus any new
  service-to-service credential this service needs to call another app
  (document it in `security/secrets.md` per D3, not here).
- DNS/TLS: **only if Step 0.2 said this service has an HTTP surface.**
  Otherwise this section is N/A — say so explicitly in the playbook's
  own doc rather than leaving a blank heading.

### Deployment

- Retrieve code: same `git`-clone-over-HTTPS-with-`github_token`
  mechanism as `fastapi_backend`/`react_frontend`, from this monorepo
  (`*_repo_subdir`) unless the service lives in its own repo.
- Install dependencies.
- Wire the trigger decided in Step 0.1: a templated systemd
  `.service`/`.timer` pair (`postgres_backup`/`scripture_scraper`'s
  pattern — a oneshot service plus a timer with `RandomizedDelaySec`
  and `Persistent=true` so a missed run catches up on next boot), or a
  mounted admin route if the trigger is on-demand.
- Migrations: only relevant if Step 0.5 concluded this service owns its
  own schema (should be rare — see that step).

### Validation

- The Step 0.3 signal, concretely: e.g.
  `systemctl status <unit>`/`journalctl -u <unit> -n 50` for a
  timer-driven job, or a specific route's response for an on-demand one.
- Idempotency: confirm re-running (a redeploy, or the job's own next
  scheduled run) doesn't duplicate output — the same discipline
  `ansible-lint`'s `changed_when` rule already requires at the task
  level (Constitution §26.4), applied here at the whole-run level.

### Rollback

- Code: same as backend/frontend — redeploy an older commit/tag (see
  [`rollback.md`](rollback.md)) if this service is release-tagged (Step
  0.6), otherwise redeploy a specific known-good branch state.
- Data/artifact: the Step 0.4 answer. If the service is a pure
  consumer/producer of a replayable archive (Barrin's Scripture's JSON
  archive), rolling back code doesn't need to roll back already-written
  output — the archive stays valid regardless of which code version
  wrote it. If it writes into `barrins_api`'s own tables via an
  ingestion route, that data's rollback story belongs to
  `barrins_api`/[`rollback.md`](rollback.md), not to this service's own
  playbook.

## Ansible coding standards still apply

A role written from this template is still `ops/my-server/` code — every
rule in Constitution §26.4 (role naming, FQCN, `<role>_`-prefixed vars,
quoted `mode:` strings, `changed_when` on every `command`/`shell` task,
named plays/tasks) applies exactly as it does to `fastapi_backend`/
`react_frontend`. `ansible-lint ops/my-server` has no relaxed profile for
a new shape.

## Precedents to build from

- [`backend.md`](backend.md)/[`frontend.md`](frontend.md) — the
  Preparation/Deployment/Validation/Rollback structure this page
  generalizes, and the release-tag/staging-branch convention (Step 0.6).
- `ops/my-server/roles/postgres_backup/` +
  [`database.md`](database.md) — the systemd `.service`/`.timer`
  pattern for a scheduled run, host-level infrastructure (no
  release tag, no staging/production split).
- `ops/my-server/roles/scripture_scraper/` +
  `ops/my-server/barrins_scripture.yml` — the closest existing
  precedent for an **application**-level scheduled job (not host
  infrastructure like `postgres_backup`): git-cloned from this monorepo
  like `fastapi_backend`/`react_frontend`, but no
  domain/SSL/reverse-proxy role, a systemd timer instead of a
  long-running `uvicorn` process. Built during T1, ahead of this
  template being written — read its
  `ops/my-server/roles/scripture_scraper/README.md` as a worked example
  of Step 0's questions already answered one way,
  including two items it explicitly leaves open ("Not automated yet"):
  the JSON archive isn't a git submodule yet, and there's no
  failure-notification wiring (Validation today is manual
  `systemctl status`/`journalctl`) — both real gaps a future consumer of
  this template should decide deliberately rather than silently repeat.
- `ops/my-server/roles/karn_tablets/` +
  `ops/my-server/karn_tablets.yml` (T8) — a second application-level
  scheduled job built directly against this checklist, narrower than
  `scripture_scraper`: no external scraping, no Chromium, no archive, no
  sweep. Reads `bs_*`/`mj_*` over a read-only DB credential and pushes to
  `barrins_api`'s `POST /internal/karn/ingest`. Its README carries the
  Step-0 answers; the read-only DB role
  (`KARN_TABLETS_DATABASE_URL_RO`) is the one item it leaves to a manual
  step (`CREATE ROLE … GRANT SELECT`), like the `postgres` superuser
  password.

## See also

- [`index.md`](index.md) — the full deployment doc set.
- `docs/project/v2.0.0-bump/t8-scripture-karn-playbooks/` — the first
  work item to write a real playbook by following this checklist.
- `docs/project/v2.0.0-bump/d2-monitoring-extension/` — extending
  monitoring to a service shaped like this (a scheduled job's "healthy"
  signal isn't HTTP uptime).
