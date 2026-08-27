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
  `roles/fastapi_backend/README.md`'s "if available" behavior).

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
repositories (`fastapi_backend`, `react_frontend`) originally always
deployed a branch (`main` in production, `develop` in staging) via `git`
module's `version:` parameter.

**Alternatives considered.**

1. Keep deploying `main`/`develop` branches directly (status quo, not
   compliant with §§25/27/31).
2. Require a human to always pass an explicit release tag
   (`-e fastapi_backend_release_tag=vX.Y.Z`) on every production deploy.
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

**Decision.** Option 3.
`fastapi_backend_use_release_tag`/`react_frontend_use_release_tag`
default to `false`; every playbook here sets them to
`deploy_env == 'production'`. When `true`, the role resolves
`fastapi_backend_release_tag`/`react_frontend_release_tag` if set,
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
  (`-e fastapi_backend_release_tag=<previous tag>`) instead of a manual
  git checkout on the server — see
  [`../deployment/rollback.md`](../deployment/rollback.md).
- The GitHub API call needs network egress from the control machine and a
  token with read access to Releases (the same `repo`-scoped PAT already
  used for cloning covers this).
- Database migrations are still never automated (a separate, pre-existing
  gap — see Constitution §31.3 and `ops/my-server/README.md`'s "Multiple
  frontends sharing one backend" section) — rolling back the *code* to an
  older release tag does not roll back the *database*. This is spelled
  out explicitly in the rollback runbook so it's never assumed away.

## ADR-3: Production email uses a transactional provider, not self-hosted

**Context.** `barrins_api` already implements signup email verification
(see [Signup & Email Verification][signup-email-verification]): a
`EmailSender` abstraction with a stdlib-`smtplib`-based
`SMTPEmailSender` for prod/staging. Production currently has no relay
configured (`SMTP_*` blank in
`ops/my-server/secrets/barrins_api/production.env`); the only relay used
so far is a temporary personal Gmail account
(`barrins-identity@gmail.com`), adopted under time pressure before
Tamiyo Scroll's launch. The domain `barrins-codex.org` is available to
send from a proper address (e.g. `identity@barrins-codex.org`), which
raised the question of whether to run a full mail server on the VPS
instead.

**Alternatives considered.**

1. Self-host a full mail server (Postfix, optionally Dovecot) on the VPS,
   managing `identity@barrins-codex.org` entirely in-house.
2. Keep the personal Gmail relay as the long-term production setup.
3. Use a dedicated transactional email provider (e.g. Brevo, Mailgun,
   SES, Postmark) as the SMTP relay, with `identity@barrins-codex.org`
   verified as the sending domain.

**Trade-offs.**

- Option 1 gives full control and no per-provider volume caps, but has
  real hidden costs for a one-VPS setup: outbound port 25 is blocked by
  default on most VPS providers and must be requested unblocked; a fresh
  VPS IP has no sending reputation, so mail lands in spam even with
  correct SPF/DKIM/DMARC/PTR until the IP "warms up" over weeks; and it
  requires indefinite maintenance (spam filtering, security patching,
  monitoring) for a purely outbound, low-volume use case (signup codes,
  future password resets). This cost is only justified if a real inbox
  (receiving mail at `identity@barrins-codex.org`) is ever required — not
  the case today.
- Option 2 (current temporary state, see signup_email_verification.md's
  "Gmail specifics" and "Temporary workaround" sections) requires an app
  password, ties the `From` header to the authenticated Gmail account,
  and caps at ~500 emails/day. Acceptable as a stop-gap, not as the
  long-term production identity: no `identity@barrins-codex.org` address,
  and it depends on a personal account rather than the project's own
  domain.
- Option 3 keeps `identity@barrins-codex.org` as the visible sender,
  delegates deliverability and IP reputation to the provider, costs €0 at
  signup/reset volumes (free tiers: Brevo 300/day, SES ≈$0.10/1000
  emails), and needs **no backend code change** — `SMTPEmailSender`
  already speaks generic SMTP, so switching relay is purely a
  configuration change (`SMTP_HOST`/`SMTP_USERNAME`/`SMTP_PASSWORD`/
  `SMTP_FROM_ADDRESS` in the production secrets file). It does require
  provisioning DNS records (SPF, DKIM, optionally DMARC) for
  `barrins-codex.org` with the chosen provider.

**Decision.** Option 3. Production email sending for
`identity@barrins-codex.org` goes through a transactional provider's SMTP
relay, never a self-hosted MTA, as long as the need stays one-directional
(sending only). Provider selection (Brevo vs Mailgun vs SES vs Postmark)
is not yet settled.

**Consequences.**

- No new dependency or code change: `get_email_sender()`
  (`app/services/email/__init__.py`) already selects `SMTPEmailSender`
  whenever `smtp_host` is set, regardless of which relay sits behind it.
- Before go-live: verify `barrins-codex.org` with the chosen provider
  (DNS records for SPF/DKIM/DMARC), fill `SMTP_*` in
  `ops/my-server/secrets/barrins_api/production.env` (currently blank),
  and flip `REQUIRE_EMAIL_VERIFICATION` back to `true` once confirmed
  working end-to-end.
- Self-hosting a full mail server is not ruled out permanently — it
  becomes worth revisiting only if `identity@barrins-codex.org` needs to
  *receive* mail as a real inbox, not just send it.

[signup-email-verification]: ../../back/barrins_api/signup_email_verification.md

## ADR-4: First production release — backup gating, monitoring, Moxfield

**Context.** v1.0.0 is the first-ever production release of this monorepo:
no application code, no production database, and no production VPS
monitoring existed before it. Three cross-cutting decisions had to be made
before it could ship, each falling under Constitution §16.2's "never
guess" list (changing deployment architecture, introducing a dependency,
handling secrets): whether the documented backup gap should block the
release, how the production VPS should be monitored, and how the Moxfield
import feature's required credential should be handled.

**Alternatives considered.**

1. **Backup gating** (Constitution §36):
   1. Ship v1.0.0 first; add the `postgres_backup` role as a fast-follow.
   2. Treat the undocumented, never-tested backup/restore process as a
      release blocker — no production migration runs before it exists.
2. **Monitoring** (Constitution §31.2, §30):
   1. No monitoring for v1.0.0; add it later.
   2. Self-hosted Uptime Kuma (Docker, alongside the existing pgAdmin
      container).
   3. An external free uptime-checker service polling `/health` plus
      certificate-expiry alerting.
3. **Moxfield credential handling** (Constitution §34):
   1. Let the frontend hold the Moxfield User-Agent value and call the
      Moxfield API directly.
   2. Treat it as a backend-only secret, handled exactly like
      `SECRET_KEY`/`SMTP_PASSWORD`.

**Trade-offs.**

- Backup: option 1 ships sooner but means the first-ever production
  migration would run with zero verified recovery path — directly against
  §36's "a backup that has never been tested is not considered reliable,"
  and there is no worse time to discover a broken restore than after real
  user data already exists. Option 2 delays go-live until a role and a
  verified restore drill exist, but a first release is the cheapest point
  to require this (no production data is at risk yet if staging testing
  surfaces a problem).
- Monitoring: option 1 is fastest but leaves any production outage
  undetected until a user reports it. Option 2 stays in-repo/on-VPS but
  can't detect a full VPS outage — it's hosted on the same machine it
  watches — and adds another service to maintain. Option 3 detects
  total-VPS-down failures from an external vantage point at zero/near-zero
  cost, at the price of a third-party account and, on the chosen free
  tier, a 2-tracker cap that leaves `tamiyo_scroll` unmonitored on its own.
- Moxfield: option 1 is simpler to wire but permanently exposes a
  credential to every browser session, an outright §34 violation. Option 2
  keeps the credential server-side only and pushes the 1 req/s rate limit
  into the backend's responsibility, in exchange for the credential never
  reaching a client — confirmed in UAT via network-tab inspection during
  a real import.

**Decision.**

1. Backup: option 2. `postgres_backup` (B1) must exist, be active, and
   have a verified restore drill on staging before the first production
   deploy (B6) applies any migration — B6 depends on B1 for exactly this
   reason.
2. Monitoring: option 3, provider **HetrixTools** — chosen over
   self-hosted Uptime Kuma specifically because it can observe a total
   VPS failure from outside, and over no monitoring because §31.2/§30
   require it. Selection criteria: free tier, private status page by
   default, minimal signup PII.
3. Moxfield: option 2. `MOXFIELD_USER_AGENT` is a `SecretStr` backend
   setting (`app/config/base.py`), never included in any API response and
   never reachable from `apps/tamiyo_scroll` — the import flow is
   backend-only per §4.1.

**Consequences.**

- Backup and monitoring are both host/VPS-level concerns rather than
  per-application ones, reinforcing the "one application, one playbook"
  boundary (§26.1): `postgres_backup` is wired into
  `postgresql_pgadmin.yml`, not into `barrins_api.yml`, and a future
  application added to this VPS inherits the same timer without new
  backup wiring of its own (only a new `pg_dump` target if the schema
  convention changes).
- HetrixTools' 2-tracker free-tier cap means a `tamiyo_scroll`-only
  outage (backend healthy, static frontend down) isn't independently
  detected — accepted because both frontends share one backend, so most
  real outages are still caught. Revisit if a paid tier, or a
  frontend-specific check, becomes worth it.
- The Moxfield rate limiter (`asyncio.Lock`, module-level) is
  process-local — correct only for the current single-worker deployment.
  If `barrins_api` ever scales to multiple workers, the 1 req/s cap needs
  a shared (Redis/Postgres-backed) limiter instead — not needed today
  per §39, but tracked here so it isn't assumed away.

## ADR-5: Barrin's Scripture — repo, database access, archive storage

**Context.** v2.0.0 introduces Barrin's Scripture, the scraped-tournament
data domain the request describes as "under `apps/barrins_scripture`."
Real scraping code already exists today, but as a separate, standalone
public repository (`barrins-project/mtg_scraper`), with its own CI, its
own JSON-archive submodule (`mtg_decklist_cache`), and its own versioning
(`0.2.0`). Three related questions had to be resolved before T1–T3 could
start: where the code ends up living, whether it gets its own database
credential, and what happens to the existing JSON archive.

**Alternatives considered.**

1. **Repo location** (`v2.0.0-bump/index.md` §1.1):
   1. Merge `mtg_scraper` into the monorepo at `apps/barrins_scripture`
      (history-preserving `git subtree`/`filter-repo`), retire the
      standalone repo.
   2. Keep `mtg_scraper` as its own repository (renamed), monorepo only
      references it via a deployment playbook — no `apps/barrins_scripture`
      folder at all.
   3. Treat `apps/barrins_scripture` as a **new** implementation that
      supersedes `mtg_scraper` (a rewrite, not a migration), archiving
      `mtg_scraper` once feature parity is reached.
2. **Database access** (§1.2):
   1. Barrin's Scripture holds its own `DATABASE_URL`, writes directly to
      `bs_*` tables it also owns/migrates.
   2. Barrin's Scripture never touches Postgres — it scrapes, writes the
      JSON archive, and calls a private, backend-only ingestion route on
      `barrins_api` (`POST /internal/scripture/ingest`) that performs the
      actual insert/upsert; `barrins_api` remains the sole schema/migration
      owner.
   3. Barrin's Scripture writes to a separate database/schema it owns,
      `barrins_api` reads from it via a replica/FDW/second `DATABASE_URL`.
3. **Archive storage** (§1.3): keep archiving scrapes as JSON outside the
   database (already `mtg_scraper`'s existing, production-proven
   behavior) — the only open question was *where* that archive lives,
   given it is already gigabytes in size and every new data-heavy domain
   this release adds compounds that: inline it into the monorepo's own
   history, or keep it in its own git repository so cloning the monorepo
   stays cheap regardless of archive size.

**Trade-offs.**

- Repo location: option 1 matches the literal "under
  `apps/barrins_scripture`" framing and the `tolaria_news` precedent, but
  is real history-rewrite migration work and loses `mtg_scraper`'s
  independent release cadence. Option 2 is the least work but contradicts
  that framing and keeps a second, differently-structured CI/release
  process alongside the monorepo's own. Option 3 avoids a risky
  history-rewrite but re-derives working, already-scheduled,
  already-tested (0.2.0, several bugfix releases) scraper logic from
  scratch.
- Database access: option 1 is the simplest data path (no extra HTTP hop)
  but duplicates schema ownership across two migration tools (a real
  §26.1 "one application, one playbook" violation applied to schema) and
  ships a second Postgres credential with production write access to a
  scheduled scraper — a wider secret-exposure surface than today's single
  `barrins_api` `.env` (ADR-1's model). Option 2 keeps exactly one thing
  (`barrins_api`) owning the schema and migrations, consistent with every
  other domain (`users`, `ts_*`), at the cost of one internal-only route
  and a service-to-service credential (same shape as the existing
  Moxfield-credential precedent: narrow-scope, backend-only, never
  reaching a browser). Option 3 avoids the HTTP coupling but introduces a
  second database/schema to operate, back up, and monitor (Constitution
  §36 already flags backups as a real operational cost) for a marginal
  benefit over option 2's single extra route.
- Archive storage: inlining into the monorepo's own history means clone
  cost grows unboundedly with scrape volume, forever. A dedicated archive
  repository (submodule) keeps the monorepo cheap to clone regardless of
  archive size, at the cost of one more repository to track.

**Decision.**

1. Repo location: option 3. `apps/barrins_scripture` is a new
   implementation that supersedes `mtg_scraper` — a rewrite, not a
   history-preserving migration. `mtg_scraper` is archived (GitHub repo
   archived, README redirected) once `apps/barrins_scripture` reaches
   feature parity: MTGO + MTGTop8 scraping, the same daily/biweekly-gap
   scheduling, the same JSON-archive output.
2. Database access: option 2. `barrins_api` remains the sole schema and
   migration owner. Barrin's Scripture scrapes, archives, and calls
   `POST /internal/scripture/ingest`, authenticated by a service
   credential, never exposed to any frontend. This route must also
   support a **maintenance-mode gate**: it rejects/queues upsert requests
   during maintenance windows rather than writing against a database
   mid-migration or failing opaquely — a narrow, route-scoped check (not
   a global maintenance page). The scraper keeps running on its own
   schedule regardless of the gate; a scrape taken during a maintenance
   window is simply retried against the ingestion route once the window
   closes, made safe by the JSON archive below.
3. Archive storage: the JSON archive keeps living in its own git
   repository (a submodule — either the existing `mtg_decklist_cache` or
   a renamed successor), never inlined into the monorepo's own history.
   T1 (repo migration) and T3 (ingestion pipeline) must design against
   this from the start.

**Consequences.**

- `mtg_scraper` and `mtg_decklist_cache` currently live in the
  `barrins-project` GitHub organization, which the user intends to delete
  once no longer needed — not on a deadline, but a given. Both
  repositories must be transferred (full history preserved, e.g.
  `git clone --mirror` + push) to a durable location (a different org, or
  under the `Spigushe` account — not yet specified) as part of T1's own
  migration work, whenever there is confidence to do so.
- `barrins_api` gains one new internal-only route and one new
  service-to-service credential to document (`security/secrets.md` /
  `ops/my-server/secrets/README.md` — tracked as D3), following the same
  "never in git" pattern as every other secret (ADR-1).
- Barrin's Scripture can be redeployed, rolled back, or reworked without
  ever needing a database migration of its own — it stays as replaceable
  and independently deployable as `tolaria_news` or `tamiyo_scroll` are
  today.
- Table naming for this domain uses the `bs_` prefix, matching the
  existing `ts_` (Tamiyo Scroll) two-letter-per-app convention — not
  `dl_`, which was inherited from a dead reference doc (see F7) and was
  never a real convention.
- The DB can be dropped and fully rebuilt at any time by replaying the
  JSON archive through the ingestion route (or a bulk-load script) — the
  archive is the durable source of truth, the database is a derived,
  rebuildable projection of it.

## ADR-6: Karn Tablets ships real, basic clustering functionality in v2.0.0

**Context.** The request describes Karn Tablets only as "the backend
service in charge of computing/providing ML and DL data," with no prior
planning anywhere in the repository or constitution. An initial
recommendation was to scope it out of v2.0.0 entirely (placeholder only),
on the grounds that a full ML/DL service is open-ended scope that risks
absorbing the whole release. The user overrode that recommendation.

**Alternatives considered.**

1. Placeholder only for v2.0.0: `apps/karn_tablets/README.md` + a docs
   stub, real implementation deferred to a future release.
2. Real, deliberately basic functionality in v2.0.0: metagame clustering
   over a defined time window, aggregated to visualize deck-type
   distribution, with "predictions" named as a future direction rather
   than separately scoped now.

**Trade-offs.** Option 1 avoids absorbing an open-ended ML scope (model
choice, training data volume, inference hosting, a fourth backend to
secure and monitor) into an already-heavy release, but ships a fourth
named application with zero real capability, deferring the actual value
the request asked for. Option 2 delivers something real and scoped
(clustering + aggregation only, no open-ended "predictions" deliverable
yet) but depends on data that doesn't exist yet (T2's schema, T3's
ingestion pipeline actually landing data), so its own critical path is
outside Karn Tablets' code entirely.

**Decision.** Option 2, per the user (2026-07-26). Scope for v2.0.0:

- **Clustering**: cluster the metagame (deck archetypes seen in scraped
  tournament results) over a defined time window. Two candidate windowing
  strategies are both viable, not yet narrowed to one — a rolling 30-day
  window, or a banlist-period window (non-overlapping periods aligned to
  Magic's Banned & Restricted announcement rhythm: last Tuesday of an
  odd-numbered month to the last Monday of the following odd-numbered
  month). Whether v2.0.0 needs both modes or just one default is a task
  for T6, not decided here.
- **Aggregation**: aggregate clustering output specifically to visualize
  deck-type distribution (archetype share of the metagame within the
  chosen window), not raw per-deck predictions.
- **"Predictions"** is named in scope but read as the natural next step
  once deck-type clusters exist (e.g. matchup/impact estimation per
  Constitution §45), not a separate, unscoped deliverable — exact
  prediction targets still need defining before implementation.
- **Tooling**: no ML library/framework is chosen here. Any new dependency
  follows the existing approval process (§4.7/§22 — problem, alternatives,
  maintenance impact, approval before adding). This work falls under
  Constitution §45 (already anticipating "macro archetype classification")
  and must follow §45.1 (ML stays isolated from frontend/auth/reports/core
  domain) and §45.2 (validated data, reproducible pipelines, documented
  datasets; every result carries source data/version/model info).

**Consequences.**

- Karn Tablets' real implementation depends on T2 (schema) and T3
  (ingestion pipeline) actually landing data, not just on this scope
  decision being confirmed.
- T6's page needs a full rewrite from a placeholder scaffold to a real,
  scoped deliverable; T8's deployment-playbook item is no longer
  deferrable alongside a placeholder — Karn Tablets is likely a third
  ops/my-server service *shape* (a periodic clustering job, possibly with
  a small results-serving API), distinct from the existing
  `fastapi_backend`/`react_frontend` roles (tracked as D1).
- No ML library/framework commitment exists yet — choosing one still
  requires its own §4.7/§22 approval record before implementation starts.

## ADR-7: Delay Barrin's Identity, keep identity on `barrins_api`

**Context.** Constitution §13.1 requires one account across every
application; `barrins_identity` is unmerged (README/CHANGELOG-only
placeholder). v2.0.0 adds two more applications that touch identity in
some way (Tolaria News frontend, Team accounts for Tamiyo Scroll, §1.6),
making this decision more schedule-critical than before — items T5, T7,
S2, and S1's "toggle to receive" extension all touch identity.

**Alternatives considered.**

1. Build `barrins_identity` now, before any v2.0.0 identity-touching
   feature starts, so every new feature is built against the final
   shared-identity service from day one.
2. Delay `barrins_identity` until a second real consumer with actual user
   management exists (today only `tamiyo_scroll` qualifies — Tolaria News
   is a public, read-only BFF with no accounts feature planned for
   v2.0.0), with every v2.0.0 identity-touching feature continuing to use
   `barrins_api`'s existing single `users` table and JWT auth directly.

**Trade-offs.** Option 1 avoids ever having to migrate an interim account
model, but means designing and building a standalone identity service
speculatively, before a second real consumer exists to design it against
— exactly the premature-abstraction risk Constitution §39/§48 warn about.
Option 2 defers that build-out, but only stays debt-free if every
identity-touching v2.0.0 feature strictly avoids inventing its own
per-app account model in the meantime (per Constitution §13.1, "do not
create application-specific user tables") — otherwise, delaying just
relocates the migration cost to later, multiplied by however many
divergent interim models were built.

**Decision.** Option 2, per the user (2026-07-25). `barrins_identity`'s
implementation is delayed until two front-end applications with real
user management have shipped. This generalizes the same v2/v3 split
confirmed for the admin metrics dashboard (ADR-9): don't build the
standalone identity service speculatively, wait until a second real
consumer exists to design against.

The condition attached to this delay, stated explicitly by the user: it
must not create technical debt. Every v2.0.0 feature that touches
identity (Tolaria News, if it ever gains accounts; Team membership, §1.6)
keeps using `barrins_api`'s existing single `users` table and JWT auth
directly, rather than inventing an interim account model per app that
would later need migrating onto `barrins_identity`.

**Consequences.**

- As long as the no-new-user-tables condition holds, delaying
  `barrins_identity` costs nothing extra later: there is only ever one
  `users` table to eventually move, not several divergent ones to
  reconcile.
- Team ownership (`ts_teams`/`ts_team_members`, ADR-8) is explicitly
  **interim**: `barrins_api` owns it for v2.0.0, ownership transfers to
  `barrins_identity`/Goblin Guide once released. A full generic "groups"
  subsystem superseding this interim schema is expected alongside
  `barrins_identity`'s own build-out — timing not yet decided.
- User roles remain owned by `barrins_api` until `barrins_identity` is
  implemented — not framed as already `barrins_identity`'s concept
  beforehand.
- This resolves I1 as "not blocking, with a condition," not "must be
  built before T5/S2 start."

## ADR-8: Team creation, joining, and ownership model for Tamiyo Scroll

**Context.** The request flags team creation as explicitly undecided
("Need to workout how the team is created"). No existing concept of a
group/team exists anywhere in the schema — `ts_*` tables are all
single-owner. A "Team Decks" selector and shared reporting both need a
real group identity to filter/gate on.

**Alternatives considered.**

1. Any authenticated user can create a team and becomes its first
   member/owner; others join via an invite code or a direct add by the
   owner.
2. Teams are admin-provisioned only, matching the existing admin/user
   role split.
3. Defer "team" as its own entity entirely; reuse the existing read-only
   sharing primitive (`ts_user_settings.data_shared`) extended to a set
   of viewers (a `ts_share_grants` table replacing today's single
   boolean) instead of a new `teams` table.

**Trade-offs.** Option 3 is the cheapest to build (extends an
already-tested mechanism) but doesn't give a "Team Decks" selector a real
group identity to filter on unless a lightweight `ts_teams`/
`ts_team_members` pair is added on top anyway — so a real team entity is
likely needed regardless of which creation semantics are chosen. Option 2
matches existing role-gating precedent but adds friction to a feature the
request doesn't describe as sensitive. Option 1 is the lowest-friction
default and matches how most collaborative products handle team creation.

**Decision.** Option 1, with a real `ts_teams`/`ts_team_members` entity,
per the user (2026-07-25). Full spec:

- **Creation**: any authenticated user can create a team and becomes its
  first member/owner. No admin gate for v2.0.0. A future gate restricting
  creation to the "Advanced User" tier (`role_c`, ordinal level 2 in
  `auth_roles.md`'s `UserRole` enum) is recorded as a later-release option
  only, so the schema doesn't need reshaping to add it — not built now,
  and not framed around any paywall/monetization reasoning.
- **Joining**: an 8-character invite code, generated per team, given out
  by existing members to anyone they want to invite.
- **Team page**: name, description, member list, and one dedicated
  chat-like discussion thread per deck under test (not one thread per
  team) — which decks get a thread is decided by the team admin
  (creator/owner).
- **Deck validation gate — deferred to v3.0.0 (2026-07-27)**: a deck
  shared into a team was originally scoped to have its name and cards
  validated against backend-held MTG data before being usable in that
  context, blocked on S8 (the MTGJSON pipeline). Deferred entirely out of
  v2.0.0, same treatment as S10: v2.0.0 accepts a team-shared deck the
  same way a personal deck is accepted today, unvalidated — no new
  inconsistency, since no deck anywhere in Tamiyo Scroll is validated
  against MTG data yet. Not a constitutional rule tied to teams
  specifically; backend validation of shared content stays a working
  direction pursued feature-by-feature in later Tamiyo Scroll releases,
  starting once S8 exists.
- **Reporting**: team members get access to the PDF report (S5) of each
  deck shared into the team.
- **Deletion isolation**: removing a deck from a team never affects that
  deck's owner's individual results on their own profile — team-level and
  personal-profile data are independent views over data the owner still
  owns.

**Ownership.** Teams are groups of persons, modeled once ecosystem-wide
(not Tamiyo-Scroll-specific). `barrins_api` is the interim owner for
v2.0.0 (see ADR-7); ownership transfers to `barrins_identity`/Goblin
Guide once released.

**Consequences.**

- New tables: `ts_teams`, `ts_team_members` (interim, `barrins_api`-owned
  per ADR-7); schema must not need reshaping when the future Advanced
  User creation gate is added later (an owner/creator role check on an
  existing table, not a new one).
- S2 (team sharing) builds on S1's existing sharing mechanism once teams
  exist, and no longer depends on S8 for v2.0.0 now that its
  deck-validation gate is deferred to v3.0.0. S4 still depends on S8
  (card images/sorting), which replaces the MTGJSON pipeline that turned
  out not to exist (F8).
- This resolves I5.

## ADR-9: Admin metrics dashboard — v2.0.0-embedded, v3.0.0-externalized

**Context.** An admin usage/metrics dashboard for Tamiyo Scroll must be
available starting v2.0.0, per the user, but the long-term shape
externalizes into its own standalone application covering every
publicly-deployed frontend, gated through Barrin's Identity/Goblin Guide
— both explicitly v3.0.0-scoped, not to be embarked before then. Two
separate questions needed resolving: what "métrique" concretely means,
and how to build the v2.0.0 version without forcing a rewrite at v3.0.0.

**Alternatives considered (what "métrique" means).**

1. Product/usage analytics: signups over time, active users, personal
   decks created, matches logged, card-tests submitted, sharing adoption
   — all derivable from existing `ts_*`/`users` tables with aggregate
   queries, no new data collection needed.
2. Operational/infrastructure metrics: request latency, error rates,
   endpoint call volume — overlaps with, and would likely duplicate, the
   existing HetrixTools setup (Constitution §4.2, "no duplicated business
   logic," generalized to "no duplicated monitoring surface").
3. Per-user moderation/support view (which accounts exist, last login) —
   touches account data more directly than options 1 or 2, with sharper
   privacy implications.

**Trade-offs.** Option 1 needs no new data collection and no new
constitution ground (the backend already holds this data for its normal
function), but the constitution has no privacy/data-retention/analytics
policy at all — a real, previously undocumented gap this feature makes
more visible than the data merely existing in the database already did.
Option 2 duplicates monitoring surface already covered by HetrixTools
(F1). Option 3 has real privacy implications with no policy to govern it.

**Decision.** Option 1, staged: ship the simplest signals first (account
count, decks created, matches recorded) to establish whether the app is
being adopted at all, before investing in anything deeper. Retention,
per-feature engagement, and sharing-adoption breakdowns are explicit
follow-on work, not v2.0.0 scope.

**v2.0.0 architecture.** Ships embedded: backend routes in `barrins_api`
(a new BFF sub-router, `app/api/tamiyo_scroll/admin.py`), UI in
`apps/tamiyo_scroll`, admin access gated by the existing `AdminUser`/
`require_role(UserRole.admin)` mechanism — no new auth system. No
`apps/`-level placeholder is created now for the future standalone
metrics app, Barrin's Identity, or Goblin Guide — all three are v3.0.0
work, out of scope for `proj/v2.0.0-bump` entirely.

**Forward-compatibility requirements** (Constitution §39 — anticipate
without prematurely implementing), so v3.0.0's externalization doesn't
force a rewrite:

1. Metrics computation lives in its own service module
   (`app/services/metrics/`), not inlined into
   `app/services/tamiyo_scroll/` — the module boundary is what gets
   lifted out wholesale later.
2. The aggregated data carries an app/source dimension from day one, even
   though v2.0.0 only ever populates it with one value (`tamiyo_scroll`)
   — retrofitting this column after other apps start feeding the rollup
   is avoidable rework. This does not mean building a multi-app
   aggregation pipeline now (YAGNI, §39/§48).
3. Metrics routes' authorization depends on `AdminUser` (fine for v2.0.0)
   rather than scattering direct `UserRole.admin` checks through route
   bodies — the v3.0.0 version authenticates admins via Barrin's
   Identity/Goblin Guide instead, a different provider, and the swap
   should only require changing the one dependency.

**Consequences.**

- A privacy/analytics policy gap in the constitution was confirmed real
  and blocking in practice by this decision, not just in theory — resolved
  via `consitution-amendment.md` Proposal 1, accepted by the user with one
  condition (any future GDPR alignment extends this policy, doesn't
  replace it). Applying that text to `docs/content/CLAUDE.md` is tracked
  via this same R5 effort, alongside every other accepted amendment.
- This resolves I6.

## ADR-10: Tolaria News' public BFF routes — rate-limited, not identity-gated

**Context.** T4 decided the Tolaria News BFF routes are public reads,
requiring no `CurrentUser` (unauthenticated tournament/metagame data, not
personal data). The user flagged that "public" shouldn't mean "open to
any caller" — these routes should be restricted to the Tolaria News
frontend specifically, "one way or the other." `apps/tolaria_news` is
planned as a static SPA calling `barrins_api`'s BFF cross-origin — a
secret embedded in a public static frontend's built JS bundle is readable
by anyone who opens devtools or downloads the bundle, so any option
assuming a hidden client-side credential only produces friction, not a
real boundary.

**Alternatives considered.**

1. CORS restriction only (§33): locks `Access-Control-Allow-Origin` to
   Tolaria News' origin. Stops other websites' JS, not direct scripts.
2. A shared "agent key" in the frontend build: extractable from the
   public bundle per the constraint above — friction, not a boundary, and
   cuts against §34 ("no secrets in the bundle").
3. Reverse-proxy-injected header: Tolaria News' own nginx vhost proxies
   `/api/*` to `barrins_api`, injecting a secret header the browser never
   sees — a real boundary, but flips the BFF call into a same-origin
   proxy, changing T5's calling pattern under §29/§26.1.
4. Accept CORS + rate-limiting as sufficient: "restricted to the Tolaria
   News app" as a soft goal, not a hard boundary, on the grounds that
   aggregated, already-public tournament results aren't sensitive enough
   to justify option 3's infrastructure.

**Trade-offs.** Options 1 and 2 raise friction, not a boundary, against a
determined caller. Option 3 is the only real access boundary, but changes
T5's calling pattern and adds an nginx-layer credential to document.
Option 4 is honest about the trade-off rather than shipping something
that looks like security but isn't — it does not, and does not claim to,
keep non-Tolaria callers out; it caps abuse volume instead. The two
realistic threats are (a) scraping-for-reuse and (b) load/cost from
abuse; only (b) is a harm independent of the data's already-public
nature, and rate-limiting addresses (b) directly. A true caller boundary
buys protection against (a) that the public nature of the data doesn't
justify paying for.

**Decision.** Option 4, per the user (2026-07-27). These routes stay open
public reads. The access posture is CORS (existing `ALLOWED_ORIGINS`) as
browser-only friction, plus inbound rate-limiting as the anti-abuse
control. "Restricted to the Tolaria News app" is explicitly recorded as a
soft goal, not a boundary.

**Consequences.**

- T4's done-statement ("no `CurrentUser` dependency") is preserved —
  rate-limiting adds no per-caller identity dependency to the route. T5's
  calling pattern is unchanged — no same-origin reverse-proxy flip.
- This is net-new work, not a config toggle: the only limiter in
  `barrins_api` today is the Moxfield importer's *outbound*
  per-process-only limiter; there is no inbound rate-limiting anywhere in
  the codebase. Inbound limiting on `POST /auth/token` is a separate,
  already-recommended-not-done open item (P-03).
- A naïve in-app limiter under multiple `barrins_api` workers multiplies
  the effective limit by the worker count (the same per-process caveat
  the Moxfield limiter carries). nginx already fronts every backend on
  `127.0.0.1:<port>` (§29) and is shared across all workers by
  construction, making it the lower-effort, on-pattern home for coarse
  per-IP limits on these routes, over a shared-state (Redis/DB) in-app
  limiter.
- The key, threshold, window, `429` response shape, and whether the limit
  is scoped to just the public BFF routes or applied globally are all
  still undefined — a follow-up before these routes ship, tracked on T4's
  page.
- A scraper pacing requests at a human-like rate is indistinguishable
  from a real reader and will not be blocked — the soft goal is genuinely
  soft, accepted rather than mitigated; the CORS entry must never later
  be read as access control against scripts.
- This resolves I7. `consitution-amendment.md` Proposal 6 records the
  durable rule this surfaces: `barrins_api` has no inbound rate-limiting
  anywhere today, a gap wider than just this one route.

## ADR-11: WeasyPrint for server-rendered training-session PDF reports

**Context.** S5 (PDF report of a training session) needs backend PDF
generation — no such capability exists anywhere in `barrins_api` today.
Constitution §4.1 argues for generating the PDF server-side from
already-computed stats rather than composing it client-side. Choosing a
library is itself "introducing a dependency" (§16.2), requiring
escalation rather than a silent pick. The user gave deciding criteria
rather than naming a library: **most stable, still being developed,
strong security, no data loss.**

**Alternatives considered** (researched 2026-07-27 against the stated
criteria).

1. **WeasyPrint** — pure-Python HTML/CSS-to-PDF renderer (CSS Paged Media
   spec). Releases roughly every 2–3 months. Two disclosed CVEs:
   CVE-2025-68616 (SSRF-protection bypass in `default_url_fetcher` via
   HTTP redirect, patched in 68.0) and CVE-2026-49452 (a CSS-properties
   vulnerability affecting `--presentational-hints` on untrusted HTML,
   patched in a later release). Both are scoped to untrusted HTML /
   external URL fetching.
2. **ReportLab** — mature canvas/Platypus-based PDF toolkit, ~3.5M
   monthly PyPI downloads, actively maintained (cadence less clearly
   evidenced than WeasyPrint's). Two disclosed CVEs, both RCE-class:
   CVE-2023-33733 (RCE via `rl_safe_eval`, exploitable through crafted
   markup, patched in 3.6.13) and CVE-2019-17626 (RCE via crafted XML in
   `paraparser`) — both stemming from expression-evaluation/
   markup-parsing features built into the library's own templating layer,
   a recurring design-level risk surface rather than a one-off bug.

**Trade-offs against the stated criteria.**

- **Security**: WeasyPrint's disclosed vulnerabilities require untrusted
  HTML or external URL fetching to trigger — neither applies to S5, since
  the report is rendered from backend-authored HTML/CSS built from
  already-computed, trusted stats. ReportLab's disclosed vulnerabilities
  are RCE-class, tied to a "safe eval"/markup-parsing feature that's part
  of the library's own internal templating rather than an opt-in feature
  a caller can simply avoid.
- **Actively developed**: WeasyPrint's 2–3 month release cadence is a
  clear, current signal; ReportLab's cadence was less clearly evidenced.
- **No data loss**: WeasyPrint's CSS-based layout is close to WYSIWYG —
  what's written in the HTML/CSS template is what renders. ReportLab
  requires explicitly placing every element via its canvas/flowable API —
  more room for a developer to silently omit or truncate content with no
  rendering-time signal, cutting against "no data loss" for a report
  meant to accurately reflect real stats.
- **Stability**: both are mature libraries; this criterion doesn't
  separate them.

**Decision.** WeasyPrint, on the stated criteria: actively developed,
disclosed vulnerabilities don't apply to this trusted, backend-authored
use case, and its CSS-based rendering model reduces the risk of
silently-missing content. Also reuses the team's existing HTML/CSS
skillset (the frontend is already Tailwind-based) rather than introducing
an unfamiliar drawing/flowable API.

**Consequences.**

- `weasyprint` becomes a new backend dependency (§22 — this research is
  the required escalation record).
- Must pin to the latest release at implementation time, confirmed to
  include fixes for both CVE-2025-68616 (≥68.0) and CVE-2026-49452 (exact
  version to verify then, not asserted here).
- Report templates are authored as HTML/CSS (e.g. Jinja2-rendered HTML
  fed to WeasyPrint), consuming the same `stats`/`decklist_coloring`
  services already used elsewhere (§4.1/§4.2 — no duplicated
  calculation).
- Implementation safeguard: the generated HTML must never include a
  user-controlled or externally-fetched URL (e.g. no remote images from
  arbitrary sources) — only backend-controlled, fixed assets — since
  that's the exact scenario CVE-2025-68616 concerned, even though it's
  patched.
- This resolves I8.
- Sources: [Python PDF library comparison (2026)][pdf-lib-comparison],
  [CVE-2025-68616][cve-2025-68616], [CVE-2026-49452 advisory][cve-2026-49452],
  [CVE-2023-33733][cve-2023-33733], [ReportLab CVE history][reportlab-cves].

[pdf-lib-comparison]: https://www.nutrient.io/blog/best-python-pdf-libraries/
[cve-2025-68616]: https://www.sentinelone.com/vulnerability-database/cve-2025-68616/
[cve-2026-49452]: https://advisories.gitlab.com/pkg/pypi/weasyprint/CVE-2025-68616/
[cve-2023-33733]: https://arcticwolf.com/resources/blog/cve-2023-33733-rce-vulnerability-in-reportlab-pdf-toolkit/
[reportlab-cves]: https://www.cvedetails.com/vulnerability-list/vendor_id-22377/product_id-76137/Reportlab-Reportlab.html

## ADR-12: Barrin's Scripture scheduling moves from VPS systemd back to GitHub Actions

**Context.** `docs/content/service/barrins_scripture/incidents/
2026-08-10-mtgo-network-block.md` documents a confirmed, IP-specific
network block: mtgo.com silently drops every connection from the VPS's
static outbound IP (`146.59.146.57`) — a `curl -4` straight to mtgo.com's
own IP hangs ~130s and returns nothing, while control domains
(`example.com`, `github.com`) over the same path succeed instantly, and
`mtr` shows 100% packet loss only on hops at/after mtgo.com's own
network. The same unmodified scraper code, run from a personal laptop and
from GitHub Actions runner IPs, reaches mtgo.com fine — ruling out a
blanket datacenter-IP policy and pointing at this one VPS IP specifically
(plausibly its own prior scraping volume/pattern). This is not fixable in
application code: no amount of timeout tuning or retry logic can complete
a TCP connection the destination silently drops.

This also revisits ADR-5/T1's 2026-07-29 decision, which had moved
scheduling *off* `mtg_scraper`'s GitHub Actions cron onto VPS systemd
(`ops/my-server/roles/scripture_scraper/`), for consistency with the
`postgres_backup` `.service`/`.timer` pattern — a decision this ADR
partially reverses, for a different, now-confirmed reason.

**Alternatives considered.**

1. **Request a new IP from the VPS provider (OVH).** Smallest change —
   architecture stays exactly as-is. Risk: if the block really is
   volume/pattern-triggered (the working theory), a new static IP can
   accumulate the same history and get flagged again later — this
   doesn't remove the failure mode, only resets its clock, and each
   recurrence costs a fresh round of network-level investigation to
   re-diagnose.
2. **Move only the MTGO leg to GitHub Actions**, keep MTGTop8 + the
   sweep/ingestion tick on the VPS. Exploits the confirmed evidence
   directly. Rejected: for one logical scraper, running two scheduling
   mechanisms (VPS systemd + GitHub Actions) is more operationally
   expensive than one — duplicated secrets, two places to monitor — for
   no benefit once MTGTop8 isn't the thing that's blocked.
3. **Move the whole scraper (MTGO + MTGTop8 + sweep) to GitHub Actions.**
   Same proven-safe path as option 2, applied to the whole pipeline
   instead of splitting it. Reverts more of T1's scheduling decision, but
   is the cheaper shape operationally — one scheduling mechanism, one set
   of secrets, one place to look when something fails.
4. **Route MTGO traffic through a proxy**, keep VPS scheduling unchanged.
   A new external dependency (§22 approval process), ongoing
   cost/maintenance, and doesn't remove the single-point-of-failure
   concern the IP-specific block already demonstrated.

**Trade-offs.**

- GitHub Actions runner IPs are drawn from a large, rotating pool —
  structurally resistant to the "one IP accumulates enough history to get
  individually flagged" failure mode a static VPS IP is exposed to,
  regardless of how that IP was obtained.
- The repo is public, so GitHub Actions minutes are free — no cost
  difference between options 2/3.
- Losing `Persistent=true`'s missed-run catch-up: GitHub Actions
  `schedule` triggers are best-effort, with no equivalent guarantee. In
  practice this is close to moot here — `scrape`'s MTGO default window
  is "5 days ago to today" and the sweep's default lookback is 7 days,
  so a single missed scheduled run is picked up whole by the next one.
- Gaining back email-on-failure notification: the VPS migration
  (T1/T8) explicitly dropped `mtg_scraper`'s
  `dawidd6/action-send-mail` step as a known, accepted trade-off, pending
  a generic scheduled-job notification mechanism (D2/F1). GitHub already
  emails the repo owner by default when a scheduled workflow run fails,
  so moving back to Actions recovers equivalent behavior without
  reintroducing that dependency.
- Secrets duplication: `ARCHIVE_PUSH_TOKEN` and `SCRIPTURE_INGEST_TOKEN`
  now also need to exist as GitHub Actions repository secrets, alongside
  their existing local, git-ignored `ops/my-server/secrets/` copies —
  one more place a rotated value needs updating.

**Decision.** Option 3 — move MTGO + MTGTop8 scraping and the sweep/
ingestion tick to a single new workflow,
`.github/workflows/scripture-scrape.yml`, scheduled daily at the same
22:00 UTC the VPS timer used, plus `workflow_dispatch` for manual/backfill
runs. `ops/my-server/roles/scripture_scraper/` is not deleted: its
`.service`/`.timer` units, wrapper scripts, and the (now-redundant) local
archive clone and app checkout are torn down on the VPS via a new
`scripture_scraper_teardown` role var, but the role's deploy logic stays
in the repo unchanged behind that same var — a rollback is "redeploy with
the var unset," not "resurrect the role from git history."

**Consequences.**

- `barrins_api`'s ingestion endpoint (`POST /internal/scripture/ingest`,
  ADR-5) and its idempotent-upsert contract are unaffected — the sweep
  still calls the same route, just from a different runner.
- The JSON archive (`Spigushe/mtg_decklist_cache`) is now committed to
  directly from GitHub Actions instead of via the VPS's local clone +
  sweep-timer push — same repository, same commit identity
  (`Barrin's Scripture` / `scripture@barrins-codex.org`), same
  idempotent "only commit if `git status --porcelain` is non-empty"
  guard.
- If mtgo.com ever also blocks GitHub Actions' IP ranges (a broader,
  differently-shaped block than what's confirmed today), this decision
  would need revisiting — nothing here rules that out, it's just not
  what the evidence in the 2026-08-10 incident shows.
- This resolves the 2026-08-10 incident.

## ADR-13: Karn Tablets output — data flow, scope, and consumption surface

**Context.** T4 v1 shipped Tolaria News' tournament/deck/standings routes
without the archetype-shaped ones (`/metagame`, `/archetypes`, `/trends`)
— those depend on Karn Tablets (T6), which ADR-6 scoped but which hadn't
started (`apps/karn_tablets` didn't exist) and left two sub-decisions open
(windowing default, consumption surface). T6's own plan additionally
defaulted the consumption surface to the S6 admin dashboard only, not
Tolaria News — the opposite of what a "full Tolaria News BFF" needs.
Planning this iteration (2026-08-11) required resolving all of this
together, since they're interdependent: the consumption surface decides
who needs the data, which decides how it should reach them.

**Alternatives considered — data flow.**

1. **Live synchronous API.** Karn Tablets self-schedules its own
   retraining internally and exposes a small read API; `barrins_api`'s
   Tolaria News BFF and the S6 dashboard call it live, per request.
2. **Push-based.** Karn Tablets self-schedules retraining the same way,
   but pushes its results to a new `barrins_api`-owned internal route
   after each run (mirrors `POST /internal/scripture/ingest`, ADR-5's
   "one schema owner" pattern); `barrins_api` stores them in its own
   tables, and every consumer reads Postgres directly.

**Trade-offs.** Option 1 keeps Karn Tablets fully decoupled from
`barrins_api`'s schema, but makes the public Tolaria News BFF's read path
depend on Karn Tablets' uptime and latency at request time — a dependency
none of v1's routes have today (they're Postgres-only). Since clustering
is inherently periodic, not real-time, that live coupling buys nothing.
Option 2 costs `barrins_api` a small amount of schema it doesn't compute
itself (the same trade ADR-5 already accepted for Barrin's Scripture,
for the same reason: one schema owner, zero new runtime dependency on the
public read path) but keeps Tolaria News exactly as available as it is
today regardless of Karn Tablets' own uptime, and lets Karn Tablets itself
collapse to a plain scheduled job (no inbound API to serve, so no
persistent process, no internal scheduler library) rather than the
"scheduled job plus narrow API" hybrid service shape ADR-6 anticipated as
a possible third `ops/my-server` shape.

**Decision.** Option 2 (push-based), per the user, 2026-08-11.

**Alternatives considered — scope and windowing.**

- **Consumption surface**: T6's plan defaulted to S6 (admin dashboard)
  only. **Amended to Tolaria News + S6, both** — the whole point of this
  iteration is exposing the data publicly; S6 keeps showing the same
  numbers for admin oversight, reading the same tables (Phase 5 of the
  implementation plan), so there's no drift between the two views.
- **Windowing**: T6 left rolling-30-day vs. banlist-period undecided.
  **Both, selectable** — v1 of Karn Tablets implements both modes rather
  than picking a single default.
- **Format scope**: `bs_tournaments.format` covers every format
  `barrins_scripture` scrapes (MTGO and MTGTop8 both cover multiple
  formats), but `apps/tolaria_news/README.md` names the app a "Duel
  Commander tournament aggregator." Karn Tablets' v1 clustering input is
  therefore filtered to `format == "Duel Commander"` only, matching the
  same string check `services/tolaria_news/decks.py` already uses for
  commander derivation. No `format` query parameter is added to the new
  BFF routes for v1 — there is exactly one consumer and it only ever
  wants one format; adding the parameter now would be an unused
  abstraction (Constitution §48).

**Consequences.**

- T6's page is amended: consumption surface (Tolaria News + S6), both
  windowing modes, Duel-Commander-only input, push-based (not live-API)
  output.
- T8's page is amended: Karn Tablets' deployment shape is a scheduled job
  (systemd timer, matching `scripture_scraper`'s `.service`/`.timer`
  pattern), not a new hybrid role — it reuses the existing scheduled-job
  precedent directly. It needs no inbound network exposure at all (only
  outbound, to Postgres and to `barrins_api`'s ingestion route), which
  also resolves what would otherwise have been an open Agent-3
  network-exposure question under the live-API alternative.
- `barrins_api` gains a new owned schema (`kt_*` tables, mirroring the
  `bs_*` naming convention already used for Barrin's Scripture's tables)
  and a new internal ingestion route (`POST /internal/karn/ingest`),
  authenticated by a static shared secret (`KARN_INGEST_TOKEN`) the same
  way `SCRIPTURE_INGEST_TOKEN` gates `POST /internal/scripture/ingest`.
- A later expansion — feeding Tamiyo Scroll's own results (`ts_*`) into
  Karn Tablets alongside scraped tournament data — is anticipated but not
  built now (Constitution §39): Karn Tablets' data-access layer should
  keep its "read decks to cluster" step behind a per-source boundary
  (today: one reader, Duel-Commander-only `bs_*`) rather than hardcoding
  a single-source assumption, and its archetype labels should be chosen
  without colliding with Tamiyo Scroll's existing `ArchetypeCategory`
  enum (S11's personal-deck macrotype) later.
- The clustering algorithm/library itself is still not chosen — that
  still requires its own §4.7/§22 approval record before implementation
  starts on Karn Tablets' pipeline.
- See `docs/project/v2.0.0-bump/t4-tolaria-news-bff/index.md`,
  `t6-karn-tablets-scaffold/index.md`, and
  `t8-scripture-karn-playbooks/index.md` for the full implementation
  breakdown.

**Amendment (2026-08-27).** The "no `format` query parameter is added to
the new BFF routes for v1" point above is superseded by the user: the
`/metagame`, `/archetypes`, `/trends`, and the S6
`/admin/metrics/karn-tablets` routes all take an optional `format` query
param from v1 (defaulting to `"Duel Commander"`, the only populated value
today). Rationale: the param will be needed as soon as Karn Tablets
clusters more than one format, and retrofitting a parameter onto an
already-public contract is worse than carrying it from the start. Nothing
else changes — the pipeline still pushes Duel-Commander-only data with no
`format` field, the ingest route's body still has no required `format`,
and the ingester stamps `"Duel Commander"` (`INGEST_DEFAULT_FORMAT`). The
`kt_*` schema, the ingester's archetype matching, and both read surfaces
are scoped by `(format, window_kind)` so a multi-format pipeline later
needs no schema or contract change.

## ADR-14: Tamiyo Scroll pagination — dedicated `Paginated[T]`, not `Envelope`

**Context.** The user wants pagination on Tamiyo Scroll's two largest
list endpoints — `GET /matches` (the "Journal") and `GET /card-tests`
— with a page size the user selects from {10, 25, 50}. Tolaria News
already has a pagination-shaped response wrapper, `Envelope[T]` /
`Meta` / `Page` (`{data, meta, page?}`, `responses_tolaria_news.py`),
raising the question of whether Tamiyo Scroll should adopt the same
wrapper for consistency (Constitution §4.3) rather than invent a
second pattern.

**Alternatives considered.**

1. **Adopt Tolaria News' `Envelope[T]`** wholesale, wrapping `Paginated`
   Tamiyo Scroll responses the same way.
2. **New dedicated `Paginated[T]`** (`items`, `total`, `page`,
   `per_page`), added to the shared `responses_base.py`, applied only
   to the two affected endpoints.

**Trade-offs.** `Envelope`'s `Page` is cursor pagination
(`next_cursor`, `limit`) — built for infinite-scroll over Tolaria
News' public, staleness-sensitive tournament data. A page-size
selector (10/25/50) is page-number pagination: the user expects a
total count and the ability to jump between pages, neither of which a
cursor token supports. `Envelope`'s `Meta` (`generated_at`,
`source_synced_at`) also has no Tamiyo Scroll equivalent — matches and
card tests are the user's own live-written data, not scraped data with
a sync lag; forcing it in would mean dummy fields with no meaning.
Beyond the shape mismatch, treating `Envelope` as *the* Tamiyo Scroll
convention would, for consistency, eventually pull in all of Tamiyo
Scroll's ~117 route handlers and every test asserting on a bare
response body — a large, unscoped migration in service of two
endpoints whose pagination need doesn't fit the wrapper being adopted.
Separately, `GET /matches` builds its result via
`services/tamiyo_scroll/sharing_merge.py`'s `build_merged_view`, which
merges the owner's own rows with name-matched shared rows **in
Python**, not SQL — there is no query to attach `LIMIT`/`OFFSET` to.
This affects the implementation (pagination is a slice of the
already-sorted merged list, acceptable at personal-tracker scale) but
not the choice between the two wrapper shapes above.

**Decision.** Option 2, per the user. `Paginated[T]` is added to
`app/schemas/responses_base.py` and used only by `GET /matches` and
`GET /card-tests`. `Envelope` remains Tolaria-News-specific, per its
original divergence rationale already documented in
`responses_tolaria_news.py`'s module docstring — this ADR reaffirms
rather than revisits that boundary.

Page size is **not** a per-request query parameter or a
`localStorage`-only client preference: it is persisted server-side as
a `ts_user_settings` field, one independent setting per list ("Journal
page size" and "Card Tests page size" are separate, per the user —
changing one never affects the other), editable only from the Account
Settings popup (`AccountSettingsDialog.tsx`), the same place
`data_shared` / `receive_shared_data` / `active_personal_deck_id`
already live. This is consistent with Option D of
`docs/content/back/barrins_api/bff/tamiyo_scroll.md` ("dedicated
`ts_user_settings` table for the BFF domain, `users` stays a pure
identity model") — page size is exactly this kind of Tamiyo-Scroll-only
preference, not a Barrin-wide concept.

**Consequences.**

- `ts_user_settings` gains two new columns (working names:
  `journal_page_size`, `card_tests_page_size`), each constrained to
  {10, 25, 50}, with a default — needs a migration.
- `ResponseUserSettings` / `UserSettingsUpdate`
  (`schemas/responses_tamiyo_scroll.py` / `schemas/tamiyo_scroll.py`)
  and `PATCH /me/settings` (`api/tamiyo_scroll/settings.py`) gain the
  two fields, validated against the allowed set the same way
  `receive_shared_data` is validated against `data_shared`.
- `GET /matches` and `GET /card-tests` gain a `page` (page number)
  query param only — `per_page` is read server-side from the caller's
  stored setting, never accepted as a request override, since the
  settings popup is the only place page size changes.
- `AccountSettingsDialog.tsx` gains two page-size selectors (one per
  list) alongside the existing sharing toggles and display-preference
  switches.
- Not yet implemented — this ADR precedes the implementation. Once
  shipped, `docs/content/back/barrins_api/bff/tamiyo_scroll.md`'s
  route map (already flagged in its own 2026-08-02 gap note as
  out of date past v1) and `responses_base.py` should reflect
  `Paginated[T]` alongside `BaseResponse`.

## ADR-15: Karn Tablets observability — job health and Jupyter Lab

**Context.** ADR-13 settled Karn Tablets as a push-based scheduled job
(systemd timer mirroring `scripture_scraper`, no inbound API, no
persistent process). That leaves two related but unresolved day-2
operability questions, neither part of the pipeline's core scope
(ADR-6): how anyone knows whether a given clustering run succeeded, and
how anyone explores the underlying data/clustering output interactively,
beyond the fixed views the Tolaria News BFF and S6 admin dashboard
surface (ADR-13).

**Alternatives considered — run-health monitoring.**

1. Add a HetrixTools tracker for Karn Tablets, matching the uptime
   monitoring already used for `barrins_api` (ADR-4).
2. Have Karn Tablets expose a small inbound HTTP status/health endpoint
   for something else to poll.
3. Scheduled-job health only: state is checked the same way
   `scripture_scraper`'s already is today (`systemctl status`/
   `journalctl` on the VPS) — no new tracker, no new endpoint.

**Trade-offs.** Option 1 would consume a HetrixTools slot on a free tier
already fully used by `barrins_api` prod+staging (ADR-4) — a paid tier or
dropping an existing tracker, for a periodic batch job with no
user-facing uptime property to begin with (HetrixTools checks HTTP
uptime; a scheduled job's failure mode is "did the run exit 0", not "is
it up right now" — the same mismatch D2/F1 already noted for
`scripture_scraper`). Option 2 reintroduces exactly the inbound network
exposure ADR-13 deliberately eliminated ("needs no inbound network
exposure at all"), for a monitoring shape that still wouldn't fit a
periodic job well. Option 3 adds nothing new architecturally and matches
existing precedent exactly, but inherits the same known gap already
tracked for `scripture_scraper`: no automated failure notification yet,
manual inspection only.

**Decision.** Option 3. Karn Tablets' scheduled-job health is checked the
same way `scripture_scraper`'s is today — manual `systemctl status`/
`journalctl` on the VPS. This folds Karn Tablets into the same,
already-open D2/F1 backlog item (automated scheduled-job failure
notification) rather than solving it separately per job. No HetrixTools
tracker is added for Karn Tablets; no inbound status endpoint is built.

**Alternatives considered — Jupyter Lab's purpose and scope.**

1. Jupyter Lab is part of the production pipeline: notebooks are how
   clustering actually runs, or how it's monitored, in production.
2. Jupyter Lab is an ops/dev exploration tool only: a workbench,
   restricted to `admin` and `ml_developer` account holders, for
   interactively poking at `bs_*`/`kt_*` data and clustering behavior.
   The pipeline itself stays exactly what T6 scaffolded — a CLI batch job
   (`uv run karn-tablets ...`), no notebooks anywhere in the execution
   path.

**Trade-offs.** Option 1 would put an interactive, hand-run artifact
inside the actual clustering execution path, cutting against Constitution
§45.2 (reproducible pipelines, every result carries source
data/version/model info) — a notebook run by hand doesn't reproduce the
same way a scheduled CLI job does. Option 2 keeps §45.2 fully intact
(the pipeline `apps/karn_tablets` already scaffolds is untouched) and
scopes Jupyter to what it's actually good at: ad-hoc exploration of data
already produced by the real pipeline.

**Decision.** Option 2. Jupyter Lab, reachable at
`karn-jupyter.barrins-codex.org`, is an interactive exploration tool over
Karn Tablets' data, restricted to `admin` and `ml_developer` account
holders — never part of the scheduled clustering job itself, which
remains the CLI pipeline `apps/karn_tablets` already scaffolds.

The authorization boundary reuses `auth_roles.md`'s existing role
hierarchy rather than inventing a new one: `ml_developer` (level 3) and
`admin` (level 4) are already-defined roles, and `MlDeveloperUser`
already exists as a dependency alias covering exactly this pair (`admin
⊃ ml_developer` in the hierarchy, so gating at the `ml_developer` level
already admits admins too). No new role is created for Jupyter access.

The *technical* enforcement mechanism is deliberately left open here
rather than prescribed: the closest existing infra precedent is pgAdmin
(`ops/my-server`) — Docker, bound to `127.0.0.1` only, its own nginx
vhost with a dedicated cert, and the tool's own login as the sole access
gate, no separate allowlist layer. Whether Jupyter follows that same
shape (its own login, credentials handed out only to `admin`/
`ml_developer` account holders, same as pgAdmin's credential-sharing
model) or something that actively validates a `barrins_api` JWT/role
(an auth-checking reverse-proxy layer, heavier to build) is not decided
here — no ops role for Jupyter exists yet, and picking the concrete
shape is deferred to the T8-style implementation task that actually
builds it, the same way ADR-13 deferred Karn Tablets' own deployment
shape until it was concretely needed.

**Consequences.**

- No new HetrixTools tracker, no new inbound endpoint on Karn Tablets;
  Karn Tablets' run-health is added to D2/F1's existing scope
  (automated scheduled-job failure notification, still open) rather than
  given its own bespoke solution.
- `apps/karn_tablets`' pipeline code and its §45.2 reproducibility
  properties are unaffected by this decision — Jupyter is additive
  tooling on top, not a second execution path.
- A new subdomain, `karn-jupyter.barrins-codex.org`, needs a
  `register_ssl` entry and a new `ops/my-server` role plus nginx vhost
  before it can go live — not yet built. Until that implementation task
  picks and builds an enforcement mechanism, "`admin`/`ml_developer`
  only" is a stated requirement, not yet an enforced access boundary.
- Follows the same pattern as ADR-1/ADR-5/ADR-13's `KARN_INGEST_TOKEN`,
  `SCRIPTURE_INGEST_TOKEN`, etc.: whatever auth Jupyter ends up using
  (its own token/password, per the pgAdmin precedent) is a secret,
  handled per ADR-1 — never committed, documented in
  `ops/my-server/secrets/README.md` once it exists.
