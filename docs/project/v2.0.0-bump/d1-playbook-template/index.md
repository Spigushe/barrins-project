# D1. Deployment playbook template for new service shapes

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `ops/my-server/` (new documentation, not a new role by itself) | / |
| **Initial date** | 2026-08-03 | Started and finished same day — no open sub-decisions blocked it |
| **Status** | ✅ **Done (2026-08-03)** | / |
| **Source** | Request item 4 | / |
| **Dependency** | None to start (a template can be written generically); I2/I4 inform which concrete shapes are needed first | Blocks T8, D2 |

---

## Context

Today's only two service shapes are `fastapi_backend` (long-running web
API) and `react_frontend` (static SPA build). Barrin's Scripture (a
scheduled job) and Karn Tablets (an ML service, whenever scoped) are
both new shapes. Request item 4 asks specifically for a playbook
*template/checklist* — not a finished playbook for a service that isn't
designed yet.

**Found while starting this item (2026-08-03)**: T1 already built a
concrete instance of the scheduled-job shape this item was meant to
templatize — `ops/my-server/roles/scripture_scraper/` +
`ops/my-server/barrins_scripture.yml`, built ahead of this template
existing. It's used below as a worked precedent (alongside
`postgres_backup`) rather than duplicated; T8's remaining scope narrows
to confirming/adjusting it against this template and still writing Karn
Tablets' own playbook once T6 lands — see T8's page.

## Done statement

- A written template
  ([`docs/content/ops/deployment/new-service-checklist.md`](../../../content/ops/deployment/new-service-checklist.md))
  generalizing Constitution §26.1 ("one application, one playbook") and
  §37 (Preparation/Deployment/Validation/Rollback) for a service that is
  neither a persistent web API nor a static frontend build — e.g. a
  scheduled job, a background worker, or an ML inference service.
- The template explicitly calls out the questions every new service
  needs answered before its playbook can be written: what triggers a
  run (cron/timer vs. GitHub Actions vs. on-demand), what "Validation"
  means without an HTTP health check, what "Rollback" means for a
  non-versioned-deployment artifact (e.g. a model checkpoint).

## Tasks

- [x] Draft the template, using `postgres_backup`'s systemd-timer
      pattern and `fastapi_backend`/`react_frontend`'s existing
      Preparation/Deployment/Validation/Rollback structure as the two
      closest precedents. **Also used `scripture_scraper`** (found
      already built during T1, see the Context note above) as a third,
      concrete application-level precedent.
- [x] Cross-check it against `ansible-lint`'s existing standards
      (Constitution §26.4) — the template's "Ansible coding standards
      still apply" section cross-references §26.4 directly rather than
      restating it, so any role built from it starts clean.
- [ ] Have T8 be its first real consumer (Barrin's Scripture's playbook)
      — not done here; T8 still needs to either confirm
      `scripture_scraper` already satisfies this template or adjust it,
      and to write Karn Tablets' playbook once T6 lands.

## UAT (manual)

- [ ] T8's playbook, written by following this template, passes
      `ansible-lint ops/my-server` on the first attempt (or close to it)
      — a rough proxy for "the template actually helps." **Still open**:
      this needs T8 itself to run (retroactively against
      `scripture_scraper`, and freshly for Karn Tablets).

## Non-regression tests

- N/A (documentation item).
