# Roadmap

Tracks each release's scope after the fact, and the concrete items
carried into the next one. Written the same way
[`operations/index.md`](operations/index.md) is: honest about gaps, not
aspirational.

## v0.0.0 → v1.0.0 (finalized)

Before this release, `origin/main` contained only the initial GitHub
Pages scaffold — no application code had ever reached production, and no
release tag existed. Getting to `v1.0.0` shipped `barrins_api` +
`tamiyo_scroll` (`staging` as it stood at cut time) and required:

| Item | What it did |
| --- | --- |
| Monitoring & `/health` | Real `GET /health` with a DB-connectivity check; external uptime and certificate-expiry monitoring via HetrixTools. |
| Sharing feature extraction | Removed the immature "sharing" feature ahead of the first public release. |
| Moxfield deck import | Import a personal deck from a public Moxfield URL; the required credential is handled as a backend-only secret, never reaching the frontend. |
| Changelog split | One `CHANGELOG.md` per sub-repo, aggregated at docs-build time into the site's Changelog section. |
| Deck-selector UX rewrite | Combobox-based deck switching in Tamiyo Scroll. |
| Root README rewrite | Presentation-first root `README.md` (no misleading pre-launch links). |
| API routes reorganization | Emerged while starting the Moxfield import work. |
| `postgres_backup` role | Daily backup plus a verified restore drill — closed the Constitution §36 blocker before the first production migration ever ran. |
| Docs site deployment playbook | `docs.yml`, staging-verified before go-live. |
| Release content finalized, merged to `staging` | |
| Promoted `staging` → `main` | |
| Tagged and cut the release | `v1.0.0` tag, GitHub Release published. |
| Deployed from tag to production | `barrins_api`, `tamiyo_scroll`, and the docs site all live from the release tag. |
| ADR-4 written | Documents the backup-gating, monitoring-provider, and Moxfield-secret-handling decisions made along the way. |

The decisions made along the way are recorded in
[ADR-1 through ADR-4](architecture/decisions.md).

**Deliberately excluded from v1.0.0:**

- `barrins_identity` — mid-implementation on `feat/barrins-identity`, not
  merged into `staging`.
- `tolaria_news` — no application code yet, only
  `apps/tolaria_news/README.md`.

## v1.0.0 → v2.0.0 (known issues to resolve)

`v2.0.0` adds **Tolaria News** as the ecosystem's second full frontend
application. Infrastructure is already wired ahead of the application
itself:

- `ops/my-server/tolaria_news.yml` exists (`react_frontend` role,
  release-tag mode in production, its own domain/vhost/SSL) but isn't
  runnable yet — there's no app code behind it.
- Domains are already reserved: `tolaria.barrins-codex.org` (production),
  `tolaria-staging.barrins-codex.org` (staging) — see
  [Frontend Deployment](deployment/frontend.md).
- [Rollback](deployment/rollback.md) is already documented for when it
  does ship.

### Blocking — Tolaria News can't ship without these

1. **No application code exists yet** for `apps/tolaria_news`. Needs a
   real implementation before `tolaria_news.yml` becomes runnable.
2. **Shared-identity decision is undecided.** Constitution §13.1 requires
   one Barrin's account usable across every application, but
   `barrins_identity` (the dedicated identity service) is still
   mid-implementation and unmerged. Before wiring Tolaria News' auth,
   decide: reuse `barrins_api`'s current auth (same pattern Tamiyo Scroll
   uses today), or wait for `barrins_identity`? Not yet decided — flag per
   Constitution §16.2 before starting that work.

### Should fix before v2.0.0 — not blocking, but compounds with a third app

1. **HetrixTools' free-tier tracker cap (2)** is already fully used by
   `barrins_api` prod + staging; `tamiyo_scroll` isn't separately
   monitored today. A third frontend competes for the same cap — revisit
   the free tier vs. a paid plan before v2.0.0 (see ADR-4,
   [Operations](operations/index.md)).
2. **Release cutting is still fully manual** (the gap ADR-2 flags) —
   tagging and creating the GitHub Release by hand doesn't scale as
   cleanly as more apps share one monorepo tag. Worth automating before
   release cadence increases.
3. **Changelog aggregation has a known cosmetic bug**, found during
   v1.0.0's changelog-split UAT: sub-repo and category headings render at
   the same level in `changelog/index.md`'s "Latest changes" section.
   Every app added to the aggregation — Tolaria News included — will show
   the same issue until `docs/hooks/sync_changelogs.py` is fixed.

### Pre-existing gaps, unrelated to Tolaria News specifically

1. **nginx security headers** (HSTS, etc.) are not implemented
   (Constitution §29.1) — see [Operations](operations/index.md)'s open
   items table.
2. **Pre-commit secret-scanning is opt-in per developer**, not enforced
   by CI or any server-side gate — see
   [Secrets Management](security/secrets.md)'s open item. Worth
   reconsidering as the contributor surface grows.

## See also

- [Decision Records](architecture/decisions.md) — ADR-1 through ADR-4.
- [Operations](operations/index.md) — current monitoring/backup/logging
  state.
- [Frontend Deployment](deployment/frontend.md) — Tamiyo Scroll / Tolaria
  News playbook reference.
