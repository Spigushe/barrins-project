# D2. Extend monitoring to new services

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | HetrixTools (or its successor per F1) | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on F1 and D1 | / |
| **Source** | Request item 4; `v2.0.0-bump/index.md` Group D | / |
| **Dependency** | F1, D1 | / |

---

## Context

Whatever F1 decides (upgrade HetrixTools, alternate provider, or accept
the gap) needs to actually cover each new service once it deploys.
Barrin's Scripture, being a scheduled job rather than a long-running
service, doesn't fit an HTTP-uptime check the way `barrins_api`'s
`/health` does — its "is it healthy" signal is closer to "did the last
scheduled run succeed," which needs a different monitoring shape.

## Done statement

- Every new production service that has an HTTP surface (Tolaria News
  frontend, once T5 ships) gets a tracker, per F1's chosen plan.
- Barrin's Scripture's monitoring answers "did the last scheduled run
  succeed," not "is an endpoint up" — exact mechanism (a dead-man's-
  switch style check, a log-based alert, or simply relying on GitHub
  Actions' own failure notifications if scraping stays on Actions per
  T8) decided alongside T8/D1.

## Tasks

- [ ] Add HTTP trackers for new frontend/backend services, per F1.
- [ ] Design and add a scheduled-job health signal for Barrin's
      Scripture, coordinated with however T8 ends up triggering runs.

## UAT (manual)

- [ ] Deliberately fail a scheduled scrape on staging (e.g. temporarily
      break a config value); confirm the new monitoring surfaces it.

## Non-regression tests

- N/A (infrastructure/ops item).
