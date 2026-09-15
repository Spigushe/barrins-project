# #123 + #124 — Structured per-game match log (mulligans, misplays, both sides)

[← Back to issue-scoping index](README.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` + `apps/tamiyo_scroll` | `ts_matches` data model + `MatchFormFields` + stats/report |
| **Initial date** | 2026-09-08 | Scoped from the code, not yet decided |
| **Status** | 🔲 **Scoped — decision needed** | Do not implement before the Decisions section is answered |
| **Source** | GitHub issues [#123](https://github.com/Spigushe/barrins-project/issues/123) (2026-09-04) + [#124](https://github.com/Spigushe/barrins-project/issues/124) (2026-09-04) | Both authored by the repo owner; both say *"Refactor match log form"* verbatim |
| **Roadmap** | [#124 → v3](../../content/front/tamiyo_scroll/roadmap.md) ("error count + comment on both sides"); [#123 → v3+](../../content/front/tamiyo_scroll/roadmap.md) ("mulligan counts per side, one row per game — likely deserves its own scoping pass") | This page is that pass |
| **Related** | roadmap v3 "winrate starting/not-starting per match", v3+ "module selection for new game screen", Constitution §13.6 (`moderator` tier), §45.2, §48 | |

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
| Player mulligans | game × side (player) | #123 |
| Opponent mulligans | game × side (opponent) | #123 |
| Player misplay count | game × side (player) | #124 |
| Opponent misplay count | game × side (opponent) | #124 |
| Misplay comment | game (× side?) — replaces the free-text box | #124 |

"Average hand size over a period/session" (#123) is **derived**, not
stored: with the London mulligan (Duel Commander's rule) N mulligans →
keep 7, bottom N → hand size `7 − N`, so
`avg_hand_size = 7 − avg(player_mulligans)` over the period. Backend-owned.

## Alternatives for the model

### A. New `ts_match_games` child table (roadmap's steer)

`(id, match_id FK, game_number 1..3, player_mulligans, opponent_mulligans,
player_misplays, opponent_misplays, player_note, opponent_note)` — one
row per game actually played.

- **Hybrid (recommended):** keep `game1/2/3` and `on_play` on
  `ts_matches` exactly as they are (every stats query reads them today —
  untouched, zero regression risk), add `ts_match_games` **only** for
  the new mulligan/misplay/note data. A game row is created lazily when
  the user fills in any of its new fields.
- **Full:** also move `game1/2/3` results (and a per-game `on_play`)
  into the child table, deprecating the flat columns.
- **Trade-offs:** the child table is the only shape in which #123's "one
  row per game" reads naturally, and it absorbs future per-game
  `on_play` / per-game notes without another migration. Hybrid keeps the
  blast radius tiny (no stats rewrite, additive migration, no backfill).
  Full is cleaner long-term but rewrites every query that reads
  `game1/2/3` and needs a data migration — a separate, larger item.

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

## Recommendation

**Alternative A, hybrid.** New `ts_match_games` table for the
mulligan/misplay/note data only; `ts_matches.game1/2/3` and `on_play`
left exactly as they are. Additive migration, no backfill, no stats
rewrite. Full normalization of `game1/2/3` into the child table is a
worthwhile but separate follow-up (and would pair naturally with the
roadmap's "winrate starting/not-starting per match" v3 item, which wants
per-game `on_play`).

## Decisions needed (flagged, not guessed)

1. **Model shape.** `ts_match_games` child table (recommended, hybrid)
   vs. flat columns vs. JSONB.
2. **Misplay comment granularity.** #124 wants to replace the free-text
   box with tracking. Is the comment **per game** (one box per game,
   replacing today's three "Game N Notes" boxes) or **per game × side**
   (two boxes per game)? Recommendation: per game × side is what "track
   both side's misplays … game per game" implies, but it's four boxes on
   screen for a full BO3 — confirm.
3. **What happens to the three free-text "Game N Notes" boxes?** The
   roadmap's #124 note says the change *"removes the 'turning point'
   block from the tracker UI"* while keeping the `turning_point` column
   for history. Options: (a) drop all three note textareas, replace with
   the structured counters + one comment field per game; (b) keep the
   textareas *and* add counters (pure addition, busier form); (c) keep
   the columns, hide the inputs, surface old data read-only in the
   journal. Recommendation: (a) — the issues explicitly ask for a
   *refactor*, and the columns stay in the schema either way (no data
   loss).
4. **Mulligan → hand-size formula.** Confirm the London mulligan
   assumption (`hand_size = 7 − mulligans`), i.e. Duel Commander rules.
   If a "Paris"/other rule is ever in play the formula differs.
5. **Where does "average hand size" surface?** Session comparison card,
   session PDF, deck-level PDF, the Match journal per-row? Recommendation:
   session comparison card + both PDF reports (it's a period metric);
   not per-row.
6. **Misplay aggregation.** Alongside hand size, do the issues want
   "average misplays per game, per side, over the period" surfaced the
   same places? #124's "in the long run" says yes. Confirm the exact
   tiles.
7. **Role-gating ("close circle").** Both issues list it only as a
   *"Possible evolution"*. Constitution §48 says don't build unused
   gating prematurely, and §13.6 makes any such gate backend-owned.
   Recommendation: **out of scope** for the first implementation — the
   counters are available to anyone with `canEdit`. Revisit as its own
   item (it overlaps the roadmap's "module selection for new-game
   screen" v3+ entry) if wanted.
8. **Optionality / partial entry.** All new fields nullable, a game row
   only created when something is entered (so a quick "2-0, done" match
   stays as cheap as today)?

## Consequences

- **Schema:** one additive migration — new `ts_match_games` table
  (recommendation) or N nullable columns on `ts_matches`. No backfill,
  no destructive change; `game1/2/3` and `on_play` untouched under the
  hybrid.
- **API contract:** `MatchWrite` (and `PUT`/`POST /matches`) grow a
  nested `games: [{game_number, player_mulligans, …}]` array (or flat
  fields); `ResponseMatch` grows the same. `GET /sessions/{id}/comparison`
  and both `report.pdf` responses grow the new derived metric(s).
  All documented per §21.1.
- **Stats:** one new backend-owned calculation (`avg_hand_size`,
  optionally `avg_misplays`) added to `compute_period_stats` /
  `report.py`. No existing winrate/matchup logic changes.
- **Frontend:** `MatchFormFields` reworked — structured number inputs
  per game/side, the free-text boxes removed or kept per D3;
  `MatchDraft` / `matchSchema` / `matchWriteSchema` grow; `MatchJournalSection`
  row/expand view shows the new data; new stat tiles in
  `SessionSummarySection`.
- **Sharing:** `sharing_merge._from_match` carries the new fields
  read-only, same as every other match field.
- **History:** `turning_point` / `opening_hand` / `final_turn` columns
  are **kept** (Constitution §11.6 — no column removal without a
  migration plan; and the roadmap explicitly wants the historical text
  retained). Only their inputs change.
- **Docs + roadmap:** the two roadmap rows (#123 v3+, #124 v3) get
  updated to link here; a `v3.0.0-bump/`-style status page is created if
  and when an approach is chosen.
- **Tests:** backend — round-trip of the nested game data through
  `POST`/`PUT`, the derived hand-size/misplay metric on the comparison
  endpoint and the PDFs, sharing-merge carries the fields. Frontend —
  the reworked form submits the structured payload, the journal renders
  it, partial entry (some games blank) works.
