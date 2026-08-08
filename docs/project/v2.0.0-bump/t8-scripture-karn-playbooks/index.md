# T8. Deployment playbooks for Barrin's Scripture and Karn Tablets

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `ops/my-server/barrins_scripture.yml` (**already exists**, built during T1 — see note below), Karn Tablets playbook (shape depends on T6) | / |
| **Initial date** | / | Not started |
| **Status** | 🟡 **Barrin's Scripture half done (2026-08-08); still blocked on T6 for Karn Tablets** — `barrins_scripture.yml`/`scripture_scraper` shipped during T1, ahead of D1. D1 is done (2026-08-03). T3 landed (2026-08-07), unblocking the two tasks this page had deferred on it: the sweep now runs on its own `barrins_scripture_sweep.service`/`.timer` (every 6h, independent of the daily scrape timer), and `SCRIPTURE_INGEST_TOKEN` is documented in `ops/my-server/secrets/` (`secrets/barrins_api/{production,staging}.env.example` and the new `secrets/barrins_scripture/{staging,production}.env.example`). `barrins_scripture.yml` also gained a `deploy_env` var (default `staging`) so the sweep can be validated against the staging `barrins_api` before a production cutover | / |
| **Source** | Request item 4; `v2.0.0-bump/index.md` §1's Group D | / |
| **Dependency** | T1 (done), T6 (open), D1 (✅ done 2026-08-03) | / |

---

## Context

**Correction (2026-08-03, found while starting D1)**: `ops/my-server/
barrins_scripture.yml` and the `scripture_scraper` role **already exist**
— built during T1, before this item or D1 started. This page previously
assumed both were still to be written; they aren't. What remains for the
Barrin's Scripture half of this item is narrower than originally scoped:
confirm the existing role against
[D1's new checklist](../../../content/ops/deployment/new-service-checklist.md)
(now done) and close its own documented "Not automated yet" gaps (the
JSON archive isn't a git submodule; no failure-notification wiring) —
not write the playbook from scratch.

Existing playbooks only cover two service *shapes*: `fastapi_backend`
(a long-running web API) and `react_frontend` (a static SPA build).
Barrin's Scripture is neither — it's a **scheduled job**, closer in
spirit to `postgres_backup`'s systemd-timer pattern
(`deployment/database.md`) than to either existing role. This is exactly
the shape `scripture_scraper` already implements (see above).

**Karn Tablets is no longer deferred** (§1.4, resolved 2026-07-26): it
ships real clustering/aggregation functionality in v2.0.0, not a
placeholder. Its playbook is still **blocked on T6**, but for an
ordinary dependency reason (T6 hasn't decided its consumption surface —
a periodic job with no API, vs. a periodic job plus a small results-
serving API), not because there's no code to deploy. Once T6 resolves
that, this item likely needs a third service shape alongside Barrin's
Scripture's scheduled-job pattern — a scheduled job that also exposes a
narrow read API, if the consumption-surface decision lands there.

## Done statement

- `ops/my-server/barrins_scripture.yml` exists, following D1's template,
  respecting Constitution §26.1 ("one application, one playbook" — this
  playbook touches nothing belonging to `barrins_api`/`tamiyo_scroll`/
  `tolaria_news`). **Already true** — it shipped during T1; remaining
  work is confirming it against D1's checklist and closing its own
  "Not automated yet" gaps, not writing it.
- Structured per Constitution §37's Preparation/Deployment/Validation/
  Rollback shape, adapted for a scheduled job rather than a service
  (e.g. "Validation" checks the last scheduled run's log/exit code
  instead of an HTTP health check). **Done** — extended to cover the
  sweep's own `.service`/`.timer` pair (2026-08-08), same pattern as the
  scrape's.
- A Karn Tablets playbook exists once T6's consumption-surface decision
  lands, following the same scheduled-job pattern (plus a minimal API
  role if T6 needs one) — no longer explicitly out of scope, but not
  written until T6 unblocks it. **Still open.**

## Tasks

- [x] Wait on D1's template — done 2026-08-03, see
      [`new-service-checklist.md`](../../../content/ops/deployment/new-service-checklist.md).
- [x] Adapt the `postgres_backup` role's systemd-timer pattern for a
      Python scheduled job — **already done during T1**
      (`scripture_scraper`), found while starting D1. `mtg_scraper`'s
      GitHub Actions schedule is retired per T1's own plan once this is
      proven equivalent (T1's remaining task, not this one's).
- [x] Walk `scripture_scraper`/`barrins_scripture.yml` against D1's
      checklist section by section (Preparation/Deployment/Validation/
      Rollback, plus the six Step-0 questions) — **done 2026-08-05**.
      Step 0's trigger/HTTP-surface/release-branch questions (0.1, 0.2,
      0.6) and Preparation/Deployment were already answered correctly in
      code and/or the playbook's own comments. Step 0.4 (Rollback) and
      Step 0.5 (data ownership/backup) had real answers, but scattered
      across T1/T3/this page's prose rather than written into the role's
      own docs, which is where the checklist says they belong — closed
      by adding explicit **Validation**, **Rollback**, and **Data
      ownership & backup** sections to
      [`scripture_scraper/README.md`](../../../../ops/my-server/roles/scripture_scraper/README.md),
      including an idempotency note confirmed against the actual code
      (`save_tournament_scrape`'s deterministic, URL-derived filenames —
      a rerun overwrites in place, never duplicates). No gap required a
      code/behavior change, only documentation.
- [ ] Close `scripture_scraper`'s remaining documented gaps: the JSON
      archive isn't a git submodule yet (T1's own tracked task — not
      this item's to do); no failure-notification wiring. **Decided
      (2026-08-07, user's call)**: option (a) — wait for
      [D2](../d2-monitoring-extension/index.md)/F1 rather than build a
      scripture-only stopgap. No implementation here until D2 lands its
      generic scheduled-job notification mechanism (itself blocked on
      F1, the HetrixTools-or-successor decision); `systemctl status`/
      `journalctl -u barrins_scripture.service` remains how a failed run
      is surfaced in the meantime.
- [x] Schedule the sweep (`apps/barrins_scripture/barrins_scripture/
      sweep.py`, T3) on its own timer tick, independent of the scrape
      schedule. **Done (2026-08-08)**: `scripture_scraper` role now
      templates `barrins_scripture_sweep.service`/`.timer` (every 6
      hours, `RandomizedDelaySec=900`, `Persistent=true`) alongside the
      existing scrape pair — same role, same checkout/venv, no new role
      (the sweep has no clone/dependency-install needs of its own).
- [x] Document the new secret(s) T3/D3 introduce (the
      Barrin's-Scripture-to-`barrins_api` service credential). **Done
      (2026-08-08)**: `SCRIPTURE_INGEST_TOKEN` added to
      `secrets/barrins_api/production.env.example` and `staging.env.example`
      (previously missing there despite already being in
      `apps/barrins_api/.env.example`), plus a new
      `secrets/barrins_scripture/production.env.example` mirroring
      `apps/barrins_scripture/.env.example`. Decided: duplicate the value
      across both apps' secrets files rather than centralize it like
      `secrets/github/token.txt` — kept consistent with the existing
      per-app `secrets/<app>/*.env` convention; both copies are
      documented as needing to match, with no automated sync. The sweep
      reads it from a local `.env` deployed to the checkout
      (`scripture_scraper_env_file`, mirroring `fastapi_backend_env_file`'s
      "use it if available" pattern) rather than templated
      `Environment=` lines, since `sweep.py` reads plain env vars with no
      dotenv-loading of its own, and this avoids putting the secret
      directly into `/etc/systemd/system/*.service`.
- [x] Let the sweep be validated against staging before pointing it at
      production. **Done (2026-08-08)**: `barrins_scripture.yml` gained a
      `deploy_env` var (default `staging`), independent of
      `scripture_scraper_git_branch`/`deploy_branch` — so e.g. main-branch
      code can still be validated against the staging API as an
      intermediate step. `scripture_scraper_env_file` now resolves to
      `secrets/barrins_scripture/{{ deploy_env }}.env`; added
      `secrets/barrins_scripture/staging.env.example` alongside the
      existing production one. Cutting over to production means passing
      both `-e deploy_branch=main -e deploy_env=production` together —
      the default never posts to production by accident.
- [ ] Once T6 resolves its consumption-surface question, write Karn
      Tablets' playbook: a scheduled job for the clustering run, plus a
      minimal API role only if T6 needs one exposed. **Out of
      Barrin's-Scripture scope** — Karn Tablets is a different
      application; not touched without the user's go-ahead.

## UAT (manual)

- [ ] A scheduled run completes end-to-end on staging: scrape → JSON
      archive → ingestion. **Now fully wired** (scrape → archive via
      `scripture_scraper`, archive → ingestion via
      `barrins_scripture_sweep.timer`) but **not yet exercised against a
      real deploy** — same open UAT step T3's own page lists (deploying
      `secrets/barrins_scripture/staging.env`, the default `deploy_env`,
      confirming a real 6h tick ingests successfully against the staging
      `barrins_api`, confirming a `barrins_api`-down tick fails cleanly
      and the next tick catches up). Only after that passes does cutting
      over to `secrets/barrins_scripture/production.env`
      (`-e deploy_branch=main -e deploy_env=production`) make sense.
- [ ] Once written, Karn Tablets' scheduled clustering run completes
      end-to-end on staging and its output is reachable however T6
      decided it should be consumed.

## Non-regression tests

- `ansible-lint ops/my-server` stays clean (the existing `ops` CI job
  requirement, Constitution §26.4).
