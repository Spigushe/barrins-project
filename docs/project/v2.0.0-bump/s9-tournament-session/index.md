# S9. Tournament / Training Session grouping for Tamiyo Scroll

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api`, `apps/tamiyo_scroll` | / |
| **Initial date** | 2026-07-27 | Scope decided 2026-07-27, added to the Group S table in `../index.md` as **S9** |
| **Status** | ✅ Done — the design pass arrived (`z-handoff-session-tab/`, 2026-07-31) and the dedicated Sessions tab is built: manage/create/close/reopen/archive, review closed sessions, and the comparison summary (incl. the relocated `ExpectedMetagameSection` for tournament-typed sessions). Full stack tested. | / |
| **Source** | Raised in conversation on 2026-07-27, not part of the original v2.0.0-bump request items | / |
| **Dependency** | None (no Group I decision touches this) | Resolves S5's open scoping question — S5's dependency row now includes S9; complements S3 without overlapping it |

---

## Context

**The request, restated**: let a user extract data for a specific tournament
or training session, as a subgroup of the "generic" tests that already
exist, and later compare that session's results against everything logged
before it.

**What exists today** (`apps/barrins_api/app/models/tamiyo_scroll.py`,
checked directly, not assumed):

- `TSMatch` (BO3 match log) and `TSCardTest` (per-card feedback) are the
  two "generic tests" entities. Neither has any grouping concept above the
  individual row — every match/card-test is a flat, ungrouped log entry
  tied to `owner_id` (and, for matches, always; for card-tests, optionally,
  `personal_deck_id`).
- `app/services/tamiyo_scroll/stats.py` computes winrate/matchup/archetype
  summaries as **pure functions over a `Sequence[TSMatch]`** — they don't
  know or care how that sequence was filtered. This matters below: a
  session-vs-baseline comparison can reuse these functions unchanged,
  just by feeding them two different subsets.
- **S5 ("PDF report of a training session") already has an open, unresolved
  task**: "Design the report's exact scope: one training session vs. a
  whole deck's history vs. a date range — not specified in the request,
  needs a follow-up question before implementation." No "session" entity
  exists anywhere in the schema today — S5's own title uses the word
  aspirationally. This item is proposed specifically to give that phrase a
  real, buildable meaning.
- No existing item in `v2.0.0-bump/index.md` §1 or its Group S table covers
  this — it is genuinely new scope, surfaced in conversation, not carried
  over from the original request.

## Proposed data model

**New table `ts_sessions`** (owned by `barrins_api`, same per-app
two-letter-prefix convention as every other `ts_*` table):

| column | type | notes |
| --- | --- | --- |
| `id` | UUID PK | |
| `owner_id` | FK → `users.id`, `ondelete=CASCADE` | |
| `personal_deck_id` | FK → `ts_personal_decks.id`, **not null** | a session is played with one deck, mirrors `TSMatch.personal_deck_id` |
| `name` | `String(255)` | e.g. "RC Toronto 2026" |
| `type` | `Enum` — `tournament` \| `training` | new `enum.StrEnum`, same pattern as `ArchetypeCategory` |
| `notes` | `Text`, nullable | |
| `created_at` | `DateTime(timezone=True)`, server default `now()` | this **is** the session's start boundary — no backdating, consistent with `TSMatch.date`'s existing "chronological log, no retroactive entry in v1" rule |
| `ended_at` | `DateTime(timezone=True)`, nullable | set by a "close session" action — the session is finished being played into, but still a live record |
| `archived_at` | `DateTime(timezone=True)`, nullable | **Resolved open question 3**: soft-delete, same pattern as `TSPersonalDeck.archived_at`/`TSMetaDeck.archived_at`. `DELETE /tamiyo-scroll/sessions/{id}` sets this rather than issuing a SQL `DELETE`, mirroring `archive_personal_deck`/`archive_meta_deck` exactly (`app/api/tamiyo_scroll/personal_decks.py`/`meta_decks.py`) |

`ended_at` vs. `archived_at`: distinct states, same as a deck can be
active-but-unused for a while before being archived. A session can be
`ended_at`-closed (no more matches logged into it) while still fully
visible; `archived_at` is the separate "hide this from my default list"
action, and — because it's soft, not a hard delete — an archived
session's comparison view stays queryable, matching `TSPersonalDeck`'s
"preserves history for future data science" rationale.

**`ts_matches.session_id`** — nullable FK → `ts_sessions.id`,
`ON DELETE SET NULL` (defensive DB-level policy only — in normal
operation `ts_sessions` rows are never hard-deleted, per the soft-delete
decision above, so this fallback exists for integrity, not as the primary
"leaving a session" mechanism). Archiving a session does **not** touch
`ts_matches.session_id`: matches logged into an archived session stay
tied to it, exactly like matches tied to an archived `TSPersonalDeck`
today.

**Resolved open question 1 — matches-only for v1, no `ts_card_tests.session_id`.**
Card-test grouping is dropped entirely, not deferred: version-scoped
card-test analysis (e.g. "how did this card perform under decklist
version 2 vs. version 3") is already extrapolable directly from
`ts_personal_decklist_versions`' own timestamps against
`TSCardTest.created_at`/`personal_deck_id`, without needing a session
concept at all. `ts_card_tests` gains no new column in this item.

This is a **subgroup, not a replacement**: `session_id IS NULL` remains the
default and is unchanged for every existing row and every new "generic"
entry going forward.

## Alternatives considered

1. **Dedicated `ts_sessions` entity + nullable FK on `ts_matches`
   (decided, described above; matches-only per resolved open question 1).**
   Gives sessions a stable identity to query against and a clear temporal
   anchor (`created_at`) to define "before it."
2. **Reuse `ts_personal_decklist_versions` as an implicit session
   boundary.** Rejected: a version bump doesn't correspond to a play
   session — conflates decklist iteration (S3's concern) with a play
   event (this item's concern). A session's matches already carry their
   own `decklist_version_id` via S3, independently — no need to overload
   one concept with the other.
3. **Freeform tag string instead of a first-class entity.** Rejected: the
   request explicitly wants comparison "against all tests ran before it,"
   which needs a stable identity to query against and a temporal anchor —
   a tag has neither.

## Comparison semantics

**Baseline definition — resolved open question 2**: same `owner_id` +
same `personal_deck_id`, `created_at < session.created_at` — i.e. every
match logged before this session started, by default **regardless of
whether those earlier rows belong to another session or are ungrouped**.
Rationale, confirmed: the ask is "everything before"; silently excluding
earlier sessions from the baseline would bias it toward casual testing
only, for no reason stated in the request.

**Flagged enhancement, not v1 scope**: comparing a session against a
specific **time frame** instead of "everything before" (e.g. "vs. the
last 30 days" rather than the deck's full history) was raised as
potentially interesting. Not designed or scheduled here — recorded so
it isn't lost, same treatment as S3's Moxfield-staleness enhancement.
If picked up later, it's an additional query parameter on the comparison
endpoint (a date-range baseline instead of the default
"before session" one), not a schema change.

**Computation is reuse, not new logic**: fetch both subsets (session rows,
baseline rows), run each through the *already-existing*
`compute_archetype_summary`/`compute_matchup_summary`, and diff the two
results (win-rate delta, matchup delta per opponent archetype). No
parallel calculation path — keeps Constitution §4.2 ("no duplicated
business logic") satisfied for free.

## API surface (new router, `app/api/tamiyo_scroll/sessions.py`)

- `POST /tamiyo-scroll/sessions` — `{name, type, personal_deck_id, notes?}`
- `GET /tamiyo-scroll/sessions?personal_deck_id=&include_archived=` —
  list, scoped to the caller via the existing `ownership.resolve_owner`
  pattern; `include_archived` mirrors `list_personal_decks`/
  `list_meta_decks`'s existing param
- `PATCH /tamiyo-scroll/sessions/{id}` — rename, edit notes, or close
  (`ended_at`)
- `DELETE /tamiyo-scroll/sessions/{id}` — **resolved open question 3**:
  archives (sets `archived_at`), never a SQL `DELETE`, exactly mirroring
  `archive_personal_deck`/`archive_meta_deck`. Matches keep their
  `session_id` unchanged — nothing falls back to the ungrouped pool from
  this action alone.
- `GET /tamiyo-scroll/sessions/{id}/comparison` — the session-vs-baseline
  stats bundle described above; works the same whether the session is
  archived or not
- `MatchWrite` schema gains an optional `session_id`, validated against
  the same owner and (recommended) the same `personal_deck_id`.
  **`CardTestWrite` does not** — resolved open question 1, matches-only.

## Frontend touchpoints

- Optional "Session" dropdown in `MatchFormFields.tsx` (not the card-test
  form — resolved open question 1, matches-only), same UX shape as the
  existing optional `opponent_deck_id`, plus an inline "+ New session"
  affordance.
- **Resolved open question 5 — both of the following, not one or the
  other**:
  1. The input-side toggle above (`MatchFormFields.tsx`), for logging
     matches into a session as they happen.
  2. A dedicated, management-like **Sessions** view (most likely its own
     tab, given it needs list/create/rename/close/archive actions that
     don't fit as a toggle inside `SuiviBo3Tab`), showing quick stats for
     whichever session is selected (match count, win rate, `ended_at`/
     `archived_at` state) plus the session-vs-baseline comparison via
     whatever stats-display components already render winrate/matchup
     tables today. Needs its own design pass (same "hifi design first"
     precedent already applied to S4) — not designed here.

## Scope addition (2026-07-30): relocate `ExpectedMetagameSection`

Raised by the user while starting this item's implementation. Today
`<ExpectedMetagameSection />` (`apps/tamiyo_scroll/src/pages/metagame/
MetaDecksSections.tsx:284`) renders unconditionally on the general
Metagame tab (`MetagameTab.tsx:13`) — a table of each roster deck's
Top 8/presence/conversion/"expected" level. That's tournament-prep data
(anticipating a specific event's field), which conceptually belongs to a
**tournament**-typed session, not to the always-on Metagame tab.

**Decided (2026-07-30)**: move, not duplicate. `<ExpectedMetagameSection />`
is removed from `MetagameTab.tsx` entirely and instead renders only inside
the dedicated Sessions view (§"Frontend touchpoints" below) when viewing a
session whose `type == "tournament"` — never for `training` sessions, and
never outside any session. This is a frontend-only relocation of an
existing, already-built component; no backend change. Depends on the
Sessions view existing to relocate into, so it lands as part of that
view's build, not before it.

## Open questions — resolved 2026-07-27

1. **Card-tests in scope for v1, or matches-only first?** **Decided:
   matches-only.** Version-scoped card-test analysis is already
   extrapolable directly from `ts_personal_decklist_versions` timestamps
   against individual `TSCardTest` entries, without a session concept —
   see "Proposed data model" above. `ts_card_tests` gains no `session_id`.
2. **Baseline scope**: "everything before," including other sessions.
   **Decided: yes** — the recommended default above is confirmed, not
   "generic pool only." A future option to compare against a specific
   time frame instead was raised as potentially interesting — flagged as
   a follow-on, not v1 scope (see "Comparison semantics" above).
3. **Session deletion**: hard-delete or soft-delete? **Decided:
   soft-delete**, via `ts_sessions.archived_at` — same pattern as
   `archived_at` everywhere else in this domain (`TSPersonalDeck`,
   `TSMetaDeck`).
4. **Does this get scheduled for v2.0.0?** **Decided: yes.** Added to the
   Group S table in `../index.md` as **S9**; S5's dependency row now
   includes S9.
5. **Frontend placement**: filter/toggle, or dedicated view? **Decided:
   both** — an input-side toggle on the match form, and a separate
   management-like Sessions view/tab with quick stats for the selected
   session. See "Frontend touchpoints" above.

## Done statement

- A user can create a named tournament/training session (`tournament` or
  `training`) against one of their personal decks, log matches into it,
  and close it (`ended_at`) when finished. Card-tests are not grouped by
  session in v1.
- A comparison view/endpoint shows the session's winrate/matchup summary
  side-by-side with the same deck's baseline (everything logged before the
  session started, including matches from other sessions), computed via
  the existing stats functions — no parallel calculation.
- A user can archive a session (`archived_at`, soft-delete, never a SQL
  `DELETE`) without affecting the matches logged during it — they keep
  their `session_id` and the session's history stays queryable.
- Sessions are usable both from an input-side toggle on the match form
  and from a dedicated Sessions view showing quick stats and the
  comparison for whichever session is selected.

## Tasks

- [x] Migration: `ts_sessions` table (`id`, `owner_id`, `personal_deck_id`,
      `name`, `type`, `notes`, `created_at`, `ended_at`, `archived_at`) +
      nullable `ts_matches.session_id` FK (`ON DELETE SET NULL`)
      (`f3b8c1d5a742_add_ts_sessions_table.py`).
- [x] `SessionCreate`/`SessionPatch`/`ResponseSession` schemas + CRUD
      routes (`app/api/tamiyo_scroll/sessions.py`), including
      `include_archived` on the list route (mirrors
      `list_personal_decks`/`list_meta_decks`) and an archive-not-delete
      `DELETE` route (mirrors `archive_personal_deck`/`archive_meta_deck`).
      **Deviation from the plan above**: no `ownership.resolve_owner`/
      `owner_id` param on the list route — sessions aren't part of the
      sharing-merge concept (confirmed nowhere in this doc's scope), so
      routes are owner-scoped via `CurrentUser` only, same shape as
      `meta_decks.py`'s write routes rather than its shared-aware
      `list_meta_decks`.
- [x] Extended `MatchWrite`/`ResponseMatch` (not `CardTestWrite`) with
      optional `session_id`. **Deviation**: validated via a new
      `_validate_session` helper in `matches.py` (owner + matching
      `personal_deck_id` check) rather than `ownership.resolve_owner`,
      which is a GET-only, shared-view concept (see above) — write-side
      validation needed a different helper, consistent with how
      `_validate_match_refs`/`_validate_decklist_version` already work in
      that same file.
- [x] `GET .../sessions/{id}/comparison` — fetches both subsets, reuses
      `compute_archetype_summary`/`compute_matchup_summary` (via
      `sharing_merge._from_match` to satisfy the `MatchLike` protocol —
      reused rather than duplicated), diffs session vs. baseline.
- [x] Frontend: optional session selector on `MatchFormFields`
      (`SessionField` in `MatchForm.tsx`), backed by new `api/sessions.ts`
      + `hooks/useSessions.ts`. Per the user (2026-07-30): same searchable
      Popover/Command combobox + inline "Create" dialog shape as
      `OpponentDeckField`, not a plain Select — the first draft used a
      plain Select (matching the sibling "Decklist version" field) and
      was corrected to match the opponent-deck field's UX exactly, per
      the original "Frontend touchpoints" spec above. A "— none —" entry
      at the top of the list is the only addition, since a session is
      optional (unlike the opponent).
- [x] **Dedicated Sessions tab, built 2026-07-31** per the design handoff
      (`z-handoff-session-tab/README.md` + `.dc.html`), 4th tab in
      `AppShell` (`/app/sessions`, after "My decklist"):
      `pages/SessionsTab.tsx` + `pages/sessions/SessionsSections.tsx`
      (`SessionsOverviewSection`, `SessionSummarySection`,
      `MatchupComparisonTable`, `StatTile`). The summary reads
      `GET .../sessions/{id}/comparison` directly (winrate already
      computed server-side); no client-side recalculation.
      **Deviation from the handoff, confirmed by the user (2026-07-31)**:
      the handoff explicitly marks the `ExpectedMetagameSection` move as
      out of scope for this tab ("hors scope... à traiter dans un handoff
      séparé si besoin") — the user chose to keep the earlier decision
      anyway. `ExpectedMetagameSection` is removed from `MetagameTab.tsx`
      and rendered inside the session summary card when
      `session.type === "tournament"`.
      **Extended the comparison response** (`session_wins`/
      `session_losses`/`baseline_wins`/`baseline_losses`, via
      `stats._tally_games`, reused not duplicated) — needed for the
      handoff's "V/D" ratio line, which `average_winrate` alone can't
      produce.
      **Reworked twice after the initial build, same day, per the user**:
      1. Initially built as two separate blocks ("Manage sessions"
         active-only table + "Review a closed session" list, per the
         handoff literally) and cross-deck (no `personal_deck_id` filter,
         matching the handoff prototype's own logic, which has no deck
         filter anywhere in its `sessions` handling). **Merged into one
         list** showing every non-archived session (ongoing + closed
         together) with a Status badge ("Ongoing"/"Closed") per row —
         the create form and Close/Reopen/✕ actions stay `canEdit`-gated,
         the list itself stays visible read-only. **Made deck-scoped**
         (matching every other tab's `useActiveDeck()` pattern) — the
         list now filters to the header's currently-selected personal
         deck via `useSessions(activeDeckId)`, and the creation form's
         "My deck" select was removed (a session is always created for
         the active deck). `hooks/useSessions.ts::useAllSessions` (the
         cross-deck hook this first needed) was added then removed in
         the same pass — no longer has a caller.
      2. Added a **per-opponent-deck matchup comparison table**
         (`MatchupComparisonTable`) to the summary, below
         `ExpectedMetagameSection`'s slot, for every session (not just
         tournaments): Deck / W/R global (baseline) / W/R session / Delta
         / Delta OTP / Delta OTD, one row per deck faced during the
         session, baseline looked up by `opponent_deck_id` from
         `baseline_matchup_summary.rows` (absent baseline = first time
         facing that deck this history contains — deltas show `—`).
         Entirely derived from the comparison endpoint's already-returned
         `session_matchup_summary`/`baseline_matchup_summary` rows — no
         backend change needed.
- [x] **Fix (2026-07-31): a closed session can no longer be picked** when
      logging or editing a match — `SessionField` (`MatchForm.tsx`) now
      splits the fetched sessions into a full list (for resolving the
      currently-assigned session's name, even if closed — an
      already-logged match shouldn't lose its label) and a
      `selectableSessions` list (`ended_at === null` only) for the
      combobox itself.
- [x] **Added (2026-07-31): reopening a closed session.** `SessionPatch`
      gains a `reopen: bool` flag (clears `ended_at`), symmetric to
      `close`; a "Reopen" button on each closed row in the sessions list
      (edit-mode only). `reopen` wins if a request somehow sends both
      flags — not a real path today, both are separate button actions.
- [x] **Added (2026-07-31): session shown on match journal rows.**
      `MatchJournalSection` now shows a neutral badge with the session's
      name (resolved via `useSessions(activeDeckId)`) on both the
      collapsed row and the View popup, when `match.session_id` is set.

## UAT (manual)

- [x] Backend: full suite green (308 tests including the new `reopen`
      test and win/loss-tally assertions) — confirms the baseline query
      excludes the session's own matches and includes prior history from
      other sessions/ungrouped, archiving leaves `ts_matches.session_id`
      untouched, and `reopen` clears `ended_at`. Frontend: full suite
      green (94 tests) — includes the closed-session-exclusion test, the
      session-badge-on-journal tests, and
      `sessions/SessionsSections.test.tsx` (merged-list status badges,
      canEdit gating, deck-scoped creation, close/reopen/archive,
      `ExpectedMetagameSection` shown only for tournament-typed sessions,
      and the matchup-comparison table's computed deltas).
- [ ] Manual UAT on staging (create a session, log matches into it and
      separately, view the comparison, close/reopen/archive it, confirm
      the Metagame tab no longer shows "Expected metagame" and the
      Sessions tab does for a tournament session) — not yet run; blocked
      on nothing technically, just not done yet.

## Non-regression tests

- New backend test: baseline query correctly excludes the session's own
  rows and includes only `created_at`-earlier rows for the same deck,
  regardless of whether those earlier rows belong to another session.
- New backend test: archiving a session sets `archived_at`, issues no SQL
  `DELETE`, leaves every matching `ts_matches.session_id` unchanged, and
  the comparison endpoint still returns correct results for it afterward.
- Confirm existing match tests are unaffected by the new nullable
  `session_id` column, and that `ts_card_tests` is untouched by this item.

## See also

- [`../s5-pdf-training-report/index.md`](../s5-pdf-training-report/index.md)
  — directly benefits from this; its open scoping question is what this
  item resolves.
- [`../s3-match-decklist-version/index.md`](../s3-match-decklist-version/index.md)
  — orthogonal, complementary: a session's matches each still carry their
  own `decklist_version_id` independently.
