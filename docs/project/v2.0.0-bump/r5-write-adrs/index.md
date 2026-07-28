# R5. Write the ADRs this release's decisions require

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/ops/architecture/decisions.md` | ADR-5 onward |
| **Initial date** | 2026-07-27 | / |
| **Status** | ✅ Merged into `proj/v2.0.0-bump` via [PR #24](https://github.com/Spigushe/barrins-project/pull/24) (squash) | / |
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
All eight (I1–I8) are resolved as of 2026-07-27 (I7, Tolaria News BFF
access restriction, was the last, closed same day) — this item was
unblocked and started the same day.

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

- [x] Wait for I7 to actually be decided — resolved 2026-07-27 (Option 4,
      §1.9). I1–I6 and I8 were already resolved.
- [x] Write each ADR, reusing the Context/Alternatives/Trade-offs text
      already drafted in `v2.0.0-bump/index.md` §1 rather than
      re-deriving it — ADR-5 (Barrin's Scripture: repo/DB-access/archive,
      §1.1–1.3), ADR-6 (Karn Tablets scope, §1.4), ADR-7 (identity delay,
      §1.5), ADR-8 (team model, §1.6), ADR-9 (metrics dashboard split,
      §1.7), ADR-10 (Tolaria News BFF access, §1.9), ADR-11 (WeasyPrint,
      I8/S5) — all added to
      [`decisions.md`](../../../content/ops/architecture/decisions.md) on
      branch `r5-write-adrs` (off `proj/v2.0.0-bump`).
- [x] Open a PR merging `r5-write-adrs` into `proj/v2.0.0-bump` —
      [PR #24](https://github.com/Spigushe/barrins-project/pull/24),
      branch protection satisfied (branch requires PRs per F9). CI green
      (`ci-required`, `docs` both pass), `mergeStateStatus: CLEAN`. A
      cspell-allowlist follow-up commit (`8b1d61d`) was needed to get
      `docs` green — 17 flagged words (technical terms, French, and the
      deliberate `consitution-amendment.md` typo), none real misspellings.
- [x] Get PR #24 merged into `proj/v2.0.0-bump` — no review required
      (`required_approving_review_count: 0` on the `proj/*` ruleset), CI
      green, squash-merged.
- [x] Every ADR now lives on `proj/v2.0.0-bump`, well **before** R1 merges
      that branch into `staging` — do not write or merge any ADR directly
      on `main` after the fact (the §3.1 mistake). R5 is complete; R1 can
      proceed once the rest of Groups T/S/F/D land.

## UAT (manual)

- [X] N/A — documentation review.

## Non-regression tests

- N/A (documentation item).
