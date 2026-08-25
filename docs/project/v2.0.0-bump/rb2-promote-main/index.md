# RB2. Promote `staging` → `main`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `main` | / |
| **Initial date** | 2026-08-25 | In progress |
| **Status** | 🟡 In progress — PR open, `release/v2.0.0-alpha.2-to-main` → `main` | / |
| **Source** | Mirrors RA3/R2, scoped to the alpha.2 cut (§1.12) | / |
| **Dependency** | RB1 | Blocks RB3 |

---

## Context

Hit the same structural issue Proposal 7 documents
(`consitution-amendment.md`, §18.5-proposed): `git merge-base
origin/staging origin/main` still resolves to this repo's very first
commit (`276fa63`) — squash merges never advance it, so a direct
`staging` → `main` PR would show the same class of whole-file `add/add`
conflicts RA3 hit, just larger (188 files this time vs. RA3's ~90).

**Applied the documented one-directional workaround**: built
`release/v2.0.0-alpha.2-to-main` from `main` (not `staging`), merged
`origin/staging` into it with `-X theirs`, and verified `git diff --stat
origin/staging HEAD` is empty — the branch's tree is byte-identical to
`staging`'s. First confirmed `staging` has no missing file relative to
`main` (`git diff --diff-filter=D --name-only origin/main
origin/staging` — empty), i.e. nothing unique on `main` would be lost.
RB1's own "done" confirmation (postponed off `staging` directly, since
`staging` is protected — no direct pushes) is committed on top of the
merge, on this branch, per §3.1's "finalize now, backport after" rule.

## Done statement

`main` reflects `staging` at the point RB1 completed, staging-verified.

**Same §3.1 rule RA3/R2 follow**: whatever confirms this step "done"
must land on **both** `main` and `staging`, not just `main` — don't
repeat v1.0.0's post-squash reconciliation cost (`6821380`, `9fa40bf`).

## Tasks

- [x] Confirm `staging` has nothing missing relative to `main` before
      building the reconciliation branch (see Context).
- [x] Build `release/v2.0.0-alpha.2-to-main` from `main`, merge `staging`
      in favoring its content (`-X theirs`), verify byte-identical tree.
- [x] Commit RB1's "done" confirmation on this branch (backported off
      `staging` directly, which is protected).
- [ ] Open PR into `main`, confirm CI green, merge.
- [ ] Immediately backport this item's "done" confirmation, and RB1's
      (already on this branch), to `staging` — a small follow-up PR,
      same one-directional limitation Proposal 7 describes (this
      direction's fix doesn't clear the reverse direction's conflict).

## UAT (manual)

- [ ] `main`'s HEAD tree matches `staging`'s tree at PR-open time
      (already verified locally — re-confirm post-merge).

## Non-regression tests

- N/A (git operation, not code).
