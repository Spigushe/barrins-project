# S2. Team sharing ("Team Decks")

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api`, `apps/tamiyo_scroll` | / |
| **Initial date** | 2026-08-01 | / |
| **Status** | ✅ Done (2026-08-01) — implementation revised mid-build from per-deck to name-based sharing, see "Implementation note" below | / |
| **Source** | Request item 2.1 | / |
| **Dependency** | I5 (§1.6, resolved), S1 (builds on the sharing mechanism), S5 (PDF-report access for team members) | S8 dependency dropped 2026-07-27 — see deck-validation gate note below. **S5 dependency flagged 2026-07-30**: the Done statement, Tasks, and UAT below all assume team members can open a deck's PDF report, which is S5's deliverable — S2 can't fully complete until S5 exists |

---

## Context

No group/team entity exists anywhere in the schema today — every `ts_*`
table is single-owner. §1.6 laid out three alternatives for how teams get
created (open, admin-provisioned, or no new entity at all — extending
the existing single-boolean `data_shared` into a set of grants). **Now
decided**: Option 1 (open creation) with a real `ts_teams`/
`ts_team_members` entity — full spec below, restated from
`../index.md` §1.6.

## Decided spec (2026-07-25)

- **Creation**: any authenticated user can create a team and becomes its
  first member/owner. No admin gate for v2.0.0.
- **Future gating, not v2.0.0**: team creation may later be restricted to
  the **"Advanced User" tier** — confirmed (2026-07-25) as the existing
  `role_c` placeholder (ordinal level 2), finalized under that name in
  `../consitution-amendment.md`. Not built now — recorded so the schema
  below doesn't need reshaping later. **Per the user (2026-07-26): no
  reason is stated for this future gate** (no paywall/monetization
  framing). **Amended 2026-07-26**: `role_c`/Advanced User is owned by
  `barrins_api` until `barrins_identity` is implemented (transfers then,
  not before). If this tier is ever surfaced in the UI, it's driven by a
  backend-owned flag ("may be moved up to Advanced User") that
  determines *when* to show a "this may evolve" comment — not a
  frontend guess based on the user's plain current role.
- **Ownership**: `barrins_api` is the interim owner of the team/group
  concept for v2.0.0; ownership transfers to
  `barrins_identity`/Goblin Guide once released (`../consitution-
  amendment.md` Proposal 3). A full generic groups subsystem may ship
  alongside that effort later, not necessarily its first wave.
- **Joining**: an 8-character invite code, generated per team, shared by
  existing members with anyone they want to invite.
- **Team page**: name, description, member list, and one dedicated
  chat-like discussion thread **per deck under test** (not one thread
  per team) — which decks get a thread is decided by the team admin
  (the creator/owner).
- **Deck validation gate — deferred to v3.0.0 (2026-07-27)**: a deck
  shared into a team was to have its name (and cards) validated against
  backend-held MTG data before it's usable in that context. **Correction
  (2026-07-26)**: no `mtgjson`/`sets`/`cards` pipeline actually exists yet
  (verified — see `../index.md` F8/S8); this gate was blocked on S8
  landing first. **Deferred (2026-07-27)**, the same treatment given to
  S10: rather than wait on S8, v2.0.0 drops this gate entirely and
  accepts a team-shared deck the same way a personal deck is accepted
  today — unvalidated. No new inconsistency (nothing in Tamiyo Scroll
  validates deck contents against MTG data yet), and S2 no longer depends
  on S8. Revisit once S8 exists and this becomes real, feature-by-feature
  follow-on work.
- **Reporting**: team members get access to the PDF report (S5) of each
  deck shared into the team.
- **Deletion isolation**: removing a deck from a team never affects that
  deck owner's individual results on their own profile — deleting the
  team-share link is not deleting the deck or its match history.

## Conflicts with the account-settings popup handoff (resolved 2026-07-30)

`docs/project/v2.0.0-bump/z_handoff_params_popup/` specifies a "Team de
test" section inside the account-settings popup (S1) that overlaps this
item's scope. Team buttons stay hidden in the popup until S2
implementation starts, but the conflicts are now resolved:

1. **Multi-team membership allowed.** No `UNIQUE(user_id)` constraint on
   `ts_team_members` — a user can belong to more than one team. The
   popup's no-team/member/owner framing is a simplified view over the
   user's teams (e.g. a "primary" team), not a hard one-team-per-user
   rule.
2. **Description set from the team page, not at creation.** The popup's
   creation card collects only a name. `ts_teams.description` is set/
   edited later from the full team page (see #3), not at creation time.
3. **Popup is "quick mode"; team page is "full mode".** The popup covers
   only lifecycle actions (create/join/leave/delete, invite-code display
   for an owner). The full team page — member list, per-deck discussion
   threads, "Team Decks" selector, deck-sharing control, PDF-report
   access — lives at its own route in `apps/tamiyo_scroll`, reached via
   a link off the popup's team-name banner.
4. **Delete/archive requires two-step confirmation.** `window.confirm`
   as a first gate, then a second step where the owner must type the
   team's exact invite code before the delete/archive executes.
5. **Invite code format finalized.** 8 alphanumeric characters, mixed
   letters/digits with no positional rule (not "4 letters then 4
   digits"), always uppercase, no special characters. Displayed as
   `XXXX-XXXX`; the dash is display-only grouping, not part of the
   stored/validated code — codes can be entered with or without it.
   Redemption is rate-limited (1 attempt per 5 seconds, 5 per minute)
   to slow brute-forcing of codes.

## Implementation note (2026-08-01) — revised from per-deck to name-based sharing

While building this item, live testing surfaced that the spec above's
per-deck-instance model (`ts_personal_decks.shared_team_id`, one flag per
physical deck row) produced duplicate rows whenever two members owned a
deck with the same name (e.g. two members both running "King T'Challa")
— each showed up as its own separate "Team Decks" entry instead of one
merged row, and each needed flagging individually. The user redirected
implementation to **name-based sharing**, matching `sharing_merge.py`'s
existing S1 convention ("matched by exact name") instead of inventing a
second, deck-instance-scoped mechanism:

- **`ts_team_deck_flags`** (team_id, deck_name, name_key, flagged_by,
  created_at) replaces `ts_personal_decks.shared_team_id` entirely — no
  FK column on `ts_personal_decks`. Flagging one member's deck flags its
  *name*; every other current or future member's deck with that exact
  name is included automatically, computed at read time (never a
  per-deck write cascade).
- **Owner-only flagging.** Only the team owner decides which names are in
  the rotation (`FlagDeckCard` on the team page, backed by
  `GET /teams/{id}/members/decks` + `POST/DELETE .../decks/flags`) — not
  each deck's own owner, superseding this doc's original "deck owner
  flags their own deck" framing.
- **Discussion threads are name-keyed** (`ts_team_deck_threads.name_key`,
  not `personal_deck_id`) for the same reason — a thread is about the
  deck name, not one member's specific copy.
- **One cumulative PDF report per deck name per team**
  (`GET /teams/{id}/decks/{name_key}/report.pdf`), not one per owner —
  aggregates matches/card tests across every current contributing member
  into a single rolling-30-days report, rather than requiring a team
  member to pick whose copy to download.
- **Personal deck rename** (`PATCH /personal-decks/{id}`) shipped
  alongside this, since renaming a deck into/out of a flagged name is how
  a member joins/leaves a team-deck's rotation under the new model.
- **In-page confirmation dialogs, not `window.confirm`** — team delete
  and member removal use the app's existing `Dialog` component (matching
  `PersonalDeckSelector`'s archive-confirmation pattern) instead of the
  browser-native `window.confirm()` this doc's spec originally called for.
- **"Teams" is a top-level nav tab** (`/app/team`, sub-tabs per team +
  "Create / join"), not a single "My team" link — reflecting multi-team
  membership more visibly than the account-settings popup's "quick mode"
  (primary-team-only) view.

The account-settings popup's "quick mode" (create/join/leave/delete) is
unaffected by this revision — it never touched deck flagging.

## Done statement

- `ts_teams` (id, name, description, invite_code, owner_id, created_at)
  and `ts_team_members` (team_id, user_id, joined_at) exist, migrated.
- Any authenticated user can create a team (`POST` under the Tamiyo
  Scroll BFF) and becomes its owner; joining via the 8-character
  `invite_code` adds a `ts_team_members` row.
- A team page (`apps/tamiyo_scroll`) shows name, description, member
  list, and one discussion thread per deck the team admin has flagged
  for discussion.
- A "Team Decks" selector (new, read-only, distinct from the personal
  "My decks" selector already in `AppShell`/`PersonalDeckSelector.tsx`)
  lists decks flagged as shared to a team the current user belongs to —
  one merged row per deck *name* (see implementation note above), never
  one row per contributing owner.
- Owner-only: a way to flag a deck *name* into the team's rotation
  (`ts_team_deck_flags`, name-based — see implementation note above,
  supersedes this bullet's original `shared_team_id` FK plan). Every
  member's own deck with that exact name is included automatically.
  **No deck-name/card validation for v2.0.0** — deferred to v3.0.0, see
  the note above.
- Team members can fetch one cumulative PDF report (S5) per deck name,
  aggregating every current contributing member's matches/card tests.
- Removing a deck from a team's shared set deletes only the share link,
  never the deck, its matches, or the owner's personal-profile results.
- Write-side enforcement follows the same pattern as S1/`resolve_owner`:
  team membership never grants write access to another member's deck,
  only read.
- The team owner can remove an existing member via an "X" control at
  the end of their row in the member list, gated by `window.confirm`;
  the removed member loses access to the team's shared decks and
  discussion threads.
- The member list shows, per member, the count of tests/matches they've
  logged across all decks flagged into the team.

## Tasks

- [x] Design and migrate `ts_teams` / `ts_team_members` (no
      `UNIQUE(user_id)` — multi-team membership allowed).
- [x] Backend: team creation, invite-code generation/redemption
      (8-char, mixed alphanumeric, uppercased, dash-agnostic), member
      list, owner-only admin actions (flagging which decks get a
      discussion thread, removing a member).
- [x] Backend: invite-code redemption rate limiting (1 per 5 seconds,
      5 per minute).
- [x] Backend: per-team-deck-*name* discussion thread storage + routes
      (`ts_team_deck_threads.name_key` — revised from `personal_deck_id`,
      see implementation note).
- [x] Backend: PDF report (S5) access check extended to "any team member
      of a team this deck is shared into," not just the deck owner; a
      second, cumulative team-deck report endpoint added on top
      (`GET /teams/{id}/decks/{name_key}/report.pdf`).
- [x] Backend: per-member test/match count across team-flagged decks,
      surfaced for the member list.
- [x] Backend: name-based flag/unflag (`ts_team_deck_flags`,
      `GET /teams/{id}/members/decks`, `POST`/`DELETE .../decks/flags`)
      and personal-deck rename (`PATCH /personal-decks/{id}`) — added
      mid-build, see implementation note.
- [x] Frontend: team page (name/description/members/discussion threads),
      description editable from this page (not at creation).
- [x] Frontend: owner-only "Flag a deck" picker on the team page
      (`FlagDeckCard`) — supersedes the originally-planned per-deck
      control in `DecklistTab`/`PersonalDeckSelector`, see implementation
      note.
- [x] Frontend: "Team Decks" selector, one merged row per deck name.
- [x] Frontend: "X" remove-member control per member-list row, gated by
      an in-page confirmation dialog (not `window.confirm`, see
      implementation note).
- [x] Frontend: two-step delete/archive confirmation (in-page dialog,
      then require typing the exact invite code).
- [x] Frontend: popup ("quick mode": create/join/leave/delete,
      invite-code display) links to the full team page ("full mode")
      off the team-name banner; a top-level "Teams" nav tab (sub-tabs per
      team + "Create / join") was added alongside it.

## UAT (manual)

- [x] Create a team, confirm an 8-character invite code is generated.
- [x] Join the team as a second user via the invite code; confirm
      membership appears on the team page.
- [x] As owner, flag a member's deck (by name) into the team; confirm it
      succeeds with no card/name validation (deferred to v3.0.0 — same
      acceptance as a personal deck today).
- [x] Confirm a second member owning a same-named deck is included
      automatically, with no action of their own, and appears merged
      (not duplicated) in "Team Decks".
- [x] Confirm the second member sees the flagged deck in "Team Decks",
      cannot edit it, and can download its cumulative PDF report.
- [x] Unflag the deck name; confirm every contributing member's deck
      drops out of the team's rotation, and their own personal-profile
      results are unaffected.
- [x] Confirm the member list shows the correct per-member test count
      across team-flagged decks.
- [x] Owner removes a member via the "X" control + in-page dialog;
      confirm the removed member loses access to team decks/threads.
- [x] Attempt to delete/archive a team: confirm it's blocked without both
      the confirmation dialog and typing the exact invite code.
- [x] Confirm invite-code redemption is rate-limited (rapid repeated
      attempts get rejected per the 1/5s, 5/min limits).
- [x] Confirm a user can join a second team without losing membership in
      their first.
- [x] Rename a personal deck; confirm it joins/leaves a team's flagged
      rotation accordingly if the new/old name matches a flag.

## Non-regression tests

- `tests/tamiyo_scroll/test_teams.py` (39 tests), following the existing
  `test_ownership.py` structure (404-not-403 on cross-team writes, same
  pattern as cross-owner writes today).
- Coverage for invite-code redemption, PDF access via team membership
  (both the deck-level S5 report and the new cumulative team-deck
  report), and deletion isolation (unflagging a name leaves every
  contributing member's own match history/report untouched). No
  validation-rejection test — deferred to v3.0.0 alongside the gate
  itself.
- Coverage for invite-code rate limiting (6th attempt in a minute or 2nd
  within 5 seconds rejected), owner-only member removal, owner-only
  flagging, multi-team membership (no uniqueness violation on a second
  join), name-based auto-sharing (flagging one deck includes every
  same-named deck; renaming into/out of a flagged name joins/leaves the
  rotation), and the two-step delete confirmation (wrong/missing invite
  code blocks deletion).
- Frontend: `TeamPage.test.tsx`, `TeamDeckSelector.test.tsx`,
  `AccountSettingsTeamSection.test.tsx`, `PersonalDeckSelector.test.tsx`
  (rename flow) — full suite (135 tests) green.
