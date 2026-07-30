# S2. Team sharing ("Team Decks")

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api`, `apps/tamiyo_scroll` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — §1.6 resolved 2026-07-25, spec below | / |
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
  lists decks flagged as shared to a team the current user belongs to.
- A way to flag an existing personal deck as shared to a specific team
  (UI control + backend field, e.g. `ts_personal_decks.shared_team_id`
  nullable FK). **No deck-name/card validation for v2.0.0** — deferred to
  v3.0.0, see the note above.
- Team members can fetch the PDF report (S5) for any deck shared into a
  team they belong to.
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

- [ ] Design and migrate `ts_teams` / `ts_team_members` (no
      `UNIQUE(user_id)` — multi-team membership allowed).
- [ ] Backend: team creation, invite-code generation/redemption
      (8-char, mixed alphanumeric, uppercased, dash-agnostic), member
      list, owner-only admin actions (flagging which decks get a
      discussion thread, removing a member).
- [ ] Backend: invite-code redemption rate limiting (1 per 5 seconds,
      5 per minute).
- [ ] Backend: per-team-deck discussion thread storage + routes.
- [ ] Backend: PDF report (S5) access check extended to "any team member
      of a team this deck is shared into," not just the deck owner.
- [ ] Backend: per-member test/match count across team-flagged decks,
      surfaced for the member list.
- [ ] Frontend: team page (name/description/members/discussion threads),
      description editable from this page (not at creation).
- [ ] Frontend: "flag to team" control alongside existing per-deck
      management UI in `DecklistTab`/`PersonalDeckSelector`.
- [ ] Frontend: "Team Decks" selector, reusing `resolve_owner`'s pattern
      generalized from a single `owner_id` to "any deck visible to a
      team I'm in."
- [ ] Frontend: "X" remove-member control per member-list row, gated by
      `window.confirm`.
- [ ] Frontend: two-step delete/archive confirmation (`window.confirm`
      then require typing the exact invite code).
- [ ] Frontend: popup ("quick mode": create/join/leave/delete,
      invite-code display) links to the full team page ("full mode")
      off the team-name banner.

## UAT (manual)

- [ ] Create a team, confirm an 8-character invite code is generated.
- [ ] Join the team as a second user via the invite code; confirm
      membership appears on the team page.
- [ ] Flag a deck to the team; confirm it succeeds with no card/name
      validation (deferred to v3.0.0 — same acceptance as a personal
      deck today).
- [ ] Confirm the second member sees the shared deck in "Team Decks",
      cannot edit it, and can open its PDF report.
- [ ] Remove the deck from the team; confirm the owner's personal-profile
      results for that deck are unaffected.
- [ ] Confirm the member list shows the correct per-member test count
      across team-flagged decks.
- [ ] Owner removes a member via the "X" control + `window.confirm`;
      confirm the removed member loses access to team decks/threads.
- [ ] Attempt to delete/archive a team: confirm it's blocked without both
      the `window.confirm` step and typing the exact invite code.
- [ ] Confirm invite-code redemption is rate-limited (rapid repeated
      attempts get rejected per the 1/5s, 5/min limits).
- [ ] Confirm a user can join a second team without losing membership in
      their first.

## Non-regression tests

- New `tests/tamiyo_scroll/test_teams.py`, following the existing
  `test_ownership.py` structure (404-not-403 on cross-team writes, same
  pattern as cross-owner writes today).
- Coverage for invite-code redemption, PDF access via team membership,
  and deletion isolation (deck removed from team leaves the owner's own
  match history/report untouched). No validation-rejection test — deferred
  to v3.0.0 alongside the gate itself.
- Coverage for invite-code rate limiting (6th attempt in a minute or 2nd
  within 5 seconds rejected), owner-only member removal, multi-team
  membership (no uniqueness violation on a second join), and the
  two-step delete confirmation (wrong/missing invite code blocks
  deletion).
