# R4. Deploy from tag (production)

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | Production VPS (`146.59.146.57`) | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — every new service's playbook must exist first | / |
| **Source** | Mirrors v1.0.0's B6 | / |
| **Dependency** | R3, D1/D2 (new services need their playbooks and monitoring *before* first deploy, same gating principle ADR-4 used for `postgres_backup`) | / |

---

## Context

v1.0.0's B6 depended on B1 (`postgres_backup`) for exactly this reason:
don't apply a first production migration/deploy without the operational
safety net already in place. The same principle applies here for Tolaria
News' first production deploy — it needs its playbook (T8) and monitoring
(D2) before that happens.

**Barrin's Scripture is a different case as of ADR-12** (2026-08-10,
`docs/content/ops/architecture/decisions.md`): its scrape+sweep scheduling
runs on GitHub Actions (`.github/workflows/scripture-scrape.yml`), not the
VPS — mtgo.com blocks the VPS's static outbound IP. There is no VPS
playbook-gated "first deploy" for it to wait on; `ops/my-server/roles/
scripture_scraper/` stays dormant, kept only as a rollback path. R4's
"Deploy/enable Barrin's Scripture" task below is satisfied by confirming
the GitHub Actions workflow's repository secrets are set for production
(`SCRIPTURE_INGEST_TOKEN`, `ARCHIVE_PUSH_TOKEN`), not by running any
playbook.

## Done statement

- Every in-scope new service is deployed from the `v2.0.0` tag to
  production, each via its own playbook (Constitution §26.1), each with
  monitoring live before or immediately after first deploy.
- `barrins_api`/`tamiyo_scroll` are redeployed from the same tag
  (standard release cadence, not a new gate).

## Tasks

- [ ] Deploy `barrins_api` from the tag (as in every prior release).
- [ ] Deploy `tamiyo_scroll` from the tag.
- [ ] Deploy Tolaria News frontend (first-ever real deploy, if T5
      shipped this release) via the already-existing `tolaria_news.yml`.
- [ ] Confirm Barrin's Scripture's GitHub Actions repository secrets
      (`SCRIPTURE_INGEST_TOKEN`, `ARCHIVE_PUSH_TOKEN`) are set for
      production — no playbook to run, see Context (ADR-12).
- [ ] Immediately backport this item's "done" confirmation to `staging`
      once written on `main` (§3.1) — same reasoning as R2/R3's
      equivalent tasks.

## UAT (manual)

- [ ] Exercise a real user flow through each deployed frontend.
- [ ] Confirm HetrixTools (or successor) shows every expected tracker
      reporting `up`.

## Non-regression tests

- N/A (deployment step) — covered by each item's own non-regression
  tests, already run before this point.
