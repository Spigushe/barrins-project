# R2. Promote `staging` → `main`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `main` | / |
| **Initial date** | 2026-09-06 | / |
| **Status** | ✅ Done | Lease-protected force-update, no PR — see Tasks |
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

- [X] Promote `staging` → `main`. `main`'s ruleset
      (`prod-main-protection`, id `19614704`) requires a merge-commit PR
      for normal traffic, but already carries an admin bypass
      (`RepositoryRole` 5, `bypass_mode: always` —
      `current_user_can_bypass: "always"` for the repo owner), unlike
      `staging`'s ruleset which had none and needed a temporary
      enforcement toggle for its own promote (§4.1 of
      `staging-promote-plan.md`). So this used a lease-protected direct
      push instead of a PR:
      ```bash
      git push \
        --force-with-lease="main:10c556ba1553da988f39709f8732659626890e4c" \
        origin origin/staging:main
      ```
      GitHub's response confirmed the bypass (`Bypassed rule violations
      for refs/heads/main: … Cannot force-push … Changes must be made
      through a pull request`). `main` became the exact same commit as
      `staging` (`116573c25c26ab273fbf3c6b22c2b83d71bd806f`) — no merge
      commit, so `main` is now a true git ancestor match of `staging`
      going forward, same property the `proj/v2.0.0-bump` → `staging`
      M1 promote delivered.
- [X] Safety net: before the force-update, pushed `main`'s pre-promote
      tip to a backup branch, `backup/main-pre-v2.0.0-promote`
      (`10c556ba1553da988f39709f8732659626890e4c`), so the prior `main`
      stays recoverable.
- [X] Immediately backport this item's "done" confirmation to `staging`
      (this doc update, landing on `staging` first) rather than leaving
      it only on `main` — don't let it accumulate the way v1.0.0's did.

## UAT (manual)

- [X] `main`'s HEAD matches `staging`'s at promotion time — verified
      `git rev-parse origin/main origin/staging` both print
      `116573c25c26ab273fbf3c6b22c2b83d71bd806f`.

## Non-regression tests

- N/A (git operation, not code).
