# R5. Write the ADRs this release's decisions require

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/ops/architecture/decisions.md` | ADR-5 onward |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on I1–I6 actually being decided | / |
| **Source** | Mirrors v1.0.0's B7 | / |
| **Dependency** | I1, I2, I3, I4, I5, I6 | / |

---

## Context

v1.0.0's ADR-4 documented the backup-gating, monitoring-provider, and
Moxfield-secret-handling decisions made along the way. This release has
more open decisions than v1.0.0 did (six, §1.1–§1.7 in
`v2.0.0-bump/index.md`), each already written in the
Context/Alternatives/Trade-offs shape the constitution requires
(§16.3) — this item is where each becomes a permanent ADR once actually
resolved, not a re-derivation of the reasoning from scratch.

## Done statement

- One ADR per resolved decision (or one combined ADR covering several,
  matching ADR-4's precedent of bundling related first-release decisions
  together) — at minimum covering: Barrin's Scripture's repo location
  and DB-access model (§1.1/§1.2), Karn Tablets' v2.0.0 scope (§1.4),
  the shared-identity approach for this release (§1.5), the team
  creation model (§1.6), and the metrics-dashboard v2/v3 split (§1.7,
  already effectively decided — this ADR mostly formalizes it).

## Tasks

- [ ] Wait for each of I1–I6 to actually be decided (not this item's
      job — tracked in Group I).
- [ ] Write each ADR, reusing the Context/Alternatives/Trade-offs text
      already drafted in `v2.0.0-bump/index.md` §1 rather than
      re-deriving it.

## UAT (manual)

- [ ] N/A — documentation review.

## Non-regression tests

- N/A (documentation item).
