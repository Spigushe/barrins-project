# S16. Tested Cards → deck change log (Removed/Added Card)

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` + `apps/tamiyo_scroll` | Breaking schema/API change — see Open questions §1 before starting |
| **Initial date** | 2026-08-23 | Drafted 2026-08-23 |
| **Status** | Done (2026-08-24) | Open question 1 resolved — see below |
| **Source** | GitHub issue [#82](https://github.com/Spigushe/barrins-project/issues/82) — "Tested card to become change log" | / |
| **Dependency** | [S15](../s15-decklist-version-diff/index.md) — item 5's inline decklist display reuses S15's UI patterns | / |

---

## Context

**Verified against the code (2026-08-23, `feat/tolaria_news_backend`):**

- `TSCardTest` (`app/models/tamiyo_scroll.py:105-147`, table
  `ts_card_tests`): `id`, `owner_id`, `personal_deck_id` (nullable),
  `tester` (`String(120)`, free text — a person's name, "allows
  crediting a teammate without a Barrin account" per its own
  docstring), `card_name` (`String(255)`, free text, **no FK/
  validation against any card table today**), `opponent_deck_id`
  (nullable), `rating` (1-5, `CheckConstraint`), `notes` (nullable).
  **No `archived_at`** — deletion is a hard `DELETE`
  (`app/api/tamiyo_scroll/card_tests.py`).
- `CardTestWrite`/`ResponseCardTest`
  (`app/schemas/tamiyo_scroll.py:148-158`,
  `app/schemas/responses_tamiyo_scroll.py:114-122`): `tester`,
  `card_name`, `opponent_deck_id`, `rating`, `notes`.
- `pages/suivi-bo3/CardTestsSection.tsx`: table headers today are
  **Nickname | Card | Match-up | Effectiveness | Notes** (line
  329-333) — `Nickname` maps to `tester`, `Card` maps to `card_name`,
  `Effectiveness` maps to `rating` (via `RATING_LABELS` lookup). The
  create-form label for the same `card_name` field is "Card name," not
  "Card" — a pre-existing inconsistency this item's rename work
  touches anyway.
- **Reusable validation utility already exists**:
  `app/services/scripture/card_resolver.py::resolve_card_name(session,
  raw_name)` — normalizes and resolves a raw string against `mj_cards`
  (Unicode fold, accent drift, double-faced-card shorthand, Attraction-
  card exclusion), with a process-local cache invalidated on MTGJSON
  import. Already used by `app/services/tamiyo_scroll/decklist_view.py`
  to resolve decklist card lines against the same reference data — the
  direct pattern to reuse for validating `added_card_name` here.
- `TSUserSettings` already carries per-user opt-in booleans
  (`data_shared`, `metagame_roster_scope`, etc.) — direct precedent
  for the new opt-in fields this item needs.

## Design decisions

- **Full pivot, per the user's 2026-08-23 decision**: `tester` is
  renamed to `removed_card_name`, `card_name` is renamed to
  `added_card_name` (both `String(255)`). This repurposes the entity
  from "who tested which card" into "which card was removed and which
  was added" — a genuine semantic change, not a label-only fix (unlike
  [S12](../s12-uiux-polish/index.md) items 3/4, which were pure
  relabeling with no field rename). `rating`/`notes` are **not**
  touched — the issue doesn't mention them, so "Effectiveness" and
  free-text notes stay exactly as they are today, even though
  "Effectiveness" no longer obviously describes a card swap; a
  possible follow-up, not in scope now (Constitution §39/§48).
- **New validation settings** on `TSUserSettings`:
  `validate_removed_card_in_decklist` (bool, **defaults on** — revised
  2026-08-24, see below) — when on, `removed_card_name` must match a
  card present in the deck's current decklist content;
  `validate_added_card_exists` (bool, default off) — when on,
  `added_card_name` must resolve via the existing
  `resolve_card_name()` utility against `mj_cards` (Magic-only).
  Enforced at write time (`POST`/`PUT /card-tests`), returning a 400
  on violation. When no `TSUserSettings` row exists yet for the owner,
  the column defaults apply (not "everything off") — a fresh account
  that creates a card test before ever visiting Account Settings still
  gets `validate_removed_card_in_decklist` enforced.
- **New opt-in `show_decklist_change_log`** (bool, default off) —
  see "Post-approval additions" below for what it actually gates
  (superseded the original single-list design).
- **Frontend labels are fixed end-to-end while already touching every
  reference**: table headers become "Removed Card" / "Added Card";
  the create-form's pre-existing "Card name" vs. table's "Card"
  mismatch is resolved to a single consistent label at the same time.

## Resolution — Open question 1

**Decided 2026-08-24: option 1, keep existing rows as-is.** Pre-pivot
`ts_card_tests` rows keep their old `tester`/`card_name` values under the
new `removed_card_name`/`added_card_name` column names — a known,
documented migration artifact (see the schema-pivot migration,
`7b7e7c53f1a5_pivot_ts_card_tests_to_removed_added_.py`). No data was
cleared.

## Post-approval additions (2026-08-24 follow-up decision)

Beyond the scope drafted above, the user asked for card-test entries to
be **linked to a real decklist change when they match one**: if a
card-test's `removed_card_name`/`added_card_name` lines up with a card
actually removed/added between two consecutive decklist versions
(anywhere in the deck's version history, matched independently per
half), its `notes` is shown as a comment on that diff line wherever the
diff is browsed (`VersionHistorySection`). A card test that matches
nothing anywhere still surfaces in a standalone list on the current
decklist (`CurrentDecklistSection`) — both gated by
`show_decklist_change_log`. See `app/services/tamiyo_scroll/card_test_matching.py`
and the new `GET /card-tests/change-log` endpoint.

Also decided mid-implementation:

- **`validate_removed_card_in_decklist` defaults ON**, not off as
  originally drafted below — the user changed this after reviewing the
  migration (matches `show_decklist_version_diff`'s opt-out convention).
  `validate_added_card_exists` stays opt-in (default off): it resolves
  against `mj_cards`, Magic-only, so it would reject every card name for
  a non-Magic deck if it defaulted on. The Account Settings copy for
  that switch says so explicitly.

## ⚠️ Open question 1 — blocking, not guessed (resolved above)

**Existing `ts_card_tests` rows predate this pivot.** The app has
shipped releases (`1.0.0`, `2.0.0-alpha`) and may already hold real
user data in this table. Renaming `tester`→`removed_card_name` and
`card_name`→`added_card_name` doesn't make old values *mean*
"removed/added card" — a row created under the old semantics just
ends up mislabeled under the new column names. Per Constitution §4.4
(backward compatibility, explicit approval before a breaking change)
and this project's own escalate-don't-guess convention, this item
**does not start implementation** until the user picks one:

1. **Keep existing rows as-is**, mislabeled, documented as a known
   migration artifact in the release notes/CHANGELOG.
2. **Clear `ts_card_tests`** as part of the migration (old test-
   feedback data is discarded, not reinterpreted).

(Superseded — kept for record. Decision: option 1, above.)

## Done statement

- `TSCardTest.removed_card_name`/`added_card_name` replace
  `tester`/`card_name`; `rating`/`notes` unchanged. Pre-pivot rows keep
  their old values under the new column names (accepted migration
  artifact).
- `POST`/`PUT /card-tests` enforce `validate_removed_card_in_decklist`
  (default **on**) / `validate_added_card_exists` (default off) when
  the owner has it enabled — including when no `TSUserSettings` row
  exists yet, via the column defaults — returning a 400 with a clear
  message on violation.
- `CardTestsSection`'s table and create form read "Removed Card"/
  "Added Card" consistently in both places (fixing the pre-existing
  Nickname/Card-name inconsistency); the stale "prefill with my display
  name" autofill (a leftover from the old "who's testing" semantics) is
  removed, not renamed.
- With `show_decklist_change_log` enabled: a card test that matches a
  real decklist change (anywhere in version history) shows its note as
  a comment on that diff line in `VersionHistorySection`; a card test
  that matches nothing shows up in a standalone list on
  `CurrentDecklistSection`.

## Tasks

### 1. Schema pivot

- [x] **Resolve Open question 1 first.**
- [x] Migration: rename `tester`→`removed_card_name`,
      `card_name`→`added_card_name` (adjust `removed_card_name`'s
      length to 255, matching `added_card_name`'s convention).
- [x] Update `CardTestWrite`/`ResponseCardTest` schemas.

### 2. Validation settings

- [x] Migration: `TSUserSettings.validate_removed_card_in_decklist`
      (default `true`), `validate_added_card_exists` (default `false`).
- [x] `UserSettingsUpdate`/`ResponseUserSettings`: expose both.
- [x] `POST`/`PUT /card-tests`: enforce `removed_card_name` against
      the deck's current decklist content when opted in.
- [x] `POST`/`PUT /card-tests`: enforce `added_card_name` via
      `resolve_card_name()` when opted in.
- [x] `AccountSettingsDialog`: two new Switches.

### 3. Frontend renames

- [x] `CardTestsSection.tsx`: table headers, create-form labels/ids,
      and any bound field names (`newDraft.tester`→
      `newDraft.removedCardName`, etc.) — consistent end to end.
- [x] Inline error display for the two new validation failures.

### 4. Change-log display

- [x] Migration: `TSUserSettings.show_decklist_change_log` (bool,
      default `false`).
- [x] `AccountSettingsDialog`: new Switch.
- [x] `app/services/tamiyo_scroll/card_test_matching.py` (new): matches
      card-test entries against decklist diffs, per-diff and across a
      deck's whole version history.
- [x] `GET .../versions/{id}/diff` response gains `card_test_notes` per
      card line (always computed, frontend-gated display).
- [x] New `GET /card-tests/change-log` endpoint: a deck's card tests
      that don't match any diff anywhere in its history.
- [x] `VersionHistorySection`: renders matched notes under their diff
      line when the setting is on.
- [x] `CurrentDecklistSection`: renders the unmatched-entries list when
      the setting is on.

## UAT (manual)

- [x] With both validations off → creating a card test accepts any
      text in Removed/Added Card.
- [x] "Removed Card must be in decklist" (on by default) → submitting a
      card not present in the deck's current decklist is rejected with
      a clear error; a card that is present succeeds.
- [x] "Added Card must exist" → submitting an unresolvable card name is
      rejected; a real card name succeeds.
- [x] Change-log display on → a card test matching a real version-to-
      version change shows its note as a comment on that diff line in
      Version history; a card test matching nothing shows up in the
      current decklist's untracked list instead.
- [x] Table and create-form labels read "Removed Card"/"Added Card"
      consistently in both places.

## Non-regression tests

- Backend: `test_card_tests.py`, `test_settings.py`,
  `test_personal_decks.py` (diff + decklist-coloring), and
  `test_decklist_coloring.py` updated for the renamed fields and the
  new default; cases added for both validations (on/off) and for the
  new change-log endpoint/matching. Full suite green
  (`uv run pytest`), `ruff format`/`ruff check`, `ty check` clean.
- Frontend: `CardTestsSection.test.tsx`, `AccountSettingsDialog.test.tsx`
  updated; new `VersionHistorySection.test.tsx`,
  `CurrentDecklistSection.test.tsx`. `tsc -b`, `oxlint`, `prettier
  --check` clean on all touched files.
- Pre-existing gap, unrelated to S16 (confirmed via `git stash` on the
  base branch): `src/demo/api/personalDecks.ts` never implemented
  `getDecklistVersionView`/`getDecklistVersionDiff` (S15 feature),
  failing `demoApi.test.ts`'s module-shape check and `tsc -b`. Fixed as
  a follow-up in this same working tree once it surfaced in CI:
  `getDecklistVersionView` parses a version's saved content with a
  `neutral` line status (versions carry no per-line status in the demo
  store); `getDecklistVersionDiff` mirrors `diff_decklist_cards` (name
  matched quantities/commander flag) and a small LCS-based line diff
  for unparsed lines, `card_test_notes` always empty (same reasoning as
  `listCardTestChangeLog`'s demo stub — no DB-backed name resolution in
  the browser). `tsc -b`, `oxlint`, `prettier --check`, and
  `demoApi.test.ts` (42 passed) all clean afterward.

## See also

- [s15-decklist-version-diff/](../s15-decklist-version-diff/index.md) —
  `VersionHistorySection`'s diff rendering, extended here with matched
  card-test comments.
- `app/services/scripture/card_resolver.py` — the existing
  `resolve_card_name()`/new `resolve_card_name_or_raw()` utilities
  reused for both the Added-Card validation and the diff-matching
  service.
- `app/services/tamiyo_scroll/card_test_matching.py` — new: matches
  card-test entries to decklist diffs.
