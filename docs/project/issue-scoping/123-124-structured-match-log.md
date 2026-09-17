# #123 + #124 — Structured per-game match log (mulligans, misplays, both sides)

[← Back to issue-scoping index](README.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` + `apps/tamiyo_scroll` | `ts_matches` data model + `MatchFormFields` + stats/report |
| **Initial date** | 2026-09-08 | Scoped from the code, not yet decided |
| **Status** | 🟩 **Decisions locked (2026-09-15)** | Ready to plan implementation. Role-gating ships at a static `moderator` floor now; the dynamic admin on/off layer follows once [T16](../v2.0.0-bump/t16-goblin-guide-feature-gates/index.md) lands |
| **Source** | GitHub issues [#123](https://github.com/Spigushe/barrins-project/issues/123) (2026-09-04) + [#124](https://github.com/Spigushe/barrins-project/issues/124) (2026-09-04) | Both authored by the repo owner; both say *"Refactor match log form"* verbatim |
| **Roadmap** | [#124 → v3](../../content/front/tamiyo_scroll/roadmap.md) ("error count + comment on both sides"); [#123 → v3+](../../content/front/tamiyo_scroll/roadmap.md) ("mulligan counts per side, one row per game — likely deserves its own scoping pass") | This page is that pass |
| **Related** | roadmap v3 "winrate starting/not-starting per match", v3+ "module selection for new game screen", Constitution §13.6 (`moderator` tier), §45.2, §48; [T16 — Goblin Guide feature gates](../v2.0.0-bump/t16-goblin-guide-feature-gates/index.md) | |

---

## Why one page for two issues

Both issues:

- say *"Refactor match log form"* as their entire "Expected Behaviour";
- add **per-game, per-side** structured data to the same `ts_matches`
  record;
- list the same "Possible evolution": *"Add those buttons under user
  level restriction to grant it only to close circle"* (Constitution
  §13.6's `moderator` tier);
- touch the same lines of the same form
  ([`MatchFormFields` in `MatchForm.tsx`](../../../apps/tamiyo_scroll/src/pages/suivi-bo3/MatchForm.tsx))
  and the same request schema.

Implementing them separately would mean two migrations and two reworks
of the same component. They are one work item.

## The requests, verbatim

**#123 — mulligans:**

> I can only write my mulligans but I can't have an average handsize over
> a period of time/session. … Refactor match log form.

**#124 — misplays:**

> I can only write and follow errors using the text area, I would like to
> have a way to track them game per game and in the long run. … Refactor
> match log form.

## Context — verified against the code (2026-09-08, `staging`)

### `ts_matches` has no per-game structure — games 1/2/3 are three flat columns

[`TSMatch`](../../../apps/barrins_api/app/models/tamiyo_scroll.py):

```text
game1 / game2 / game3 : Mapped[GameResult | None]   # three flat nullable columns
on_play               : Mapped[bool]                # ONE match-level bool, not per game
opening_hand          : Mapped[str | None]          # free text  (form label: "Game 1 Notes")
turning_point         : Mapped[str | None]          # free text  (form label: "Game 2 Notes")
final_turn            : Mapped[str | None]          # free text  (form label: "Game 3 Notes")
```

There is **no `ts_match_games` table**. Mulligans and misplays exist
today only as whatever the user types into those three free-text boxes.
`on_play` being a single match-level bool also means "who was on the
play in game 2/3" is not recorded at all (relevant to the roadmap's
separate v3 "winrate starting/not-starting" item, and a reason a
per-game table is attractive).

### Write path

- [`MatchWrite`](../../../apps/barrins_api/app/schemas/tamiyo_scroll.py)
  — flat mirror of the columns above.
- [`_apply_payload` in `matches.py`](../../../apps/barrins_api/app/api/tamiyo_scroll/matches.py)
  — copies the 6 fields across, nothing more.
- Frontend `MatchDraft` / `emptyMatchDraft` / `draftFromMatch` /
  `matchDraftToWrite` in `MatchForm.tsx`, plus `matchSchema` /
  `matchWriteSchema` (Zod) in `schemas/tamiyoScroll.ts` — all flat
  mirrors again.
- `MatchFormFields` renders three `GameResultSelect`s and three
  `Textarea`s. The S12 work already renamed the textarea labels
  ("Opening hand" → "Game 1 Notes", etc.) without touching the columns.

### Stats / reports that would consume a new "average hand size" metric

- [`stats.py` `compute_period_stats`](../../../apps/barrins_api/app/services/tamiyo_scroll/stats.py)
  — the shared winrate/matchup calculator.
- [`report.py`](../../../apps/barrins_api/app/services/tamiyo_scroll/report.py)
  — the WeasyPrint session + deck PDF reports.
- `GET /sessions/{id}/comparison` → `SessionSummarySection` stat tiles.
- `sharing_merge.py` `_from_match` — the read model shared/merged
  matches flow through; any new field must be carried here too.

None of these branch on `session.type`; all are backend-owned (§4.1) so
the derived metric must be computed server-side, never in the form.

## The data question at the centre of both issues

New data to capture, per the issues:

| Field | Per what | From which issue |
| --- | --- | --- |
| Player mulligans | game × side (player), live stepper — see D2 | #123 |
| Opponent mulligans | game × side (opponent), live stepper — see D2 | #123 |
| Player misplay count | game × side (player), live stepper — see D2 | #124 |
| Opponent misplay count | game × side (opponent), live stepper — see D2 | #124 |
| Misplay comment | game × side (decided D2 below — not a replacement, see D3) | #124 |

"Average hand size over a period/session" (#123) is **derived**, not
stored: with the London mulligan (Duel Commander's rule) N mulligans →
keep 7, bottom N → hand size `7 − N`, so
`avg_hand_size = 7 − avg(player_mulligans)` over the period. Backend-owned.

## Alternatives for the model

### A. New `ts_match_games` child table (roadmap's steer) — **chosen: Full**

`(id, match_id FK, game_number 1..3, player_mulligans, opponent_mulligans,
player_misplays, opponent_misplays, player_note, opponent_note)` — one
row per game actually played.

- **Hybrid (originally recommended):** keep `game1/2/3` and `on_play` on
  `ts_matches` exactly as they are (every stats query reads them today —
  untouched, zero regression risk), add `ts_match_games` **only** for
  the new mulligan/misplay/note data. A game row is created lazily when
  the user fills in any of its new fields.
- **Full (decided, 2026-09-15):** also move `game1/2/3` results and a
  per-game `on_play` into the child table, deprecating the flat columns.
  Chosen over the hybrid despite the larger blast radius — it gives
  #123's "one row per game" its natural shape everywhere at once and
  absorbs the roadmap's separate "per-game `on_play`" v3 item for free,
  instead of paying for a second migration later.
- **Trade-offs accepted:** every read site of `game1/2/3` must be
  rewritten against `ts_match_games` — `stats.py` (its `MatchLike`
  protocol / tally logic, not `report.py` directly — `report.py`
  consumes `stats.py`'s output), `sharing_merge.py::_from_match`,
  `MatchJournalSection`, `matches.py::_apply_payload`, `MatchForm.tsx`,
  plus the demo fixtures (`demo/api/matches.ts`, `statsCore.ts`) — six
  frontend files total touch the flat fields and must move together in
  one PR (Agent 2 review, 2026-09-15). This is materially larger than
  the hybrid and needs its own migration-safety pass (§31.3: backup,
  verify compatibility, test the migration) before it runs against
  production data — see **D1's amendment** below (two migrations, not
  one).

### B. Flat columns on `ts_matches`

`player_mulligans_g1/g2/g3`, `opponent_mulligans_g1/g2/g3`,
`player_misplays_g1/g2/g3`, `opponent_misplays_g1/g2/g3` (+ note columns)
— 12–18 new nullable columns.

- **Trade-offs:** no join, trivially additive, mirrors the existing
  `game1/2/3` style. But it's wide, it hard-codes "max 3 games" into the
  schema three times over, and #123's "one row per game" becomes a
  cross-column read every time. Gets unwieldy fast if any further
  per-game field is ever added.

### C. One JSONB `games` column on `ts_matches`

- **Trade-offs:** flexible, one migration. But it puts structured,
  queried, aggregated data (the whole point of #123 is *aggregation*)
  behind JSON extraction, which the project has generally avoided for
  anything that isn't an opaque passthrough (`moxfield_data` is the
  precedent, and that is deliberately *never* queried field-wise).
  Rejected unless the user wants it.

## Decision (2026-09-15) — supersedes the original recommendation

**Alternative A, full normalization.** All eight flagged decisions below
are resolved; do not re-litigate them without a new scoping pass. The
original recommendation (hybrid, defer role-gating) was **not** taken —
see D1 and D7.

## Decisions (resolved 2026-09-15)

1. **Model shape — Full normalization, migration split in two (amended
   2026-09-15).** `ts_match_games` absorbs `game1/2/3` and per-game
   `on_play` too; the flat columns are eventually dropped. Per the Agent
   1 + Agent 3 review, this ships as **two separately-deployed
   migrations, not one**: Migration 1 adds `ts_match_games` and backfills
   every existing match's `game1/2/3`/`on_play` into it, then the app
   deploys reading/writing the new table while the flat columns still
   exist; Migration 2, only after a production verification window
   (row-for-row check: `ts_match_games` row count and values per match
   match the pre-migration `game1/2/3`/`on_play` data), drops the flat
   columns. This gives a real rollback point between the two steps that
   a single combined migration would not. See the "Trade-offs accepted"
   note under Alternative A above for the full list of call sites this
   touches.
2. **Misplay/mulligan input — live stepper controls, not a Select; layout
   amended after UX + frontend review (2026-09-15); comment granularity
   amended a second time to per-event (2026-09-15, later same day).**
   Both counters (mulligans and misplays, per game × side) are **live
   increment ("+1") controls**, not a dropdown chosen after the fact —
   the actual usage pattern is entering each misplay one after another
   as it happens, with the match form filled in live and updated after
   each game, not filled out retrospectively at the end. `MatchFormFields`
   gets a per-game subcomponent (Agent 2's recommendation) rather than
   inlining new rows into the existing flat component; a game's row
   appears/becomes live once that game starts, consistent with D8's lazy
   row creation. The original plan to copy `CardTestsSection.tsx`'s
   `<Select>` + pinned-"add"-row list chrome verbatim is **not**
   followed — that pattern fits an occasional, unbounded, add-to-a-list
   log (card-test evaluations); this is a bounded, high-frequency,
   live-during-play entry, and needs its own lighter interaction.

   **Second amendment — comment is per-event, not per-game×side.** The
   user's real requirement: *"comments for misplay and mulligan are on a
   per-item basis — EACH NEW misplay/mulligan can add a specific comment
   (game state, decision, cards in hand, etc)."* This supersedes D2's
   first amendment above, which had settled on a single per-game×side
   comment `<Input>`. Resolved via a follow-up clarifying round:
   - **Both a stored counter and an event list are kept** (not a purely
     derived count). Each side/kind (`player_mulligans`,
     `opponent_mulligans`, `player_misplays`, `opponent_misplays`) is now
     an **ordered list of events**, each with its own optional comment,
     *and* `ts_match_games` still stores the resulting count as a plain
     integer column for cheap averaging — but that integer is now
     **backend-derived only** (`len(events)`), never independently
     client-writable. There is exactly one source of truth (the event
     list); the integer is a maintained cache of it, never a second
     place the same fact could drift (§4.2).
   - **Mulligans and misplays behave identically** — one generic
     event concept (`side` × `kind`), no special-casing between the two.
   - **UI flow: "+1" immediately logs a blank-comment event**; the
     comment is edited inline afterwards, whenever convenient — matching
     the live, game-state-dependent nature of the comment ("cards in
     hand" at the moment of the misplay), which usually isn't known
     before the event itself.
   - **Events are ordered by entry sequence** — a per (game, side, kind)
     `sequence` integer assigned server-side at creation (array position
     in the write payload), displayed as an ordered list ("Misplay #1",
     "#2", …), not an unordered bag.
   - The single per-game×side `player_note`/`opponent_note` fields from
     the first amendment are **dropped** — superseded by the per-event
     `comment`.
   - **NULL-vs-zero semantics preserved, adapted to events:** the stored
     integer stays nullable at the DB level. Migration 1's backfill
     leaves it `NULL` for every pre-existing (pre-feature) game row —
     mulligan/misplay tracking did not exist for that data, so it must
     stay excluded from `avg()`, not silently read as `0`. Every row the
     *application* writes going forward sets a real integer (`0` when a
     tracked side's event list is genuinely empty) for a `moderator`+
     caller, or `NULL` for a sub-`moderator` caller (for whom the concept
     still doesn't exist at all, distinct from "tracked and zero") — see
     D7's updated enforcement below.
3. **The three free-text "Game N Notes" boxes — kept, not replaced.**
   `opening_hand` / `turning_point` / `final_turn` textareas stay in the
   form exactly as they are today; the new per-game × side counters and
   comment inputs (D2) are added alongside them. This is a pure addition
   rather than the refactor the issue titles describe — the form gets
   busier (three existing textareas plus up to four new counter+comment
   rows), but nothing about existing user habits changes and no history
   is at risk.
4. **Mulligan → hand-size formula — London mulligan.**
   `hand_size = 7 − mulligans`, confirmed as Duel Commander's actual
   rule; `avg_hand_size = 7 − avg(player_mulligans)` over the period.
5. **Where "average hand size" surfaces — session comparison card +
   both PDF reports.** Not per-row in the journal; it is a period
   metric.
6. **Misplay aggregation — same tiles as hand size.** `avg_misplays`
   (per side) computed alongside `avg_hand_size` in
   `compute_period_stats` / `report.py`, surfaced in the same places as
   D5.
7. **Role-gating — included now, at a static floor; enforced
   field-level, not route-level (amended 2026-09-15); the dynamic
   admin toggle is a separate, later item.** Not deferred as originally
   recommended. Two layers, shipped in sequence:
   - **Now, with this feature:** the new mulligan/misplay/comment fields
     are gated at a static `moderator` role floor. **Correction from the
     original plan (Agent 1 + Agent 0 review):** this cannot be a
     route-level `Depends(require_role(Role.moderator))` on the match
     write endpoint, because the gated fields live inside the same
     `games[]` payload as the ordinary game-result/`on_play` fields
     every user can already submit — a route-level dependency would
     reject the **entire** request for a sub-moderator caller, breaking
     the very fields D7 promises stay unchanged for them. Enforcement
     is **field-level, inside `_apply_payload`/schema validation**:
     accept `games[]` from any authenticated caller with `canEdit`, and
     reject the whole request with **403** only if a sub-moderator's
     payload includes a non-empty event list in the gated fields
     (`player_mulligans`/`opponent_mulligans`/`player_misplays`/
     `opponent_misplays` — updated to event lists by D2's second
     amendment). The frontend never renders those fields for a
     sub-moderator `currentUser` in the first place (D2/Consequences
     below), so a 403 here should only ever fire against a stale or
     hand-crafted client — this is a backstop, not the primary UX path.
     `Role`/`require_role` genuinely derive from the verified identity
     token's `role` claim, not a local table (`apps/barrins_api/app/
     dependencies/auth.py` + `app/core/roles.py`, confirmed by Agent 6
     against ADR-20's cutover) — no new backend infrastructure needed
     beyond this one field-level check.
     **For accounts below `moderator`, current behavior is unchanged**
     — they never had this feature, and still don't; nothing they can
     do today stops working. Their games' stored counters are set to
     `NULL` (never `0`), same as a pre-migration historical row — the
     concept doesn't exist for them, which is different from "tracked
     and zero" (D2's second amendment).
   - **Later, a separate work item:** a generic **gate engine** —
     admins get a Goblin Guide screen to open/close any feature flagged
     as "gateable" at runtime, no deploy required, layered on top of
     the static role floor above. Scoped as
     [T16](../v2.0.0-bump/t16-goblin-guide-feature-gates/index.md) in
     the v2.0.0-bump project. This feature's counters become T16's
     first registered gate once T16 ships; until then they are simply
     moderator-gated, always on for that tier.
   This sequencing means 123/124 does **not** block on T16 — it ships
   with the static gate now, and gets the dynamic on/off layer for free
   whenever T16 lands.
8. **Optionality / partial entry — lazy nullable rows.** All new fields
   nullable; a `ts_match_games` row is only created once something is
   entered for that game, so a quick "2-0, done" match stays as cheap as
   today.

## Agent review (2026-09-15)

Before implementation, Agent 0, Agent 1, Agent 2, Agent 3, Agent 4, and
Agent 6 each reviewed this fully-decided plan against their domain.
Consensus: **proceed**, with three corrections folded into D1/D2/D7
above (not left as open questions):

- **Agent 1 (backend) + Agent 3 (DevOps), independently:** the D1
  migration must be split in two, not combined — see D1's amendment.
- **Agent 1, echoed by Agent 0:** D7's original route-level
  `ModeratorUser` gate would have regressed sub-moderator callers'
  existing ability to submit ordinary game results, since the gated
  fields share a payload with ungated ones. Moved to field-level
  enforcement — see D7's amendment.
- **Agent 2 (frontend) and Agent 4 (UX), reconciled against the user's
  clarification of actual usage** (misplays are logged live, one after
  another, as the match is played — not tallied retrospectively):
  dropped the literal `CardTestsSection` list-chrome copy in favor of
  live stepper controls paired with the existing per-game Notes
  textareas — see D2's amendment.
- **Agent 6 (identity):** no objections to D7 or to T16's sequencing;
  confirmed `Role`/`require_role` genuinely derive from the identity
  token claim, not a local table.

No open disagreements remain blocking implementation.

## Consequences

- **Schema — two migrations (amended), plus a new event table (D2's
  second amendment):** Migration 1 adds `ts_match_games` (`game_number`,
  `on_play`, `result`, and four nullable integer counter columns —
  `player_mulligans`/`opponent_mulligans`/`player_misplays`/
  `opponent_misplays`, backend-derived only, see D2) and a new child
  table `ts_match_game_events` (`game_id` FK, `side` [`player`/
  `opponent`], `kind` [`mulligan`/`misplay`], `sequence`, `comment`,
  `created_at`) — one row per individual logged mulligan/misplay, each
  with its own optional comment. Migration 1 backfills every existing
  `ts_matches.game1/2/3`/`on_play` into `ts_match_games`, leaving the
  four new counter columns `NULL` on every backfilled row (mulligan/
  misplay tracking didn't exist for that historical data — `NULL`, not
  `0`, so `avg()` correctly excludes it); no `ts_match_game_events` rows
  are backfilled (there is nothing to backfill — the concept is new).
  The flat `ts_matches` columns are left in place. Migration 2, after a
  production verification window with an explicit row-for-row backfill-
  correctness check, drops `game1/2/3`/`on_play`. §31.3 applies in full
  to both: backup, verify compatibility, test the migration before
  running it on production data. `CheckConstraint`s bound `game_number`
  (1–3), the four counter columns (mirroring the existing
  `rating BETWEEN 1 AND 5` precedent on `ts_card_test_evaluations`), and
  `ts_match_game_events.sequence` (>= 1); `UNIQUE(game_id, side, kind,
  sequence)` keeps each side/kind's event order gap-free and
  addressable. `opening_hand` / `turning_point` / `final_turn` are
  **not** touched by either migration (see History below) — they stay
  put and the table keeps writing them (D3).
- **API contract:** `MatchWrite` (and `PUT`/`POST /matches`) grow a
  nested `games: [{game_number, on_play, result, player_mulligans,
  opponent_mulligans, player_misplays, opponent_misplays}]` array,
  replacing the flat `game1/2/3`/`on_play` fields — **each of the four
  counter fields is now an ordered list of `{comment}` objects**, not an
  integer or a single note string (D2's second amendment); array
  position is the event's `sequence`. `ResponseMatch` mirrors it,
  additionally exposing each event's `id` (stable key for the frontend)
  and the backend-computed integer count per side/kind. `GET
  /sessions/{id}/comparison` and both `report.pdf` responses grow
  `avg_hand_size` / `avg_misplays`. All documented per §21.1.
  **Enforcement is field-level (amended, D7):** `_apply_payload` accepts
  `games[]` from any `canEdit` caller and returns `403` only if a
  sub-`moderator` caller's payload includes a non-empty event list in
  any of the four gated fields — never a route-level `ModeratorUser`
  dependency on the whole endpoint, which would also block the ordinary
  game-result fields sub-moderator callers already write today. For a
  `moderator`+ caller, the stored integer count is always recomputed
  server-side as `len(events)` (real `0` when a side's list is
  genuinely empty); for a sub-`moderator` caller it is always forced to
  `NULL`, never `0` (the concept doesn't exist for them, which must stay
  distinguishable from "tracked and zero" in the average). Editing an
  existing event's comment should update that event row in place
  (matched by `game_id`/`side`/`kind`/`sequence`), not delete-and-reinsert
  the whole list on every `PUT` — otherwise `created_at` resets on every
  autosave for no reason.
- **Stats / read paths rewritten against `ts_match_games` +
  `ts_match_game_events` instead of `game1/2/3`:** `stats.py` (its
  `MatchLike` protocol / game-tally logic — `report.py` itself only
  consumes `stats.py`'s output and needs its DTO/WeasyPrint templates
  extended with the two new derived fields, not a direct rewrite),
  `sharing_merge.py::_from_match`, `matches.py::_apply_payload`. No
  existing winrate/matchup *logic* changes, but every one of these call
  sites changes its read shape — treat this as a rewrite, not a bolt-on.
  `avg_hand_size`/`avg_misplays` read the stored integer counters (not a
  live join+count over `ts_match_game_events`) — that's the whole point
  of keeping the counter. Watch for N+1 query patterns once
  `ts_match_games`/`ts_match_game_events` are joined/loaded across the
  journal, sharing, and report paths (Agent 1 review).
- **Frontend (amended layout, D2, twice):** `MatchFormFields` gains a
  new per-game subcomponent rendering a live stepper (not a `<Select>`)
  for mulligans and misplays per side. Clicking "+1" immediately appends
  a blank-comment event to that side/kind's list (the visible count is
  the list length) and renders it as a new row in a small ordered list
  ("Misplay #1", "#2", …) directly beside that game's existing "Game N
  Notes" textarea, each row carrying its own inline, independently
  editable comment `<Input>` — not `CardTestsSection`'s expand/pinned-
  add-row chrome, and not a single per-game×side comment (D2's first
  amendment, now superseded). The three existing Notes textareas are
  otherwise unchanged (D3). `MatchDraft` / `matchSchema` /
  `matchWriteSchema` move from flat `game1/2/3`/`on_play` fields to a
  `games` array whose four counter fields are event-object arrays, not
  numbers — six files touch the flat shape today (`MatchForm.tsx`,
  `MatchForm.test.tsx`, `MatchJournalSection.tsx`,
  `schemas/tamiyoScroll.ts`, `demo/api/matches.ts`, `statsCore.ts`) and
  must move together in one PR, including the demo API, or it will
  silently drift from the real one (Agent 2 review). New
  `avg_hand_size` / `avg_misplays` tiles in `SessionSummarySection`.
  The stepper+event-list rows only render for a `moderator`+ `currentUser`
  (an ordinal check against the `role` claim, new to the frontend —
  today's only precedent is an exact `role === 'admin'` string match in
  `AppShell.tsx`/`useAdmin.ts`); this is a UX convenience only, per
  §4.1 — the field-level `403` above is the actual enforcement boundary,
  not this client-side check.
- **Sharing:** `sharing_merge._from_match` carries the new
  `ts_match_games` fields (counters) and `ts_match_game_events` rows
  read-only, same as every other match field.
- **History:** `turning_point` / `opening_hand` / `final_turn` columns
  are **kept and still actively written** (D3 — this is now a pure
  addition, not a deprecation; Constitution §11.6 is satisfied
  trivially since nothing is removed).
- **Role-gating:** static `moderator` floor now, enforced field-level
  in `_apply_payload` (no new backend infra); the dynamic admin on/off
  layer is [T16](../v2.0.0-bump/t16-goblin-guide-feature-gates/index.md),
  a separate work item this feature does not block on (D7).
- **Docs + roadmap:** the two roadmap rows (#123 v3+, #124 v3) get
  updated to link here; a status page is created under
  `docs/project/v2.0.0-bump/` (or the next active `-bump/` project) once
  implementation starts.
- **Tests:** backend — round-trip of the nested `games` array (event
  lists included) through `POST`/`PUT`, an edited comment on an existing
  event updates in place rather than resetting `created_at`, Migration
  1's backfill correctness (existing matches' `game1/2/3`/`on_play`
  preserved in `ts_match_games`, counters left `NULL`) verified before
  Migration 2 runs, the new `CheckConstraint` bounds (including
  `ts_match_game_events.sequence`), the derived hand-size/misplay metric
  on the comparison endpoint and the PDFs (confirming `NULL` counters
  are excluded from the average, not read as `0`), sharing-merge carries
  the counters and events, a sub-`moderator` caller gets `403` only when
  a gated field's event list is non-empty (and still succeeds — with
  `NULL` counters, never `0` — when every gated field's list is empty)
  on both `POST` and `PUT`. Frontend — the reworked form submits the
  structured payload (event lists), the journal renders it, partial
  entry (some games blank) works, clicking "+1" appends a blank-comment
  event and the count updates, a non-moderator `currentUser` never
  renders the stepper+event-list rows, the demo API stays in sync with
  the real schema.

## Addendum (2026-09-16) — Play/Draw derivation for games 2/3

Implemented alongside D2/D7 above, during the same build. The user's
request: *"G2 and G3 on the play/draw can be derived from previous game:
G1/G2 loss => G2/G3 on the play; G1/G2 win => G2/G3 on the draw."* This is
the standard "loser chooses" Magic convention, assumed to choose to play.
Resolved via a short clarifying round:

- **A default, not a forced value.** Games 2/3's `on_play` toggle is
  pre-filled from the derived rule but stays manually overridable — the
  rare real match where the loser chooses to draw instead of play is
  still representable. A manual choice is tracked (`onPlayTouched` in the
  frontend draft) and is never silently overwritten by a later edit to
  the previous game's result.
- **No rule for a draw.** When the previous game was a draw (no loser to
  make the choice) or hasn't been played yet, `on_play` stays `null`
  ("unknown") unless the user sets it directly — consistent with the
  column already being nullable per game (D1: only game 1's `on_play` was
  ever historically guaranteed; §"model shape" above).
- **Frontend-only, no backend change.** This is a smart default at
  data-entry time, not a persisted invariant — the value actually saved
  is whatever the user leaves in the field, exactly like manual entry
  today. No new backend logic; `TSMatchGame.on_play` was already nullable
  (D1/Migration 1). Implemented in `MatchForm.tsx` via
  `deriveOnPlay`/`applyDerivedOnPlay`, applied both on initial load
  (`draftFromMatch`) and on every in-session edit (`updateGame`'s
  cascade).
- **Contract bug caught in passing:** the frontend's Zod schema declared
  `on_play: z.boolean()` (non-nullable) for both the response and write
  shapes, while the backend's `on_play` was already legitimately nullable
  (a pre-feature backfilled game 2/3, or a game whose Play/Draw isn't
  known yet). This would have thrown a validation error the first time
  the frontend loaded any match with a null `on_play` on game 2/3 — fixed
  to `z.boolean().nullable()` on both schemas as part of this addendum,
  not a separate issue.
