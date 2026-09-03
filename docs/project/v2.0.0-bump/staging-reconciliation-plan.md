# Staging ↔ v2.0.0-bump reconciliation + identity-cutover landing — plan

Status: **APPROVED** — open questions answered 2026-09-02 (see §5). Two items
still need a human visual check before the relevant step runs; they are marked
**⚠ CONFIRM** inline. **To be implemented by a fresh session** — this doc is the
entry point.
Author: Claude (Sonnet 5), 2026-09-02.

Prerequisite state for the implementing session: `feat/goblin-guide-login` is at
`41d2ac6c` (identity cutover, Phase 7+8), committed, **not pushed**, tree clean.
`git fetch origin` first. `origin/proj/v2.0.0-bump` and `origin/staging` are the
refs this plan reasons about.

---

## 1. Where every line sits today

| Ref | Relationship | Notes |
| --- | --- | --- |
| `feat/goblin-guide-login` (`41d2ac6c`) | **+26 / −0** vs `proj/v2.0.0-bump` | Identity cutover (rollout Phase 7+8) — committed, local only, not pushed. Fully current with its parent. |
| `proj/v2.0.0-bump` | the branch's real parent | Has the whole v2.0.0 app set (tolaria_news, karn_tablets, barrins_scripture, goblin_guide, identity_client, dc_calendar, …). |
| `staging` | **+23 / −23** vs `proj/v2.0.0-bump` | An **old fork** of the line. Missing every v2.0.0 app. `diff` = 546 files, +13.7k / −57.5k (the −57.5k is proj content staging never got). |

`origin/HEAD` → `origin/staging`, so `staging` is the repo default branch and the
eventual promotion target: `feat/goblin-guide-login` → `proj/v2.0.0-bump` → `staging`.

## 2. The problem

A straight `git merge origin/staging` into `feat/goblin-guide-login` produced
**160 conflicted files** (47 `barrins_api`, 58 `tamiyo_scroll`, 20
`barrins_scripture`, 17 project docs, 10 ops). Almost none of that is "staging is
ahead" — it is staging colliding with an older snapshot of six whole apps, plus
~18 dependency downgrades. Doing that reconciliation *inside* the cutover branch
would also bundle three unrelated efforts into one unreviewable merge commit
(constitution §18.1 / §18.3).

## 3. Is it "only PR #83"? — yes, substantively

`staging` has **23 commits** absent from `proj/v2.0.0-bump`:

| Category | Commits | Keep? |
| --- | --- | --- |
| **Feature** | `84109d9e` — **#83** "MTGJSON pipeline, decklist versioning, session overhaul, card-log split (S8–S18)" | **Yes — the reason for this effort** |
| CI fixes | `6a33fa8b` (#77 needrestart/WeasyPrint), `75278ea5` (#39 front job Node 22) | **⚠ CONFIRM** — diff each against proj before Step 2; carry only if not already covered |
| Docs | `625014dd` "backport RB1–RB4 done confirmations + backend_work_dir fix" | **⚠ CONFIRM** — same: visual check vs proj, carry only the delta |
| Promotion merge | `49a85e49` "RA2: v2.0.0-alpha — proj/v2.0.0-bump → staging" | N/A — artefact of a past promote, do not carry |
| Dependency bumps | ~18 dependabot commits (#25–#37, #59, #69, #76, #100, #101) | **No — decided.** Do not import staging's stale pins. Instead, after Step 3, get proj **up to date with dependabot** on its own (re-run / re-open dependabot PRs against the reconciled proj). |

So the reconciliation payload is **#83**, plus — pending the visual check — the two
CI fixes and the docs backport delta.

### What #83 actually carries (vs its own parent)

- **New files**: 47 `barrins_api`, 16 `tamiyo_scroll`, 11 project docs, 5 ops.
- **Modified files that also differ on `proj/v2.0.0-bump`** (→ real 3-way on a
  cherry-pick to proj): **~40** — 15 `barrins_api`, 11 `tamiyo_scroll`, the rest
  docs/ops. The `barrins_api` ones are mostly the **S8 MTGJSON extract fighting
  PR #60** (proj already has the *full* MTGJSON pipeline via `b5bac7cd`); #83's
  "reduced extract" is redundant there. The genuinely-new-to-proj content of #83:
  - **T6** — `text` / `keywords` / `power` / `toughness` / `loyalty` on `mj_cards`
    (migration `b7d1f4a290ec`).
  - **F10** — metagame roster scoped to the active personal deck
    (`TSMetaDeck.personal_deck_id` FK + `metagame_roster_scope` setting).
  - **S13** — shared `ConfirmDialog`.
  - **S14** — session overhaul (`location`, editable `started_at`/`ended_at`,
    freeform hue, `GET /sessions` sort/filter/paginate, opt-in auto-archive).
  - **S15** — decklist version history: view past content + card-aware diff
    (`DecklistViewContent`, `VersionHistorySection`).
  - **S16** — "Tested Cards → decklist change log" (relabels, card-test
    validation switches, change-log rendering).
  - **S17** — card-log / match-up-evaluation split + live card-name search
    (`api/cards.ts`, `hooks/useCards.ts`, `useDebouncedValue`).
  - **S18** — route flattening (`/app/tracker` → `/tracker`, etc., with
    redirects from the old paths).

## 4. Proposed sequence

### Step 0 — safety

- `feat/goblin-guide-login` is committed at `41d2ac6c`, tree clean. That is the
  rollback point for everything below.
- No pushes until each step is reviewed.

### Step 1 — land the identity cutover on `proj/v2.0.0-bump` — **via a real GitHub PR** (decided)

The branch is +26 / −0, so this is clean.

```
git push origin feat/goblin-guide-login
gh pr create --base proj/v2.0.0-bump --head feat/goblin-guide-login \
  --title "feat(identity): barrins_api → identity JWKS + Goblin Guide in tamiyo_scroll (Phase 7+8)"
```

- This is the **first push** of the rollout — it has been local-only until now
  (memory `goblin-guide-t11-login-slice`). Confirm the local dev-DB migration
  (`d9e1a2c3b4f5` + UUID remap, already applied) does not need to be part of the
  PR narrative beyond the runbook that is already in the diff.
- Expected merge conflicts on the PR: **none** (branch fast-forwards proj).
- CI must be green: `barrins_api` pytest + ruff + ty; `tamiyo_scroll` build +
  vitest + oxlint; `barrins_identity` suite; `ansible-lint ops/my-server`;
  markdownlint (`docs/content/**`) + cspell; `mkdocs build --strict`.
  `prettier --check` for `tamiyo_scroll` runs in CI (local CRLF checkout gives
  false positives — memory `goblin-guide-t11-login-slice`).
- Merge the PR by **squash** — the repo authorises squash-merge only. The 26
  sub-commits collapse into one on `proj/v2.0.0-bump`. Consequence: the local
  `feat/goblin-guide-login` tip is then *not* an ancestor of proj (squash makes a
  new commit), so after the merge **delete the local + remote branch**, or
  `git reset --hard origin/proj/v2.0.0-bump` it — do not keep committing on it.

### Step 2 — reconciliation branch off the updated `proj/v2.0.0-bump`

```
git checkout -b reconcile/staging-s8-s18 proj/v2.0.0-bump
git cherry-pick -x 84109d9e            # the #83 squash
# resolve ~40 files; then optionally:
git cherry-pick -x 6a33fa8b 75278ea5   # the two CI fixes, if still relevant
```

Resolution principles:

- **`barrins_api` MTGJSON / scripture files** — keep proj's fuller PR #60
  version; take from #83 only T6's new `mj_cards` columns + migration
  `b7d1f4a290ec` (re-parent it onto proj's real migration head) + the new
  S14–S17 endpoints/services (`sessions`, decklist-version, card-log,
  card-name search).
- **`tamiyo_scroll` shared files** (`CardTestsSection`, `SessionsSections`,
  `MetaDecksSections`, `MatchJournalSection`, `schemas/tamiyoScroll.ts`,
  `demo/*`) — take #83's S8–S18 version as the base; it is strictly ahead of
  proj's S1–S12 batch for these.
- **`AccountSettingsDialog` + `useSettings` + settings schema** — take #83's
  version (it adds the F10/S14/S15/S16 switches). The identity-cutover changes
  to this file that landed via Step 1 (`<AccountScreen>` embed, drop
  display-name form, `moderator` role) must be **re-applied on top** — this is
  the one file where Step 1 and #83 genuinely overlap. See Step 4.
- **Auth files** (`api/auth.ts`, `hooks/useAuth.ts`, `schemas/auth.ts`,
  `LoginPage.tsx`, `VerifyEmailPage.tsx`) — #83 still contains them (it predates
  the cutover). After Step 1 they are **deleted on proj**. Resolve every
  delete/modify conflict as **keep deleted**; re-point any #83 code that imported
  them onto `@barrins/goblin-guide` / `identityTokenStore`.
- **Route flattening (S18)** — proj's routes still carry `/app/*` after Step 1.
  Take #83's flattened paths + redirects; re-check `ProtectedRoute` /
  `AdminRoute` / `App.tsx` (touched by the cutover) against the new paths.
- **`package.json` / lockfiles** — keep proj's (post-cutover, has
  `@barrins/goblin-guide`); layer #83's genuinely-new deps only.

Verify the full test matrix again on `reconcile/staging-s8-s18`.

Estimated conflict surface: **~40 files**, all comprehensible as "S8–S18 vs
v2.0.0" — no dependabot noise, no six-apps churn.

### Step 3 — merge the reconciliation into `proj/v2.0.0-bump`

Real GitHub PR `reconcile/staging-s8-s18` → `proj/v2.0.0-bump`. After this, proj
has: v2.0.0 apps + identity cutover + S8–S18. `staging` can then be brought
forward from proj in a later, separate promote (RA2) — out of scope here.

### Step 3b — bring proj up to date with dependabot (decided)

Do **not** import staging's ~18 stale bumps. Instead, once proj carries #83's
new deps, let dependabot re-scan the reconciled proj and open fresh PRs; merge
those normally. This keeps pins current instead of resurrecting old ones.

### Step 4 — settings popup enhancement (the original ask #1)

Own branch off the reconciled `proj/v2.0.0-bump`, after Steps 1–3, then PR.
**Done on branch `feat/tamiyo-settings-popup-rework` (2026-09-03).**

1. `AccountSettingsDialog` keeps only application settings: sharing toggles,
   the F10/S14/S15/S16 switches, the four S12 display prefs.
   **Correction (2026-09-03):** an earlier draft of this line also listed
   "the test-team section". That section was *removed from the popup by
   S8–S18* (`v2.0.0-alpha.2`) and Step 4 does **not** re-add it there.
   But the removal turned out to be an *incomplete* refactor — the
   unmounted `AccountSettingsTeamSection` was the app's only leave-team /
   delete-team UI (the `barrins_api` endpoints stayed live). Step 4
   therefore re-homes that control onto the team page as
   `TeamPage.tsx`'s `TeamMembershipCard` (owner → two-step invite-code
   delete; member → leave), deletes `AccountSettingsTeamSection.tsx` /
   `.test.tsx`, and ports their coverage into `TeamPage.test.tsx`.
2. Removed the embedded `<AccountScreen>`; added a **"Manage my account"**
   button.
3. Where the button goes — **⚠ CONFIRM: answered Option B** (user,
   2026-09-03, "option b with a button 'back to <>'", same tab). The button
   navigates the current tab to
   `${VITE_GOBLIN_GUIDE_URL}/?return_to=<origin>&return_label=Tamiyo%20Scroll`.
   Goblin Guide's `ShellFrame` renders a "← Back to Tamiyo Scroll" link
   when `return_to` is a valid http(s) URL (never an auto-redirect → no
   open redirect). New `VITE_GOBLIN_GUIDE_URL` wired through `config.ts`,
   `.env.example`, `start-local.ps1`, and
   `ops/my-server/tamiyo_scroll.yml` (build-time reference only — never
   deploys/restarts Goblin Guide, §26.1). Option A (in-app `/account`
   route) was not taken.
4. **Needs visual confirmation** (OQ2): screenshot the reworked popup + the
   Goblin Guide account screen with the back link before the PR is
   finalised.
5. `AccountSettingsDialog.test.tsx` updated;
   `apps/goblin_guide/src/App.test.tsx` gains 3 back-link cases (present /
   absent / non-http rejected).

## 5. Open questions — answered 2026-09-02

| # | Question | Answer |
| --- | --- | --- |
| 1 | Step 1: GitHub PR or local merge? | **Real PR, squash-merge** (repo authorises squash only). First push of the rollout. |
| 2 | Carry CI fixes `#77` / `#39` + docs `625014dd`? | **Show the full diff + conflict list first.** The implementing session surfaces the complete Step 2 cherry-pick diff and every conflict for review *before* resolving anything — decide `#77`/`#39`/`625014dd` (and each conflict) then. |
| 3 | Dependabot | **Be up to date with dependabot** — drop staging's stale bumps, re-run dependabot on the reconciled proj (Step 3b). |
| 4 | Step 4 popup target | **Validated later** — route `/account` acceptable, but may end up a redirect to Goblin Guide. Build for either (Step 4 Option A/B). |
| 5 | `/account` route vs external link | Route is OK; **may finally be a redirect to Goblin Guide** — Option A/B in Step 4. |
| 6 | Who implements | **A new session** implements this plan end-to-end. This doc is the hand-off. |

### Still needing a human before the relevant step

- **⚠ CONFIRM (Step 2)**: the implementing session must **paste the full
  cherry-pick diff summary + the complete conflict list** and wait for review
  before resolving. No conflict resolution without sign-off. Includes the
  `#77` / `#39` / `625014dd` keep/drop call.
- **⚠ CONFIRM (Step 4)**: `/account` route vs Goblin Guide redirect; and a
  screenshot review of the reworked popup.

### Assumption to verify (not blocking)

- `barrins_scripture`'s 20 add/add conflicts in the staging-merge attempt are an
  artefact of merging *stale staging*; #83 does not touch `barrins_scripture`, so
  they should not appear at all under cherry-pick-onto-proj. Confirm by
  inspecting `git status` after the Step 2 cherry-pick.

## 6. Rollback points

- Before Step 1 push: `git checkout feat/goblin-guide-login && git reset --hard 41d2ac6c`.
- Step 1 PR merged in error: `git revert -m 1 <merge sha>` on `proj/v2.0.0-bump`
  (or delete-and-recreate proj from `origin/proj/v2.0.0-bump` if nothing else
  landed after it).
- Step 2 cherry-pick bad: `git cherry-pick --abort`; `reconcile/staging-s8-s18`
  is disposable — delete and start over.
- Local dev DB (`barrins_api_dev`) already migrated to `d9e1a2c3b4f5` +
  UUID-remapped (backup: scratchpad `barrins_api_ts_backup.20260902_182157.sql`) —
  unaffected by any of the above.
