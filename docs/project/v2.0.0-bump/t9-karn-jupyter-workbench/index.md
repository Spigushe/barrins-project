# T9. Karn Tablets Jupyter Lab workbench (`karn-jupyter.barrins-codex.org`)

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | A new `ops/my-server` role + playbook, a `register_ssl` entry and nginx vhost for `karn-jupyter.barrins-codex.org`, a DNS record, and a Jupyter access secret | / |
| **Initial date** | 2026-08-28 | Split out of T8 |
| **Status** | 🔲 **Not started** — T8 (2026-08-28) deliberately shipped the scheduled clustering job only; this is the "T8-style implementation task that actually builds it" ADR-15 defers to, which had no tracking page until now | / |
| **Source** | [ADR-15](../../../content/ops/architecture/decisions.md#adr-15-karn-tablets-observability--job-health-and-jupyter-lab) — the Jupyter Lab half (the run-health half of ADR-15 is closed: folded into D2/F1, no new tracker/endpoint) | / |
| **Dependency** | T6 (done via #106 — real `bs_*`/`kt_*` data to explore), T8 (done — the read-only DB credential and shared-secret patterns to reuse), `auth_roles.md` (`ml_developer`/`admin` roles + the `MlDeveloperUser` alias already exist) | Blocks nothing further |

---

## Context

ADR-15 decided **Option 2**: Jupyter Lab is an ad-hoc *exploration* tool
over Karn Tablets' data — never part of the scheduled clustering job,
which stays the CLI batch pipeline `apps/karn_tablets` already ships (T6,
ADR-13). It is restricted to `admin` and `ml_developer` account holders,
reusing `auth_roles.md`'s existing hierarchy (`MlDeveloperUser` already
covers exactly that pair — `admin ⊃ ml_developer`). No new role is
invented for access.

ADR-15 **explicitly deferred the technical enforcement mechanism** to
this implementation task. Its stated closest precedent is `pgAdmin`
(`ops/my-server`): Docker, bound to `127.0.0.1` only, its own nginx
vhost with a dedicated cert, and the tool's own login as the sole access
gate (credentials handed out only to the right account holders, no
separate allowlist layer).

The T8 deployment (2026-08-28) built `karn_tablets.yml` + the
`karn_tablets` role as a headless daily `systemd`-timer job with **no
inbound HTTP surface**. This item adds the interactive workbench beside
it, without touching that job (Constitution §26.1 — one application, one
playbook).

## Open sub-decisions (all inherited from ADR-15's deferral)

1. **Auth enforcement mechanism.**
   - (a) **pgAdmin model** — Jupyter's own token/password login, the
     credential shared out-of-band with `admin`/`ml_developer` holders,
     no `barrins_api` involvement. Lightest; matches the existing
     precedent exactly. "`admin`/`ml_developer` only" is enforced by
     *who gets the password*, not by a live role check.
   - (b) **A live role check against an identity service** — a proxy
     (nginx `auth_request` / small sidecar) that validates a token and
     its role claim on every request. **A `barrins_api`-JWT version of
     this was built once (2026-08-15) and entirely reverted**: it
     coupled Jupyter to Tamiyo Scroll's login/session, rejected as
     incorrect cross-app coupling (see `feedback` on not coupling other
     apps' auth to Tamiyo Scroll). The user's stated direction if this
     route is taken: build it against `barrins_identity` ("Goblin
     Guide", `apps/barrins_identity` — currently a stub, delayed by
     ADR-7 until a second real consumer exists), which would make
     scoping `barrins_identity` a prerequisite of this option.
   - Given (b)'s history, **(a) is the low-friction path** unless the
     team decides Jupyter is the second consumer that finally justifies
     `barrins_identity`.
2. **Playbook boundary.** Its own `ops/my-server/karn_jupyter.yml` (the
   `postgresql_pgadmin.yml` pattern — a dedicated playbook for a shared
   piece of infra that other playbooks only reference), vs. folding it
   into `karn_tablets.yml`. §26.1 and the pgAdmin precedent both point
   at a **separate playbook**.
3. **Runtime shape.** JupyterLab in Docker bound to `127.0.0.1` (pgAdmin
   precedent) vs. a `uv` venv + a long-running `systemd` service. Docker
   keeps it isolated and matches pgAdmin.
4. **Database access for notebooks.** Reuse
   `KARN_TABLETS_DATABASE_URL_RO` (already read-only, already scoped to
   `bs_*`/`mj_*` — T8) vs. a distinct read-only credential that *also*
   grants `SELECT` on `kt_*` (the clustering output the pipeline writes
   via the ingest API — notebooks will likely want to read it back).
   The T8 role's `GRANT SELECT ON ALL TABLES` snippet already covers
   `kt_*` in practice; the question is whether Jupyter gets its own
   named role for auditability.
5. **Notebook material.** Does `apps/karn_tablets` gain a `notebooks/`
   directory and a `jupyter` dependency group, or does the Docker image
   `pip install` the published package and keep notebooks in a separate
   location/volume? ADR-15 requires the *pipeline* package to stay
   untouched by this — a dependency group is fine, a hard dependency is
   not.
6. **Environments.** One instance (pgAdmin is single-instance), or a
   staging/production split like `karn_tablets.yml`'s `deploy_env`.
   Exploration tooling probably needs only one.

## Done statement

- `karn-jupyter.barrins-codex.org` resolves, has a valid cert
  (`register_ssl`), and serves a JupyterLab instance reverse-proxied
  through nginx, bound to `127.0.0.1` on the host.
- A new `ops/my-server` role (and, per sub-decision 2, most likely a
  `karn_jupyter.yml` playbook) deploys it, following Constitution §26.1
  — it touches nothing belonging to `barrins_api` / `karn_tablets` /
  the frontends.
- Access is limited to `admin`/`ml_developer` account holders by the
  mechanism chosen in sub-decision 1, documented in the role README and
  `docs/content/ops/security/`.
- The Jupyter access secret is handled per ADR-1 — git-ignored,
  documented in `ops/my-server/secrets/README.md`, a `*.example`
  template committed.
- Notebooks can read `bs_*`/`mj_*`/`kt_*` read-only; they cannot write
  to `barrins_api`'s schema (sub-decision 4).
- `ansible-lint ops/my-server` stays clean (Constitution §26.4).
- Docs: a role page (auto-synced from the README), an entry in
  `docs/content/ops/roles/index.md` + `docs/mkdocs.yml` nav, and a
  deployment note. ADR-15's "Consequences" bullet about the subdomain
  "not yet built" updated once it is.

## Tasks

- [ ] Decide sub-decision 1 (auth enforcement) — the one ADR-15 calls
      out as the real fork. Present (a) vs (b) with trade-offs, get a
      decision before building.
- [ ] Decide sub-decisions 2–6 (playbook boundary, runtime shape, DB
      credential, notebook material, environments) — mostly precedent
      -driven, but confirm.
- [ ] Build the `ops/my-server` role + playbook + `register_ssl` +
      nginx vhost.
- [ ] Add the DNS record for `karn-jupyter.barrins-codex.org`.
- [ ] Add the access secret to `secrets/README.md` + a `*.example`.
- [ ] Docs: role page, roles index + nav, security page, update
      ADR-15's "not yet built" consequence.

## UAT (manual)

- [ ] `karn-jupyter.barrins-codex.org` loads over HTTPS with a valid
      cert; the access gate (chosen mechanism) actually blocks an
      unauthenticated / wrong-role request.
- [ ] A notebook can `SELECT` from `bs_*`/`kt_*` and **cannot**
      `INSERT`/`UPDATE` anything in `barrins_api`'s schema.
- [ ] Running `karn_tablets.yml` (the scheduled job) does not restart,
      rebuild, or otherwise touch the Jupyter service, and vice versa
      (§26.1).

## Non-regression tests

- `ansible-lint ops/my-server` stays clean (the `ops` CI job,
  Constitution §26.4).
