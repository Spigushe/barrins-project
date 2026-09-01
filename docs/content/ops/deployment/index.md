# Deployment

Two independent playbooks, per Constitution §37 — one per application,
each with its own Preparation / Deployment / Validation / Rollback:

- [Backend — barrins_api](backend.md)
- [Frontend — Tamiyo Scroll / Tolaria News](frontend.md)
- [Frontend — Goblin Guide](goblin-guide.md) — the standalone Barrin's
  Identity login / account SPA; calls `barrins_identity` directly in
  cookie mode (ADR-18), not `barrins_api`.
- [Identity — barrins_identity](identity.md) — a second backend
  (standalone RS256/JWKS identity service); includes the mandatory
  Brevo/OVH email-verification setup.
- [Database Administration — PostgreSQL & pgAdmin](database.md) —
  infrastructure/admin tooling, not release-tagged.
- [Docs Site](docs_site.md) — self-hosted mkdocs deployment, same
  environment/branch/tag options as the app playbooks.
- [New Service Checklist](new-service-checklist.md) — template for a
  service that is neither a backend nor a frontend (a scheduled job, a
  background worker, a small inference service).
- [Rollback](rollback.md) — the shared release-tag rollback mechanism, and
  the backend-specific database caveat.

All of these are implemented by Ansible playbooks under
`ops/my-server/` in this repository — see
[`../architecture/independence.md`](../architecture/independence.md) for
why they live here, and `ops/my-server/README.md` for the full command
reference.
