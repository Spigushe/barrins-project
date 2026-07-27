# S2. Team sharing ("Team Decks")

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api`, `apps/tamiyo_scroll` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — §1.6 resolved 2026-07-25, spec below | / |
| **Source** | Request item 2.1 | / |
| **Dependency** | I5 (§1.6, resolved), S1 (builds on the sharing mechanism) | S8 dependency dropped 2026-07-27 — see deck-validation gate note below |

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

## Tasks

- [ ] Design and migrate `ts_teams` / `ts_team_members`.
- [ ] Backend: team creation, invite-code generation/redemption, member
      list, owner-only admin actions (flagging which decks get a
      discussion thread).
- [ ] Backend: per-team-deck discussion thread storage + routes.
- [ ] Backend: PDF report (S5) access check extended to "any team member
      of a team this deck is shared into," not just the deck owner.
- [ ] Frontend: team page (name/description/members/discussion threads).
- [ ] Frontend: "flag to team" control alongside existing per-deck
      management UI in `DecklistTab`/`PersonalDeckSelector`.
- [ ] Frontend: "Team Decks" selector, reusing `resolve_owner`'s pattern
      generalized from a single `owner_id` to "any deck visible to a
      team I'm in."

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

## Non-regression tests

- New `tests/tamiyo_scroll/test_teams.py`, following the existing
  `test_ownership.py` structure (404-not-403 on cross-team writes, same
  pattern as cross-owner writes today).
- Coverage for invite-code redemption, PDF access via team membership,
  and deletion isolation (deck removed from team leaves the owner's own
  match history/report untouched). No validation-rejection test — deferred
  to v3.0.0 alongside the gate itself.

## See also

- [`../s10-personal-deck-game-flag/index.md`](../s10-personal-deck-game-flag/index.md)
  — same "deferred to v3.0.0, recorded so the design work isn't lost"
  treatment used for this item's deck-validation gate.
