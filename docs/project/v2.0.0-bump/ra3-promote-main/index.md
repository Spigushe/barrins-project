# RA3. Promote `staging` → `main`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `main` | / |
| **Initial date** | / | Not started |
| **Status** | ✅ **Done (2026-08-03)** — hit Proposal 7's conflict at much larger scale than RA2: `git merge-base origin/main origin/staging` resolved to this repo's very first commit (`276fa63`), so a direct PR showed ~90 whole-file `add/add` conflicts. Fixed the same way (build from `main`, merge `staging` in, take `staging`'s content throughout — verified `main`'s 9 unique commits were already reflected in `staging` under the renamed `v1.0.0-bump/` path before discarding them). PR #52 merged (`a2835ad`); `main`'s tree confirmed byte-identical to `staging`'s | / |
| **Source** | Mirrors R2/v1.0.0's B4, scoped to the alpha cut (§1.11) | / |
| **Dependency** | RA2 | Blocks RA4 |

---

## Done statement

`main` reflects `staging` at the point RA2 completed, staging-verified.

**Same §3.1 rule R2 follows**: whatever confirms this step "done" must
land on **both** `main` and `staging`, not just `main` — don't repeat
v1.0.0's post-squash reconciliation cost (`6821380`, `9fa40bf`).

## Tasks

- [x] Promote `staging` → `main` (via PR #52, `release/v2.0.0-alpha-to-main`
      — a merge-commit branch built from `main`, not a direct
      `staging` → `main` PR; see Proposal 7).
- [x] Immediately backport this item's "done" confirmation to `staging`
      rather than leaving it only on `main` — this edit lands via
      `proj/v2.0.0-bump-scripture` → `proj/v2.0.0-bump` → `staging`,
      same as every other doc update this release.

## UAT (manual)

- [x] `main`'s HEAD matches `staging`'s at promotion time — confirmed via
      `git diff --stat origin/staging origin/main` (empty output) right
      after PR #52 merged.

## Non-regression tests

- N/A (git operation, not code).
