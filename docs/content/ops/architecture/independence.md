# Infrastructure Independence — why `ops/my-server` lives here

Constitution §26.1 requires the ecosystem to be deployable independently
per component, with a deployment of one component never requiring
rebuilding or restarting unrelated ones. This page explains how
`ops/my-server/` (the Ansible deployment for the project's VPS) satisfies
that, and why it moved into this monorepo instead of staying in a
dedicated `myserver` repository.

## One playbook per application

Every application gets exactly one playbook under `ops/my-server/`:

| Application | Playbook |
| --- | --- |
| `barrins_api` (shared backend) | `barrins_api.yml` |
| Tamiyo Scroll (frontend) | `tamiyo_scroll.yml` |
| Tolaria News (frontend) | `tolaria.yml` (a known, documented exception — see below) |

Running `tamiyo_scroll.yml` never touches `barrins_api`'s systemd service
or nginx vhost, and vice versa. This is enforced structurally, not by
convention: `tamiyo_scroll.yml` simply contains no `fastapi-backend` role
invocation at all. `tolaria.yml` still embeds its own copy of the backend
role block (a leftover from before this split — both converge on the same
systemd unit/nginx vhost as `barrins_api.yml`'s, and every role invocation
is idempotent, so running either or both is safe) — see
`ops/my-server/README.md`'s "Multiple frontends sharing one backend" for
the full rationale and the open item to migrate it.

## Why this moved from a separate `myserver` repo into this monorepo

**Context.** The Ansible deployment originally lived in its own repository
(`Spigushe/myserver`), developed independently of the application code it
deployed.

**Alternatives considered.**

1. Keep `myserver` as a separate repository, cross-referenced from here.
2. Move the Ansible content into this monorepo, under `ops/my-server/`.
3. Split further — one deploy repo per application.

**Trade-offs.**

- Option 1 (status quo) meant infrastructure and application code evolved
  on separate timelines, in separate PRs, often reviewed by different
  people, with no single commit capturing "this app change requires this
  infra change." It also meant a second repo, a second clone, a second set
  of access permissions, and a second place documentation could drift from
  reality.
- Option 3 (per-app deploy repos) would maximize independence but adds
  repos for no real benefit here — this is a single small team operating a
  single VPS, not multiple teams needing hard access boundaries between
  infra for different apps.
- Option 2 (this monorepo) keeps `ops/my-server/` a self-contained Ansible
  project (its own `ansible.cfg`, `hosts.ini`, `roles/`, still invoked
  exactly the same way, `cd ops/my-server && ansible-playbook ...`) while
  giving it the same commit history, PR review, and documentation site as
  the applications it deploys. Deployment independence (one playbook per
  app, no shared blast radius) is preserved regardless of which repo the
  playbooks live in — it was never about repo boundaries, only about what
  each playbook touches.

**Decision.** Option 2: `ops/my-server/` inside this monorepo. The
previous `myserver` repository is deprecated (see its README) and is no
longer used for new work.

**Consequences.**

- Infra changes and the app changes that require them can land in the same
  commit/PR, reviewed together.
- `ops/my-server/` still works as a standalone Ansible project — nothing
  about how you invoke it changed, only where it lives.
- The `myserver` repository's git history (playbook evolution, past
  incidents, prior domain-naming decisions) remains available there for
  reference but should not receive new commits.
- Anyone with monorepo access can now see and review infrastructure
  changes, which is a net widening of visibility — acceptable for a
  single-team project, but worth revisiting if the team or access model
  changes.

## See also

- [`decisions.md`](decisions.md) — the secrets-management and release-tag
  decision records.
- [`../deployment/index.md`](../deployment/index.md) — how to actually run
  these playbooks.
- `ops/my-server/README.md` — the operational reference (commands,
  variables, port ledger).
