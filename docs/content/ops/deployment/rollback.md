# Rollback

Constitution §37.1/§37.2 require a documented rollback procedure for both
backend and frontend deployments. This page is that procedure.

## The mechanism: redeploy an older release tag

Every production deploy in `ops/my-server/` targets a GitHub release tag
(ADR-2 in [`../architecture/decisions.md`](../architecture/decisions.md)).
Rolling back means telling the playbook to deploy an older tag instead of
"latest":

```bash
# Backend
ansible-playbook barrins_api.yml -e fb_release_tag=<previous-tag>

# Frontend
ansible-playbook tamiyo_scroll.yml -e rf_release_tag=<previous-tag>
ansible-playbook tolaria.yml -e rf_release_tag=<previous-tag> -e fb_release_tag=<previous-tag>
```

Find the previous tag with `git tag --sort=-creatordate | head` in the
application repo, or from the GitHub Releases page. This re-clones the
repo at that tag, reinstalls dependencies, rebuilds (frontend) or
restarts the service (backend) — the same idempotent path as a forward
deploy, just pointed backward.

## Frontend rollback: that's it

A frontend has no database and no long-running process holding state —
rolling back is just "serve the older build." No further steps.

## Backend rollback: code and database are separate

Rolling back `barrins_api`'s code does **not** roll back its database.
Before rolling back a release that included an Alembic migration, decide
explicitly what happens to the schema:

1. **The migration is backward-compatible** (the old code can run against
   the new schema — e.g. a migration only added a nullable column or a new
   table) — code rollback alone is safe. Leave the database as-is.
2. **The migration is not backward-compatible** (e.g. it renamed or
   dropped a column the old code still reads/writes) — code rollback alone
   will break. Either:
   - write and apply a compensating "down" migration
     (`alembic downgrade <revision>`) before or as part of the rollback, or
   - accept the incompatibility is unresolvable without a schema-aware fix
     and roll forward with a hotfix instead of rolling back.

Constitution §31.3 already requires evaluating backward compatibility and
testing before *any* migration — the same discipline applies in reverse
when deciding whether a rollback is safe. When in doubt, restore from a
database backup taken before the migration ran (Constitution §36 requires
these backups exist and be tested — see the open item in
[`../operations/index.md`](../operations/index.md) about the current state
of that requirement).

## Rollback checklist

- [ ] Identify the last known-good release tag.
- [ ] For a backend rollback: check whether the release being rolled back
      included a migration, and if so, whether it's backward-compatible.
- [ ] Run the playbook with `-e fb_release_tag=<tag>` /
      `-e rf_release_tag=<tag>`.
- [ ] Validate (see the "Validation" section of
      [`backend.md`](backend.md) / [`frontend.md`](frontend.md)).
- [ ] If the database needs a compensating action, take it and re-validate.
- [ ] Communicate the rollback and its cause — this is not automated or
      logged anywhere beyond the deploy itself.

## See also

- [`backend.md`](backend.md), [`frontend.md`](frontend.md) — normal
  deployment procedures.
- [`../architecture/decisions.md`](../architecture/decisions.md) — ADR-2,
  why release-tag deploys work this way.
