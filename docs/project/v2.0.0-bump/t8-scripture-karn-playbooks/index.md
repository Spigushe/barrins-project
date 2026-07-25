# T8. Deployment playbooks for Barrin's Scripture and Karn Tablets

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `ops/my-server/barrins_scripture.yml` (new), Karn Tablets playbook deferred with T6 | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on T1, T6, and D1's template | / |
| **Source** | Request item 4; `v2.0.0-bump/index.md` §1's Group D | / |
| **Dependency** | T1, T6, D1 | / |

---

## Context

Existing playbooks only cover two service *shapes*: `fastapi_backend`
(a long-running web API) and `react_frontend` (a static SPA build).
Barrin's Scripture is neither — it's a **scheduled job**, closer in
spirit to `postgres_backup`'s systemd-timer pattern
(`deployment/database.md`) than to either existing role. Karn Tablets
has no code to deploy yet (T6 is placeholder-only), so its playbook is
deferred alongside it, not written now.

## Done statement

- `ops/my-server/barrins_scripture.yml` exists, following D1's template,
  respecting Constitution §26.1 ("one application, one playbook" — this
  playbook touches nothing belonging to `barrins_api`/`tamiyo_scroll`/
  `tolaria_news`).
- Structured per Constitution §37's Preparation/Deployment/Validation/
  Rollback shape, adapted for a scheduled job rather than a service
  (e.g. "Validation" checks the last scheduled run's log/exit code
  instead of an HTTP health check).
- No Karn Tablets playbook yet — explicitly out of scope until T6's
  placeholder becomes real code.

## Tasks

- [ ] Wait on D1's template.
- [ ] Adapt the `postgres_backup` role's systemd-timer pattern for a
      Python scheduled job (vs. that role's `pg_dump` cron shape) —
      or keep scraping on GitHub Actions entirely (as it runs today) and
      write only the credential/secrets wiring this playbook needs
      rather than a VPS-hosted scheduler; **not yet decided which**.
- [ ] Document the new secret(s) T3/D3 introduce (the
      Barrin's-Scripture-to-`barrins_api` service credential, if that's
      §1.2's outcome).

## UAT (manual)

- [ ] A scheduled run, whichever mechanism is chosen, completes
      end-to-end on staging: scrape → JSON archive → ingestion.

## Non-regression tests

- `ansible-lint ops/my-server` stays clean (the existing `ops` CI job
  requirement, Constitution §26.4).
