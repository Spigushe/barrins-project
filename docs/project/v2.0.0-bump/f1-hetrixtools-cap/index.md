# F1. HetrixTools free-tier tracker cap

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `ops/my-server/`, HetrixTools account | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — should fix before v2.0.0 ships, not blocking | / |
| **Source** | `docs/content/ops/roadmap.md` (carried from v1.0.0), ADR-4 | / |
| **Dependency** | None | Feeds D2 |

---

## Context

ADR-4 chose HetrixTools' free tier (2-tracker cap) for uptime/cert
monitoring, already fully used by `barrins_api` prod + staging;
`tamiyo_scroll` isn't separately monitored. v2.0.0 adds up to two more
deployable services (Tolaria News frontend, Barrin's Scripture), making
the existing gap worse.

## Done statement

- A decision made (paid tier vs. alternate provider vs. accept the gap
  a while longer) and, if changed, implemented — new trackers covering
  at minimum the new production services once they deploy.

## Tasks

- [ ] Check HetrixTools' paid-tier pricing against the number of
      trackers this release actually needs (up to 2 new prod endpoints
      + their staging equivalents).
- [ ] Decide: upgrade, or accept degraded coverage a while longer
      (escalate either way, per ADR-4's own reasoning style).
- [ ] If upgrading: add the new trackers during each new service's first
      production deploy (D2 depends on this).

## UAT (manual)

- [ ] Each new production service has a live tracker reporting `up`
      within HetrixTools' dashboard after its first deploy.

## Non-regression tests

- N/A (infrastructure/ops item, no application code).
