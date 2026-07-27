# R5. Write the ADRs this release's decisions require

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/ops/architecture/decisions.md` | ADR-5 onward |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — I1–I6, I8 decided; I7 still open | / |
| **Source** | Mirrors v1.0.0's B7 | / |
| **Dependency** | I1, I2, I3, I4, I5, I6, I7, I8 | **Blocks R1** (resequenced 2026-07-26 — see §3.1) |

---

## Context

v1.0.0's ADR-4 documented the backup-gating, monitoring-provider, and
Moxfield-secret-handling decisions made along the way. This release has
more open decisions than v1.0.0 did (eight, §1.1–§1.7 and §1.9 in
`v2.0.0-bump/index.md`, plus S5's PDF-library choice), each already
written in the Context/Alternatives/Trade-offs shape the constitution
requires (§16.3) — this item is where each becomes a permanent ADR once
actually resolved, not a re-derivation of the reasoning from scratch.
Seven of eight (I1–I6, I8) are resolved as of 2026-07-27; only I7
(Tolaria News BFF access restriction, §1.9) is still open.

**Resequenced 2026-07-26**: this item now **precedes R1** (it used to
just "depend on I1–I8, once resolved," with no ordering against the
merge-to-staging step). v1.0.0 wrote ADR-4 and several "done"
confirmations **after** the squash-merge to `main` (`e61d9f1`,
`11ac754`, and others), which never existed on `staging` and needed two
dedicated reconciliation PRs (`6821380`, `9fa40bf`) to fix — see §3.1.
Every ADR this item produces must be merged into `proj/v2.0.0-bump` (and
so into `staging` via R1) **before** R2 promotes to `main`, not written
directly on `main` afterward.

## Done statement

- One ADR per resolved decision (or one combined ADR covering several,
  matching ADR-4's precedent of bundling related first-release decisions
  together) — at minimum covering: Barrin's Scripture's repo location,
  DB-access model, and org-relocation (§1.1/§1.2/§1.3), Karn Tablets'
  v2.0.0 scope (§1.4), the shared-identity approach for this release
  (§1.5), the team creation model (§1.6), the metrics-dashboard v2/v3
  split (§1.7, already effectively decided — this ADR mostly formalizes
  it), Tolaria News' BFF access restriction (§1.9, once I7 resolves),
  and S5's PDF-library choice (I8, resolved 2026-07-27 — WeasyPrint,
  see S5's page for the full Context/Alternatives/Trade-offs).

## Tasks

- [ ] Wait for I7 to actually be decided (not this item's job — tracked
      in Group I). I1–I6 and I8 are already resolved.
- [ ] Write each ADR, reusing the Context/Alternatives/Trade-offs text
      already drafted in `v2.0.0-bump/index.md` §1 rather than
      re-deriving it.
- [ ] Merge every ADR into `proj/v2.0.0-bump` **before** R1 merges that
      branch into `staging` — do not write or merge any ADR directly on
      `main` after the fact (the §3.1 mistake).

## UAT (manual)

- [ ] N/A — documentation review.

## Non-regression tests

- N/A (documentation item).
