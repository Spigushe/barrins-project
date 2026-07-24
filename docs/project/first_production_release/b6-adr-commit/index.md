# B6. Document the decision and commit

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/ops/architecture/decisions.md` | / |
| **Initial date** | 2026-07-23 | / |
| **Status** | 🔲 Not started | / |
| **Source** | Release checklist | document the decisions made across this release |
| **Dependency** | B5 | documents the decisions made through production deploy |

---

## Tasks

- [ ] Add ADR-3 to `docs/content/ops/architecture/decisions.md` — "First
      production release: backup-before-go-live, monitoring, and
      Moxfield import" — Context/Alternatives/Trade-offs/Decision/
      Consequences.
- [ ] One commit per logical task (§18).

## Done statement

ADR-3 written and merged.

## UAT (manual)

- [ ] Read ADR-3; confirm it accurately reflects the decisions actually
      made (external monitoring choice, backup-gating the release,
      Moxfield secret handling).

## Non-regression tests

None (docs-only).
