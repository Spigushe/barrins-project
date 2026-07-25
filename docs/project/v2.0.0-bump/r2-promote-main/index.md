# R2. Promote `staging` → `main`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `main` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started | / |
| **Source** | Mirrors v1.0.0's B4 | / |
| **Dependency** | R1 | Blocks R3 |

---

## Done statement

`main` reflects `staging` at the point R1 completed, staging-verified.

## Tasks

- [ ] Promote `staging` → `main` (fast-forward or merge, matching
      whatever v1.0.0 actually did).

## UAT (manual)

- [ ] `main`'s HEAD matches `staging`'s at promotion time.

## Non-regression tests

- N/A (git operation, not code).
