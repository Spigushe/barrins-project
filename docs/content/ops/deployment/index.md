# Deployment

Two independent playbooks, per Constitution §37 — one per application,
each with its own Preparation / Deployment / Validation / Rollback:

- [Backend — barrins_api](backend.md)
- [Frontend — Tamiyo Scroll / Tolaria News](frontend.md)
- [Rollback](rollback.md) — the shared release-tag rollback mechanism, and
  the backend-specific database caveat.

All of these are implemented by Ansible playbooks under
`ops/my-server/` in this repository — see
[`../architecture/independence.md`](../architecture/independence.md) for
why they live here, and `ops/my-server/README.md` for the full command
reference.
