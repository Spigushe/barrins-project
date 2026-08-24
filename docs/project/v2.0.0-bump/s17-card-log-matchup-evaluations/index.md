# S17. Card log / match-up evaluation split + inline decklist change display

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` + `apps/tamiyo_scroll` | Breaking schema/API change — splits `TSCardTest` into two entities |
| **Initial date** | 2026-08-24 | Drafted 2026-08-24 |
| **Status** | 🔲 **Not started — scoping resolved 2026-08-24** | All 4 open questions decided by the user; ready for implementation |
| **Source** | User-authored draft note (`docs/project/v2.0.0-bump/new-s17.md`), formalized into this page and removed — **not** a GitHub issue like S13-S16 (checked: no open issue past #82 exists in this repo as of 2026-08-24) | / |
| **Dependency** | [S16](../s16-tested-card-changelog/index.md) — splits the same `TSCardTest` table S16 just pivoted, and item 3 reuses S16's `card_test_matching.py` pattern to decide which decklist line a card log targets | / |

---

## Context

**Verified against the code (2026-08-24, `feat/tolaria_news_backend`):**

- `TSCardTest` (`app/models/tamiyo_scroll.py:105-158`, table `ts_card_tests`)
  today is a **single flat row** combining both what item 1 calls the "card
  log" and its evaluation: `removed_card_name`, `added_card_name`,
  `personal_deck_id`, `owner_id`, `notes`, `created_at`, plus
  `opponent_deck_id` (nullable — "the matchup is optional") and `rating`
  (1-5, required). `CardTestWrite`/`ResponseCardTest`
  (`app/schemas/tamiyo_scroll.py:176-186`,
  `app/schemas/responses_tamiyo_scroll.py:120-128`) mirror this flat shape
  — there is no separate evaluation entity anywhere today.
- `CardTestsSection.tsx`'s creation form (lines 254-330) collects **all
  five** fields at once — Removed Card, Added Card, the `MatchupDeckField`
  combobox (opponent deck), an Effectiveness `<Select>` (rating), and
  Notes. Item 1 asks to split creation (base fields only) from evaluation
  (match-up + effectiveness), the latter only addable from the edit form,
  one card log to many evaluations.
- `decklist_coloring.color_decklist()` (`app/services/tamiyo_scroll/
  decklist_coloring.py:40-67`) today aggregates ratings **by
  `added_card_name.lower()` across every `TSCardTest` row scoped to the
  deck** (callers fetch by `personal_deck_id`, e.g.
  `personal_decks.py:589-596`), majority rule: `>=4` majority → `validated`
  (green), `<=2` majority → `rejected` (red), otherwise `in_test`
  (orange); no color (`neutral`) when nothing matches. **Two unrelated
  card-test rows that happen to add the same card name are merged into one
  aggregate today** — this pooling behavior is kept unchanged by the
  split (Design decisions below).
- `LineStatus`/`DecklistLineStatus` is a closed 4-value type today
  (`"validated" | "rejected" | "in_test" | "neutral"`, mirrored in
  `apps/tamiyo_scroll/src/lib/mtg-format.ts`'s
  `DECKLIST_LINE_STATUS_LABELS`/`_BG_CLASS`/`_TEXT_CLASS`). **No
  blue/"pending" state exists anywhere today** — adding it is a real,
  end-to-end type change (Python `Literal`, the TS union, and all three
  label/class maps), not just a new CSS color.
- `GET /cards/search-by-name/{name}` (`app/api/general/mtgjson.py:214-260`)
  is, despite its name, an **exact** full-name-or-face-name lookup
  (`Card.name == name` / `Card.face_name == name`) that can return several
  *distinct* cards for one exact string — it is not a prefix/substring
  search. **Item 2's "3 characters starts the search, dropdown populated
  with matching names" has no existing endpoint to call** — a genuinely
  new partial-match search route is needed.
- `MatchupDeckField` (`CardTestsSection.tsx:60-168`) — an existing
  `Popover`+`Command` combobox filtering an already-fetched in-memory list
  — is the closest UI precedent for item 2's two new card-name dropdowns,
  though it filters client-side data, not a live backend search (the
  Added-Card dropdown needs the new endpoint above; the Removed-Card
  dropdown can reuse the pattern client-side, since the current decklist
  is already fetched by the tab).
- `DecklistCardRow`, rendered per card from `DecklistViewContent.tsx`
  (`Qty | Name | Color pips | Popover` columns, shared by
  `CurrentDecklistSection` and S15's `VersionHistorySection` expand-in-
  place view) is the existing per-card row component. Item 3's inline
  removed→added display is a change to **this** component, not a new one.
- `CurrentDecklistSection.tsx:79-94` already renders a **separate** "Card
  change being considered in this version" block for card tests unmatched
  to any real decklist diff (S16's `show_decklist_change_log` feature) —
  two stacked lines (`- removed_card_name` in red, `+ added_card_name` in
  green), not one row with a strikethrough+arrow. Item 3 reads as
  replacing/extending this with an inline single-row treatment inside
  `DecklistCardRow` itself, reusing S16's
  `app/services/tamiyo_scroll/card_test_matching.py` logic to decide
  whether a given decklist line is the target of a pending change.

## Design decisions

- **Client-side dropdowns are presentation only.** S16's opt-in backend
  validations (`TSUserSettings.validate_removed_card_in_decklist`,
  default on; `validate_added_card_exists`, default off) stay the
  enforcement mechanism, unchanged by item 2 — the new dropdowns make
  hitting a valid name easier, they don't replace server-side validation.
- **Hover-card images reuse the existing Scryfall proxy** (`GET
  /api/v1/cards/{scryfall_id}/image`, built for S4) for both the old and
  new card, rather than a new image source.
- **Evaluation entity (Open question 1, resolved 2026-08-24 — option A):**
  new `TSCardTestEvaluation` table, FK to `ts_card_tests.id`, columns
  `opponent_deck_id` (now **required** — unlike today's optional field on
  `TSCardTest`, since an evaluation is specifically a match-up), `rating`
  (1-5), and its own optional `notes`. `TSCardTest` drops
  `opponent_deck_id`/`rating` entirely, **keeps its own `notes`** (one
  shared, overall note about the swap, independent of any one
  evaluation's note) plus `removed_card_name`/`added_card_name`/
  `personal_deck_id`/`owner_id`/`created_at`. A card log has zero, one, or
  many evaluations.
- **Decklist-coloring aggregation scope (Open question 2, resolved
  2026-08-24 — kept today's behavior):** unchanged — a decklist line's
  color pools evaluations from **every** card log (for the deck) whose
  `added_card_name` matches that line, majority rule as today (`_line_
  status`'s `>=4`/`<=2` rule, reused as-is). A newer card log does not
  supersede an older one sharing the same added name; their evaluations
  merge into one calculation, same as `color_decklist` does today for
  flat `TSCardTest` rows.
- **"pending"/blue (Open question 3, resolved 2026-08-24 — reframed, not
  guessed from either originally-drafted option):** "pending" is not
  about evaluation count on the *added* card — it's whether the swap has
  actually been executed in the decklist yet. A decklist line is
  **pending** (blue) when its card name matches a card log's
  `removed_card_name` **and** that name is still present in the deck's
  *current* decklist content (i.e. the swap hasn't been saved into a new
  decklist version). That line renders per item 4 below: the removed name
  struck-through, an arrow, and the added name inline — not a separate
  list entry. Once a new decklist version drops the removed card, that
  line no longer matches "pending" (the card is gone); the added card's
  own line — once it actually appears in a decklist version — is colored
  by the evaluation-based majority rule (`validated`/`rejected`/
  `in_test`/`neutral`) exactly as before. **"pending" and the evaluation-
  based states are two independent axes**, not a merge or replacement of
  `in_test` — `in_test` keeps its existing meaning untouched. This also
  resolves item 3's "the old card name should be highlighted in blue" —
  that *is* the pending indicator, applied specifically to the removed
  name.
- **Migration (Open question 4, resolved 2026-08-24 — option A):**
  backfill — one `TSCardTestEvaluation` row created per existing
  `ts_card_tests` row, carrying `opponent_deck_id`/`rating` over
  unchanged (each pre-S17 row degenerates into a card log with exactly
  one evaluation). No feedback data lost, mirroring S16's own "keep
  existing rows as-is" precedent.

## Done statement

- `TSCardTest` becomes a pure removed/added-name identity (plus its own
  overall `notes`); `TSCardTestEvaluation` (new table) carries
  `opponent_deck_id` (required), `rating`, and its own optional `notes`,
  many per card log. The creation form only collects base fields
  (Removed Card, Added Card, Notes); evaluations are only addable from
  the edit form.
- Decklist-line coloring: a line matching a card log's `removed_card_name`
  still present in the current decklist renders **pending** (blue,
  struck-through old name → arrow → new name, both card images on
  hover). A line matching an `added_card_name` (once actually present in
  a decklist version) is colored `validated`/`rejected`/`in_test`/
  `neutral` from the pooled majority of every evaluation across every
  card log sharing that added name — unchanged from today's aggregation,
  just fed by evaluations instead of flat rows.
- Existing `ts_card_tests` rows keep working unchanged: each gets exactly
  one backfilled evaluation carrying its old `opponent_deck_id`/`rating`.
- Removed-Card dropdown lists the current decklist's card names
  (client-side, already-fetched data); Added-Card dropdown calls a new
  partial-match card-name search endpoint (3-character minimum), with a
  not-found warning; free-text entry still works, gated by S16's existing
  opt-in validations at write time.

## Tasks

### 1. Schema split

- [ ] Migration: new `TSCardTestEvaluation` table (`opponent_deck_id`
      required, `rating`, optional `notes`, FK to `ts_card_tests.id`);
      `TSCardTest` drops `opponent_deck_id`/`rating`, keeps `notes`.
- [ ] Backfill: one evaluation row per existing `ts_card_tests` row,
      carrying its old `opponent_deck_id`/`rating`.
- [ ] New `CardTestEvaluationWrite`/`ResponseCardTestEvaluation` schemas;
      `CardTestWrite`/`ResponseCardTest` narrowed to base fields.
- [ ] `POST`/`PUT`/`DELETE /card-tests/{test_id}/evaluations[/{id}]`
      routes, scoped under an owned card log (mirrors the existing
      `_get_owned_card_test` ownership check).

### 2. Decklist coloring

- [ ] `color_decklist()` reworked: (a) evaluation-based majority coloring
      now pools `TSCardTestEvaluation` rows across every matching card log
      (unchanged aggregation, new data source), (b) new `pending` pass —
      a line matching a card log's `removed_card_name` still present in
      the current decklist content renders `pending`, independent of the
      evaluation-based pass.
- [ ] New `pending` value threaded through: Python `Literal`,
      `ColoredLine`/`ResponseDecklistLine`, the mirrored TS
      `DecklistLineStatus` union, and `DECKLIST_LINE_STATUS_LABELS`/
      `_BG_CLASS`/`_TEXT_CLASS` in `mtg-format.ts`.
- [ ] Unit tests: pending detection (present/absent in current decklist),
      pooled evaluation majority across multiple card logs sharing an
      added name, and the two axes never colliding on one line.

### 3. Name validation UX (item 2)

- [ ] New backend partial-match card-name search endpoint (`GET
      /cards/search-by-name` doesn't fit — see Context; needs its own
      route, e.g. prefix/substring `ILIKE` over `Card.name`, 3-character
      minimum enforced client-side).
- [ ] Removed-Card dropdown: client-side combobox over the current
      decklist's card names (already fetched by the tab via
      `decklist-view`), reusing `MatchupDeckField`'s combobox pattern.
- [ ] Added-Card dropdown: same combobox pattern, backed by the new
      search endpoint; "not found" warning when the query returns no
      match. Free-text entry stays possible — S16's opt-in validations
      remain the actual enforcement (Design decisions above).

### 4. Inline decklist display (item 3)

- [ ] `DecklistCardRow`: when a decklist line's card name matches a card
      log's `removed_card_name` still present in the current decklist,
      render the removed name struck-through + blue, a right arrow, and
      the added name — same row, not a separate list. Reuses S16's
      `card_test_matching.py` pattern to find the relevant card log.
- [ ] Hover on either name shows both cards' images (existing Scryfall
      proxy).
- [ ] Color pips/popover data reflect the **added** card, not the
      removed one.
- [ ] Added name's color (once it actually appears in a decklist version)
      follows the pooled evaluation-majority rule, unrelated to pending.
- [ ] `CurrentDecklistSection.tsx`'s separate "Card change being
      considered" block (lines 79-94) is retired — the inline row display
      replaces it for changes matched to the current decklist.

## UAT (manual)

- [ ] Creating a card log without any evaluation succeeds (base fields —
      Removed Card, Added Card, Notes — only); while the removed card is
      still in the current decklist, that line shows pending/blue with
      the struck-through-name → arrow → new-name treatment.
- [ ] Adding a match-up evaluation from the edit form, then a second one
      for a different opponent deck, both attach to the same card log;
      each can carry its own note independent of the card log's note.
- [ ] Saving a new decklist version that actually drops the removed card
      and adds the new one: the line stops showing pending; the added
      card's line instead shows the evaluation-based color.
- [ ] Two different card logs that both added the same card name: their
      evaluations pool into one majority color on that card's line.
- [ ] Typing 3+ characters in the Added-Card dropdown returns matching
      names; an unmatched name shows the warning.
- [ ] Hovering either name in a pending row shows its card image.

## Non-regression tests

- Backend: `test_card_tests.py`, `test_decklist_coloring.py`,
  `test_personal_decks.py`/`test_teams.py`/`test_sessions.py` (every
  `color_decklist` call site) need updates for the split schema and the
  new `pending` state.
- Frontend: `CardTestsSection.test.tsx` and any `DecklistCardRow`/
  `DecklistViewContent` tests need updates for the new form shape (no
  match-up/rating at creation) and the new inline pending-row rendering.

## See also

- [s16-tested-card-changelog/](../s16-tested-card-changelog/index.md) —
  the `TSCardTest` pivot and `card_test_matching.py` this item builds on
  and further splits.
- [s15-decklist-version-diff/](../s15-decklist-version-diff/index.md) —
  `DecklistViewContent`/`DecklistCardRow`, reused/extended here for the
  inline change display.
- [s4-decklist-display-redesign/](../s4-decklist-display-redesign/index.md) —
  origin of the Scryfall image proxy reused for item 3's hover images.
- [s18-deletion-defaults-to-archive/](../s18-deletion-defaults-to-archive/index.md) —
  the project-wide archive-not-delete policy (Constitution §11.8)
  surfaced by this item's own first-cut `DELETE /card-tests/{id}`
  cascading to destroy evaluations; `TSCardTest`/`TSCardTestEvaluation`
  were corrected here the same day, the rest of the domain is S18's scope.
