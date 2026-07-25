# B7. Document the decision and commit

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/ops/architecture/decisions.md` | / |
| **Initial date** | 2026-07-23 | / |
| **Status** | ✅ Implemented | as ADR-4, not ADR-3 (see comment below) |
| **Source** | Release checklist | document the decisions made across this release |
| **Dependency** | B6 | documents the decisions made through production deploy |

---

## Tasks

- [X] Add ADR-4 (not ADR-3 — that slot was already taken by the
      production-email ADR added in the v1.0.0 squash-merge, #20/ba54ef4)
      to `docs/content/ops/architecture/decisions.md` — "First
      production release: backup-before-go-live, monitoring, and
      Moxfield import" — Context/Alternatives/Trade-offs/Decision/
      Consequences.
- [X] One commit per logical task (§18).

## Done statement

ADR-4 written and merged.

## UAT (manual)

- [X] Read ADR-4; confirm it accurately reflects the decisions actually
      made (external monitoring choice, backup-gating the release,
      Moxfield secret handling).

## Non-regression tests

None (docs-only).
