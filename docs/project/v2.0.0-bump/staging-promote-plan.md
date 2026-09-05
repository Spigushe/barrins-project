# Staging promote plan — full `v2.0.0` (`proj/v2.0.0-bump` → `staging`)

[← Back to project index](index.md) ·
companion to [`staging-reconciliation-plan.md`](staging-reconciliation-plan.md)

| | |
| --- | --- |
| **Goal** | Get the fully-reconciled `proj/v2.0.0-bump` (identity cutover + S8–S18 + Steps 1–4) onto `staging`, then deploy staging. |
| **Status** | ✅ **§4 branch promote complete** (verified 2026-09-05). `staging` was force-updated to `proj/v2.0.0-bump`'s tip via **M1** (Q5 resolved by action) — confirmed by `staging`'s linear history carrying the full T1–T15/S1–S18 payload and by `git diff origin/staging origin/proj/v2.0.0-bump` being empty at the time of promotion. `proj/v2.0.0-bump` was re-synced to `staging`'s later tip via PR #127 (2026-09-04) and then deleted (this change). **§5 (staging server deploy) has not started** — code is on `staging`, but the operator run (backups, user migration, `alembic upgrade head`, ansible deploys) is still pending; user will drive it manually (Q4). Q3 still open. |
| **Scope** | `proj/v2.0.0-bump` → `staging` only. `staging` → `main` (RA3/RB2-equivalent) is the next, separate step and is **out of scope here**. |
| **Predecessors** | `staging-reconciliation-plan.md` Steps 1–4 (all merged: #109, #113, #114). RA2 (`ra2-merge-staging/index.md`) — the *alpha* promote, done 2026-08-03, whose lessons this reuses. |

---

## 1. Why this is not a fast-forward

`proj/v2.0.0-bump` and `staging` have genuinely diverged (measure again
before acting — these are the 2026-09-03 numbers):

- `proj/v2.0.0-bump` is **~27 commits ahead** of `staging` — the whole
  v2.0.0 line (Tamiyo S1–S12, Scripture pipeline, Tolaria News, Karn T6,
  identity/Goblin T10–T15, the S8–S18 reconciliation #113, Step 4 #114).
  This is the intended payload.
- `staging` is **~23 commits ahead** of `proj/v2.0.0-bump`, and those are
  **not** all disposable:

  | On `staging`, not on `proj` | Disposition |
  | --- | --- |
  | `84109d9e` — #83 "MTGJSON pipeline … (S8–S18)" | **Content already in `proj`** via `git cherry-pick -x 84109d9e` in #113. A plain merge sees the same changes on both sides → spurious conflicts across every S8–S18 file. |
  | `6a33fa8b` — #77 needrestart CI fix | Same — cherry-picked into #113. |
  | `625014dd` — "docs: backport RB1–RB4 done confirmations …" | Reconciliation plan §2 said **drop**. |
  | `75278ea5` — #39 "bump front job to Node 22 …" | Reconciliation plan §2 said **drop**. |
  | ~18 dependabot bumps (#25–#37, #59, #69, #76, #100, #101) | Reconciliation plan **Step 3b**: do **not** import these. Re-run dependabot on reconciled `proj` and merge fresh PRs instead. |
  | `49a85e49` — "RA2: v2.0.0-alpha — proj/v2.0.0-bump → staging" | Old promote merge commit; superseded. |

### The structural problem (already documented)

`v2.0.0-bump/index.md` §RA2 and
[`consitution-amendment.md`](consitution-amendment.md) **Proposal 7**
record that this repo's **squash-only branch protection never advances
the git merge-base** between two long-lived branches. RA2's PR #46
(`proj/v2.0.0-bump` → `staging` direct) hit exactly this and was
abandoned; the fix was a new branch built by merging `proj/v2.0.0-bump`
**into** `staging` (making `staging` a real ancestor), landed as PR #49.
This promote will hit the same wall and needs the same class of
workaround — see §3.

---

## 2. Prerequisites (do these first)

1. ✅ **Land `feat/team-url-by-code` (`f797935f`) into `proj/v2.0.0-bump`** —
   done: squash-merged as **PR #115** (`0e0693d4`). Rides in the promote.
2. 🟡 **Step 3b — dependabot** on the reconciled `proj/v2.0.0-bump`: let
   dependabot re-scan, open fresh PRs against `proj`, merge them normally.
   This brings pins current instead of resurrecting `staging`'s ~18 stale
   bumps. Do **not** cherry-pick the old bumps.
   - Dependabot reads `dependabot.yml` **only from the default branch
     (`staging`)**, and `target-branch` is a single string (no arrays, no
     wildcards). **PR #116** (→ `staging`, merged `1deb3777`) mirrors the
     four `staging` update entries with `target-branch: proj/v2.0.0-bump`
     so fresh grouped PRs are raised against the promote branch.
     Temporary — removed / auto-discarded at promote.
   - Re-scan done. Grouped PRs raised / resolved:
     - `npm /apps/*` → `proj/v2.0.0-bump`: **PR #118 merged** (`81ce1d4f`)
       — `react-router-dom` in tamiyo_scroll + 11 in tolaria_news.
     - `uv /apps/*` → `proj/v2.0.0-bump`: **⏳ not yet raised** — nudge
       `uv` on the Dependabot page (Insights → Dependency graph →
       Dependabot → Check for updates). Will bump pydantic / ruff / ty
       (+ selenium in scripture) from `proj`'s lower pins.
     - `npm /docs`, `github-actions /` → `proj/v2.0.0-bump`: no PR =
       nothing outdated.
   - Stale `staging`-side PRs: #110 / #111 **closed**; the re-scan's
     `staging`-targeted uv PR **#119 merged into `staging`** (`4fb750f0`,
     by user decision) — will be discarded by the Option-A promote.
2b. ✅ **Upgrade `proj/v2.0.0-bump`'s own `.github/dependabot.yml`** to
   match `staging`'s (`directories: ["/apps/*"]` glob + `all-updates`
   grouping, `target-branch: staging` only) — **PR #117** merged
   (`b8d9314e`), result byte-identical to `staging`'s config. Keeps the
   Option-A promote from regressing the config.
3. ✅ / 🔁 **Confirm `proj/v2.0.0-bump` HEAD is CI-green** — was `0e0693d4`
   (all 10 `ci` jobs green); now `b8d9314e` after #117. **Re-confirm
   after the Step 3b Dependabot PRs merge** (HEAD moves again).
4. ✅ **Branch strategy decided — Option A** (§3, 2026-09-03). Executed
   2026-09-0x via **M1** — see §4 below.
5. 🟡 **Prepare the staging deploy** — §5. In particular the `barrins_api`
   staging cutover cannot be skipped. Code is on `staging` (§4 done); the
   operator run itself is not scheduled yet (Q4: user will drive it
   manually — see §8).

---

## 3. Branch strategy — ✅ DECIDED: Option A (2026-09-03)

Two viable ways to make `proj/v2.0.0-bump`'s content the new `staging`,
given the divergence + poison commits + squash-merge-base problem:

### Option A — force-update `staging` to `proj/v2.0.0-bump` (recommended)

`staging` is reset to `proj/v2.0.0-bump`'s tip (a new branch PR that
resolves 100% to `proj`, or an admin force-push if branch protection
allows, or `git push -f` on a throwaway then fast-forward). Discards
`staging`'s stale dependabot bumps and the redundant cherry-picked
commits outright.

- **Pro:** `staging` history becomes clean and linear with `proj`; no
  fake conflicts to resolve; the dependabot state is whatever Step 3b
  produced, not a merge of two stale sets.
- **Con:** rewrites `staging` history — anything only on `staging` and
  not accounted for in §1's table is **lost**. Requires re-verifying that
  table is exhaustive (`git log --oneline proj/v2.0.0-bump..staging` at
  execution time, every entry classified). Coordinate if anyone has
  branches off `staging`.

### Option B — merge `proj/v2.0.0-bump` **into** `staging` (RA2's #49 shape)

Build a `release/v2.0.0` branch by merging `proj/v2.0.0-bump` into a
checkout of `staging`, resolving each conflict **in favour of `proj`**
for the cherry-picked S8–S18 / #77 files, then PR that branch → `staging`
so `staging` is a real ancestor and the PR diff is clean.

- **Pro:** no history rewrite; matches the RA2 precedent exactly.
- **Con:** a large manual conflict pass (every S8–S18 file, plus
  package/lock files vs staging's stale bumps) that is almost entirely
  "take `proj`" busywork; risk of a wrong resolution hiding in the noise;
  the merge commit permanently records staging's stale bumps as
  "superseded" rather than gone.

**Recommendation:** **Option A.** The reconciliation already did the real
integration work; Option B re-does it as conflict resolution. Option A
needs one careful audit (is §1's table exhaustive?) instead.

---

## 4. Execute (Option A)

**Status: ✅ done.** Verified 2026-09-05: `staging`'s commit history is a
linear superset carrying every `proj/v2.0.0-bump` commit (T1–T15,
S1–S18 reconciliation, Steps 1–4, #113/#114/#115/#117/#118), which is
only possible via the M1 hard-reset path — confirming M1 was used and
resolving Q5. `origin/proj/v2.0.0-bump` was re-synced to `staging`'s
(by-then-further-advanced) tip via PR #127 to make the final diff empty,
then deleted — closing §4.1 steps 6–7 (this doc update is step 7).

1. **Exhaustiveness audit of `proj/v2.0.0-bump..staging`.** Re-run at
   execution time (`git fetch && git log --oneline origin/proj/v2.0.0-bump..origin/staging`)
   — the run on **2026-09-03** (25 commits) classified **cleanly, nothing
   unclassified**:

   | Class | Commits | Disposition |
   | --- | --- | --- |
   | **(a)** content already in `proj` | `84109d9e` #83 S8–S18 (cherry-picked in #113), `6a33fa8b` #77 needrestart (cherry-picked in #113), `75278ea5` #39 front→Node 22 (proj CI is already on `node-version: "22"`) | discarded, no loss |
   | **(b)** explicit drop | `625014dd` RB1–RB4 backport, `49a85e49` RA2-alpha merge commit, `1deb3777` #116 Step-3b mirror config (temporary by design), `4fb750f0` #119 uv bumps (merged staging-side by choice; `proj` gets its own uv PR) | discarded, intended |
   | **(c)** stale dependabot bump (§1 — do **not** import) | `57821241` #101, `ad9577bd` #100, `233ff767` #76, `c985e843` #69, `482317e8` #59, and #25–#37: `67ea29c8` `1ceda30f` `d438ed70` `f65b003b` `6fb59e1b` `7add989d` `80ba806c` `212b8a68` `e79722fa` `9e7e89c4` `6779bc66` `9b57ac86` `be4cf2d8` | discarded; Step 3b (#118 + the pending `uv` PR) replaces them |

2. **Point `staging` at `proj/v2.0.0-bump`'s tip.** `staging` protection
   is `non_fast_forward` + `required_linear_history` + `pull_request` +
   `required_status_checks`, so a plain `git push -f staging` is blocked.
   **Record the pre-promote SHA** (`git rev-parse origin/staging`) first.

   - **M1 — admin bypass + hard reset (recommended).** Repo admin
     momentarily adds themselves to the `staging` ruleset bypass list (or
     unchecks *Block force pushes*), then:

     ```bash
     git fetch origin
     git switch staging && git reset --hard origin/proj/v2.0.0-bump
     git push --force-with-lease origin staging
     ```

     Re-enable the ruleset immediately. `staging` becomes the **same
     commit** as `proj/v2.0.0-bump` — no merge, so the `84109d9e` /
     `6a33fa8b` spurious-conflict problem (§1) never arises, and history
     is clean + linear. This is the only mechanism that delivers what
     Option A's "Pro" promises.
   - **M2 — content-sync PR (fallback, no admin toggle).** One commit on
     a branch off `staging` whose tree is overwritten to match `proj`:

     ```bash
     git switch -c promote/v2.0.0 origin/staging
     git restore --source=origin/proj/v2.0.0-bump --staged --worktree -- :/
     git clean -fd
     git commit -m "promote: v2.0.0 — proj/v2.0.0-bump content onto staging"
     ```

     PR → `staging`, squash-merge (CI-gated). The tree diff is exactly
     `staging → proj` (large, 100 % intentional). **Con:** `staging`
     keeps its divergent commits as ancestors, so the squash-merge-base
     issue (§3.1) persists for future `staging`↔`proj/*` work — tolerable
     only because `proj/v2.0.0-bump` is deleted right after this.

   After either: assert `git diff origin/staging origin/proj/v2.0.0-bump`
   is **empty**, then delete `proj/v2.0.0-bump`.

3. Confirm CI green on `staging` post-update — every job, not a subset.
4. Update this document's status and
   [`staging-reconciliation-plan.md`](staging-reconciliation-plan.md)
   (Step 3b + promote done) **on `staging`, in this same change** — the
   §3.1 lesson: release-tracking docs land on `staging` before `main`,
   never as a post-merge patch on `main`.

### 4.1 M1 runbook — force-update `staging` ← `proj/v2.0.0-bump`

Do this in one sitting. It only moves the branch pointer + triggers CI —
**there is no auto-deploy on push to `staging`** (only `CI.yml` and
`scripture-scrape.yml` exist; deploys are the manual §5.1 playbook runs),
so no maintenance window is needed for this part.

**Fixed facts** (verified 2026-09-03):

| Thing | Value |
| --- | --- |
| Remote | `origin` → `https://github.com/Spigushe/barrins-project.git` |
| `staging` ruleset | **`preprod-staging-protection`**, id **`19614687`**, `enforcement: active`, **`bypass_actors: []`** (nobody can bypass → must toggle) |
| `proj/**` ruleset | `proj-release-branch-protection` id `19839693` — **already** has admin-role bypass (`RepositoryRole` 5, `always`), so an admin can delete `proj/v2.0.0-bump` directly in step 6 without any toggle |
| Your access | repo **owner + admin** — can edit rulesets |
| SHAs *then* (will have moved — re-record in step 1) | `origin/staging` `4fb750f0`, `origin/proj/v2.0.0-bump` `81ce1d4f` |

---

**1. Pre-flight — re-fetch, re-record, re-audit.**

```bash
git fetch --all --prune
git rev-parse origin/staging            # >>> RECORD THIS as STAGING_OLD (rollback anchor)
git rev-parse origin/proj/v2.0.0-bump   # the target
git log --oneline origin/proj/v2.0.0-bump..origin/staging
```

Every commit the `git log` prints must map to class (a)/(b)/(c) in §4
step 1. If a commit appears that is **not** in that table, STOP and
classify it before continuing. (Expected at execution: the same 25, plus
possibly one more Step-3b dependabot commit on `staging` — that's class
(b), discarded.)

Confirm the working tree is clean (`git status` — an untracked
`staging-promote-plan.md` is fine; `git reset --hard` leaves untracked
files alone).

**2. Disable `staging` ruleset enforcement.** UI (lowest risk):

> GitHub → repo **Settings** → **Rules** → **Rulesets** →
> **`preprod-staging-protection`** → **Enforcement status** →
> switch **Active → Disabled** → **Save changes**.

CLI alternative (round-trips the JSON so no rule is dropped):

```bash
gh api repos/Spigushe/barrins-project/rulesets/19614687 \
  | jq 'del(._links, .node_id, .created_at, .updated_at, .current_user_can_bypass, .source, .source_type) | .enforcement = "disabled"' \
  > /tmp/staging-ruleset-off.json
gh api -X PUT repos/Spigushe/barrins-project/rulesets/19614687 --input /tmp/staging-ruleset-off.json \
  --jq '.enforcement'          # -> "disabled"
```

**3. Reset and force-push `staging`.**

```bash
git switch staging
git reset --hard origin/proj/v2.0.0-bump
git push --force-with-lease origin staging
```

`--force-with-lease` (not `--force`): it aborts if `origin/staging` moved
since your step-1 fetch, protecting against a race.

**4. Re-enable enforcement immediately.** Reverse of step 2 — UI:
Enforcement status **Disabled → Active → Save**. Or:

```bash
gh api repos/Spigushe/barrins-project/rulesets/19614687 \
  | jq 'del(._links, .node_id, .created_at, .updated_at, .current_user_can_bypass, .source, .source_type) | .enforcement = "active"' \
  > /tmp/staging-ruleset-on.json
gh api -X PUT repos/Spigushe/barrins-project/rulesets/19614687 --input /tmp/staging-ruleset-on.json \
  --jq '.enforcement'          # -> "active"
```

Then re-verify the ruleset still has all five rules and `bypass_actors:
[]`:

```bash
gh api repos/Spigushe/barrins-project/rulesets/19614687 \
  --jq '{enforcement, bypass_actors, rules: [.rules[].type]}'
# expect: active, [], ["deletion","non_fast_forward","required_linear_history","pull_request","required_status_checks"]
```

**5. Verify the promote.**

```bash
git fetch origin
git diff origin/staging origin/proj/v2.0.0-bump    # MUST be empty (identical trees)
git rev-parse origin/staging origin/proj/v2.0.0-bump   # MUST print the same SHA twice
```

Then wait for CI on the new `staging` tip and confirm **every** job green
(not just `ci-required`):

```bash
gh run list --branch staging --workflow CI.yml --limit 3
gh run view <run-id> --json jobs --jq '.jobs[] | "\(.conclusion)  \(.name)"'
```

**6. Delete `proj/v2.0.0-bump`** (now fully redundant — identical to
`staging`). Admin bypass on `proj-release-branch-protection` already
permits this:

```bash
git push origin --delete proj/v2.0.0-bump
git branch -D proj/v2.0.0-bump        # local
```

If the remote delete is refused, temporarily disable ruleset `19839693`
the same way as step 2, delete, re-enable.

**7. Docs (step 4 above).** On the new `staging`, in one squash-merged
PR: flip this file's Status to ✅ done and mark
`staging-reconciliation-plan.md` Step 3b + promote complete.

---

**Rollback (before deploys start).** `staging` still enforcement-disabled,
or disable it again, then:

```bash
git switch staging
git reset --hard <STAGING_OLD>        # the SHA recorded in step 1
git push --force-with-lease origin staging
```

re-enable enforcement. (`proj/v2.0.0-bump` deletion: recreate with
`git push origin <STAGING_OLD-or-81ce1d4f>:refs/heads/proj/v2.0.0-bump`
if you had already deleted it.) Once app deploys have run, roll back per
§7 / the cutover runbook instead.

---

## 5. Staging deploy (after the branch is promoted)

Promoting drives the staging deploys (`env_branch: staging` in every ops
playbook). Independent per app (§26.1 — one app, one playbook):

- **`barrins_identity`** — already on staging (rollout
  [`identity-goblin-guide-rollout.md`](identity-goblin-guide-rollout.md)
  Phase 5). Redeploy from the promoted `staging` tag; confirm JWKS +
  `POST /api/v1/users/lookup` + service-token.
- **`barrins_api` — the cutover gate.** The release carrying ADR-20 needs
  [`docs/content/ops/deployment/identity-cutover.md`](../../content/ops/deployment/identity-cutover.md)
  run **end to end** on staging: `IDENTITY_SERVICE_URL` +
  `IDENTITY_SERVICE_CLIENT_ID` / `_SECRET` in the staging env, and the
  one-time `users` → `barrins_identity` data migration **before**
  `alembic upgrade head` drops the `users` table. `ops/my-server/barrins_api.yml`
  never runs Alembic — SSH in and run it per the playbook's own reminder.
- **`goblin_guide`** — already on staging (Phase 5). Rebuild from the
  promoted tag (`VITE_IDENTITY_SERVICE_URL` = `identity-staging` origin).
- **`tamiyo_scroll`** — rebuild: `VITE_API_BASE_URL` = `api-staging`,
  `VITE_IDENTITY_SERVICE_URL` = `identity-staging`, and the new
  **`VITE_GOBLIN_GUIDE_URL`** = `goblin-staging` origin (Step 4). Run
  `barrins_api.yml -e deploy_env=staging` first so a backend exists.
- **`tolaria_news`** — unaffected by the cutover (still `barrins_api`
  token-less BFF reads). Redeploy only if its own code changed in the
  payload.
- **`docs`** — redeploy if the docs site is served from staging.

Order: `barrins_identity` → `barrins_api` (with the cutover runbook) →
frontends. Nothing in one app's playbook may restart another's (§26.1).

### 5.1 Execution checklist

Pre-req: §4 promote done, `staging` CI green, **maintenance window
announced** (logins are inconsistent between the `pg_dump` and the
`barrins_api` restart). Live-data detail for steps 2–6 is in
[`identity-cutover.md`](../../content/ops/deployment/identity-cutover.md)
— this is the sequence, not a substitute. All playbooks run from
`ops/my-server/` with `-e deploy_env=staging`; post-promote they build
from the `staging` branch by default (the runbook's
`-e ..._git_branch=feat/goblin-guide-login` examples are **stale** — that
work is now on `staging`).

1. **`barrins_identity`** — ensure `ALLOWED_ORIGINS` has
   `https://tamiyo-staging.barrins-codex.org` +
   `https://goblin-staging.barrins-codex.org`; `ansible-playbook
   barrins_identity.yml -e deploy_env=staging`. Verify `/health`,
   `/.well-known/jwks.json` (one key), `POST /api/v1/users/lookup` with a
   service token.
2. **Service account for `barrins_api`** — scope `identity:users:read`
   only; record `client_id` + once-shown `client_secret`.
3. **`barrins_api` staging env** (`ops/my-server/secrets/barrins_api/staging.env`)
   — remove `SECRET_KEY` / `ALGORITHM` / token-expiry vars; add
   `IDENTITY_SERVICE_URL` + `IDENTITY_SERVICE_CLIENT_ID` / `_SECRET`.
4. **Back up** `barrins_api_staging` and `barrins_identity_staging`
   (`pg_dump -Fc` to `~/backups/..._pre-cutover.dump`).
5. **User migration** — `scripts/migrate_users_to_identity.py --dry-run`,
   read the report (synthesised usernames, `-N` collisions, emails
   already in identity), then re-run without `--dry-run` (one target
   transaction; safe to repeat).
6. **Deploy `barrins_api`** — `ansible-playbook barrins_api.yml -e
   deploy_env=staging`, then **SSH in and `alembic upgrade head`** (the
   playbook never runs Alembic): applies `d9e1a2c3b4f5`, dropping
   `users` / `auth_email_verifications` / `userrole` + 12 FKs. Verify
   `alembic current` → `d9e1a2c3b4f5 (head)`, single head.
7. **Frontends** (each its own playbook, `-e deploy_env=staging`):
   - `goblin_guide.yml` — `VITE_IDENTITY_SERVICE_URL` = `identity-staging`
   - `tamiyo_scroll.yml` — `VITE_API_BASE_URL` = `api-staging`,
     `VITE_IDENTITY_SERVICE_URL` = `identity-staging`,
     `VITE_GOBLIN_GUIDE_URL` = `goblin-staging`
   - `tolaria_news.yml` — only if its code changed in the payload
   - `docs.yml` — if the docs site is served from staging
8. Proceed to §6 UAT.

---

## 6. UAT on staging

- Full CI green on the `staging` tip (backend pytest, frontend
  tsc/oxlint/vitest/build, `ansible-lint ops/my-server`, docs
  markdownlint/cspell, `mkdocs build --strict`).
- Auth: log in via Goblin Guide on `tamiyo-staging`; reload keeps the
  session (cookie-mode restore); "Manage my account" → `goblin-staging`
  with the "← Back to Tamiyo Scroll" link; account changes reflect back.
- Teams: `tamiyo-staging` team page resolves at `/team/<invite_code>`;
  member names render (identity directory reachable — not "Unknown
  member"); owner delete / member leave from `TeamMembershipCard`.
- S8–S18 smoke: MTGJSON data present; decklist version diff; session
  auto-archive; card-log / matchup evaluations; delete = archive.
- Migrations: `alembic heads` is a single head on the staging DB after
  `upgrade head`.

## 7. Rollback

- **Branch**: if Option A, `staging` can be pointed back at its previous
  tip (record the pre-promote SHA before step 4.2). If Option B, revert
  the merge commit.
- **Deploy**: each app's playbook has its own rollback (redeploy the
  prior release tag). `barrins_api` DB rollback = restore the pre-cutover
  backup taken as part of `identity-cutover.md` (the `users` table drop
  is not reversible by `alembic downgrade` alone once identity holds the
  authoritative copy).

---

## 8. Open questions

| # | Question | Owner |
| --- | --- | --- |
| ~~Q1~~ | ~~Option A (force-update) vs Option B (merge-into-staging)?~~ **Resolved: Option A** (2026-09-03). | user / Agent 0 |
| ~~Q2~~ | ~~Does `feat/team-url-by-code` ride in this promote?~~ **Resolved: yes** — merged as PR #115 (`0e0693d4`). | user |
| Q3 | Is `main` promotion (`staging` → `main`) in the same window, or a later cut? **Framing:** same-window = one maintenance window, but `main`'s live `users`-table drop happens right after staging UAT with no soak. Later cut = staging soaks under real use (surfaces identity / cutover regressions) before prod, at the cost of a second window + keeping `main` deployable meanwhile. The cutover's `users` drop is irreversible without a dump restore → a soak is the conservative call. | user |
| Q4 | Who runs the `barrins_api` staging cutover runbook (§5.1 steps 2–6), and when relative to the §4 branch promote? Runbook is `identity-cutover.md`; must be **after** §4 (needs `d9e1a2c3b4f5` on the promoted `staging`, which is satisfied — §4 is done). **Partially resolved (2026-09-05):** the user will drive the execution manually; Claude prepares/reviews commands and checks outputs. Timing (maintenance window) still to be scheduled. | user |
| ~~Q5~~ | ~~§4 step 2 mechanism: M1 or M2?~~ **Resolved: M1 was used** — confirmed 2026-09-05 by `staging`'s linear history containing every `proj/v2.0.0-bump` commit. | user (repo admin) |
