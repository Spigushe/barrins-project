# RA3. Promote `staging` → `main`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `main` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started | / |
| **Source** | Mirrors R2/v1.0.0's B4, scoped to the alpha cut (§1.11) | / |
| **Dependency** | RA2 | Blocks RA4 |

---

## Done statement

`main` reflects `staging` at the point RA2 completed, staging-verified.

**Same §3.1 rule R2 follows**: whatever confirms this step "done" must
land on **both** `main` and `staging`, not just `main` — don't repeat
v1.0.0's post-squash reconciliation cost (`6821380`, `9fa40bf`).

## Tasks

- [ ] Promote `staging` → `main` (fast-forward or merge, matching
      whatever this project's actual convention is by this point).
- [ ] Immediately backport this item's "done" confirmation to `staging`
      rather than leaving it only on `main`.

## UAT (manual)

- [ ] `main`'s HEAD matches `staging`'s at promotion time.

## Non-regression tests

- N/A (git operation, not code).
