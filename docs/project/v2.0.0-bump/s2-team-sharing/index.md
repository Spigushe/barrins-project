# S2. Team sharing ("Team Decks")

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api`, `apps/tamiyo_scroll` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on §1.6 (team creation model) | / |
| **Source** | Request item 2.1 | / |
| **Dependency** | I5 (§1.6), S1 (builds on the sharing mechanism) | / |

---

## Context

No group/team entity exists anywhere in the schema today — every `ts_*`
table is single-owner. §1.6 lays out three alternatives for how teams
get created (open, admin-provisioned, or no new entity at all —
extending the existing single-boolean `data_shared` into a set of
grants) — **not decided**. Whichever is chosen, a "Team Decks" selector
in the UI needs *some* group identity to filter on, most likely a
lightweight `ts_teams`/`ts_team_members` pair regardless of the creation
semantics chosen.

## Done statement (once §1.6 is decided)

- A team entity exists with the creation/membership rules §1.6 settled
  on.
- A "Team Decks" selector (new, read-only, distinct from the personal
  "My decks" selector already in `AppShell`/`PersonalDeckSelector.tsx`)
  lists decks flagged as shared to a team the current user belongs to.
- A way to flag an existing personal deck as shared to a specific team
  (UI control + backend field, e.g. `ts_personal_decks.shared_team_id`
  nullable FK — exact shape depends on §1.6's outcome).
- Write-side enforcement follows the same pattern as S1/`resolve_owner`:
  team membership never grants write access to another member's deck,
  only read.

## Tasks

- [ ] Get §1.6 decided.
- [ ] Design and migrate the team schema.
- [ ] Add the "flag to team" control (likely alongside the existing
      per-deck management UI in `DecklistTab`/`PersonalDeckSelector`).
- [ ] Add the "Team Decks" selector, reusing `resolve_owner`'s pattern
      generalized from a single `owner_id` to "any deck visible to a
      team I'm in."

## UAT (manual)

- [ ] Create a team (however §1.6 defines it), add a second member,
      flag one deck to the team; confirm the second member sees it in
      "Team Decks" and cannot edit it.

## Non-regression tests

- New `tests/tamiyo_scroll/test_teams.py`, following the existing
  `test_ownership.py` structure (404-not-403 on cross-team writes, same
  pattern as cross-owner writes today).
