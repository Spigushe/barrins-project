# S18. Deletion defaults to archive (soft-delete), not physical removal

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` | Schema/API change across most of the Tamiyo Scroll domain — no frontend redesign expected (list endpoints already hide archived rows the same way today) |
| **Initial date** | 2026-08-24 | Drafted 2026-08-24 |
| **Status** | 🔲 **Not started — scoped 2026-08-24** | `TSCardTest`/`TSCardTestEvaluation` already converted as part of S17; this item is the rest |
| **Source** | Surfaced while implementing S17 (`s17-card-log-matchup-evaluations/`) — the first cut of `DELETE /card-tests/{id}` cascaded to permanently destroy every evaluation logged against it. Generalized by the user into a project-wide rule, recorded as Constitution Amendment Proposal 8 (`../consitution-amendment.md`), applied the same day as `.claude/CLAUDE.md` §11.8 | / |
| **Dependency** | S17 (establishes the pattern this item extends to the rest of the domain) | / |

---

## Context

**Constitution §11.8** (added 2026-08-24): by default, every user-triggered
delete action is a disguised archive, not a physical removal — the row
disappears from the user's active view but stays in the database. A real
hard delete is only acceptable as an explicit, documented exception.

**Audit against the code, 2026-08-24** (`apps/barrins_api/app/`):

- **Already soft-delete** (an `archived_at` column, list queries filter
  it out): `TSPersonalDeck` (`personal_decks.py`), `TSMetaDeck`
  (`meta_decks.py`), `TSSession` (`sessions.py`). Of these, **only
  `TSSession` has a working restore path**
  (`PATCH /sessions/{id}` with `SessionPatch.restore` clearing
  `archived_at`) — `TSPersonalDeck`/`TSMetaDeck` can be archived but never
  un-archived today; `archived_at` is write-once.
- **Hard delete today** (`session.delete(...)`, no soft-delete column):
  - `TSCardTest` + `TSCardTestEvaluation` (`card_tests.py`) — **already
    converted** as part of S17 (`archived_at` on both, migration
    `6cf95145f67e`, delete routes archive instead of deleting, list/report
    queries filter `archived_at.is_(None)`). No restore path yet, matching
    `TSPersonalDeck`/`TSMetaDeck`'s current state.
  - `TSMatch` (`matches.py::delete_match`) — single table, no cascade
    fan-out.
  - `TSTeam` + its full cascade family (`teams.py::delete_team`) —
    `TSTeamMember`/`TSTeamDeckFlag`/`TSTeamDeckThread`/`TSTeamDeckMessage`
    are all `ondelete="CASCADE"` off `ts_teams.id` (and
    `TSTeamDeckMessage` further cascades off `TSTeamDeckThread`). One
    `delete_team` call today destroys rows in all four tables at once —
    the deepest cascade chain of any delete in the schema. A CASCADE FK
    can only express physical deletion, not "archive alongside parent",
    so this needs its own redesign, not a bulk column addition.
- **Confirmed out of scope**: `TSPersonalDecklistVersion`
  (`personal_decks.py::delete_decklist_version`) — stays a hard-delete
  exception, per the pre-existing "Option G" rationale (the version, not
  the deck, is the deliberate delete target, cf.
  `docs/tamiyo_scroll_tracker/00_plan_general.md`). Reviewed against the
  new default and explicitly kept by the user 2026-08-24.

## Tasks

### 1. Fill the restore-path gap

- [ ] `TSPersonalDeck`: add a restore mechanism (mirror `TSSession`'s
      `PATCH /personal-decks/{id}` + a `restore` flag on
      `PersonalDeckPatch`, clearing `archived_at`).
- [ ] `TSMetaDeck`: same, on `PATCH /meta-decks/{id}`.

### 2. Convert `TSMatch` deletion

- [ ] Add `archived_at` to `TSMatch`, migration.
- [ ] `DELETE /matches/{id}` sets `archived_at` instead of
      `session.delete`.
- [ ] `GET /matches` (and any stats/report call site reading matches
      directly) filters `archived_at.is_(None)`.
- [ ] Decide whether a restore path ships now or is deferred like
      `TSPersonalDeck`/`TSMetaDeck` today — flagged as an open question,
      not guessed here.

### 3. Redesign the Teams cascade family

- [ ] `TSTeam`: add `archived_at`; `DELETE /teams/{id}` archives instead
      of deleting; `leave_team`'s hard `session.delete(member)` and
      `remove_member` need the equivalent treatment for `TSTeamMember`.
- [ ] `TSTeamMember`, `TSTeamDeckFlag`, `TSTeamDeckThread`,
      `TSTeamDeckMessage`: each needs its own `archived_at` (none exist
      today) — a CASCADE FK cannot express "archive when your parent
      archives", so archiving a team needs application-level logic to
      archive its members/flags/threads/messages alongside it, not a
      schema-only change.
- [ ] Decide whether the existing `ondelete="CASCADE"` constraints stay
      (as a defensive DB-integrity fallback, never actually triggered in
      normal operation once the route-level archive-cascade is in place)
      or are loosened — open question, not guessed here.
- [ ] Team deletion's existing invite-code re-entry confirmation gate
      (the UX safeguard, not the hard-delete mechanism) is preserved —
      only the delete route's *effect* changes, not the confirmation
      flow in front of it.

### 4. Out of scope (confirmed, not re-litigated here)

- `TSPersonalDecklistVersion` deletion stays a hard delete — Option G.

## Non-regression tests

- Backend: every list/report endpoint touching `TSMatch`/`TSTeam`/its
  cascade family needs an "archived rows are excluded" test, mirroring
  the pattern already used for `TSPersonalDeck`/`TSMetaDeck`/`TSSession`
  and the new `TSCardTest`/`TSCardTestEvaluation` tests
  (`test_card_tests.py::TestDeleteCardTest::test_archives_rather_than_hard_deletes`,
  `TestDeleteCardTestEvaluation::test_archives_rather_than_hard_deletes`).
- Cascade-family archiving needs its own tests: archiving a team archives
  its members/flags/threads/messages too, and none of them are still
  reachable through normal reads afterward.

## See also

- [s17-card-log-matchup-evaluations/](../s17-card-log-matchup-evaluations/index.md) —
  where this was first surfaced and where `TSCardTest`/
  `TSCardTestEvaluation` were already converted.
- [../consitution-amendment.md](../consitution-amendment.md) — Proposal 8,
  the full Context/Alternatives/Trade-offs/Decision/Consequences record.
