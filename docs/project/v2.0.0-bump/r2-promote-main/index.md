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

**Added 2026-07-26 (§3.1)**: whatever confirms this step "done" — a
docs commit checking off this item — must land on **both** `main` and
`staging`, not just `main`. v1.0.0's equivalent confirmation
(`c4949d8`, "confirm B4 merged") was written directly on `main` only,
one of the five post-squash commits that needed two later reconciliation
PRs (`6821380`, `9fa40bf`) to fix.

## Tasks

- [ ] Promote `staging` → `main` (fast-forward or merge, matching
      whatever v1.0.0 actually did).
- [ ] Immediately backport this item's "done" confirmation to `staging`
      (a small follow-up commit/PR) rather than leaving it only on
      `main` — don't let it accumulate the way v1.0.0's did.

## UAT (manual)

- [ ] `main`'s HEAD matches `staging`'s at promotion time.

## Non-regression tests

- N/A (git operation, not code).
