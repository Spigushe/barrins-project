# S16. Tested Cards → deck change log (Removed/Added Card)

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` + `apps/tamiyo_scroll` | Breaking schema/API change — see Open questions §1 before starting |
| **Initial date** | 2026-08-23 | Drafted 2026-08-23 |
| **Status** | Not started — **blocked on Open question 1** | / |
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
- **New opt-in validation settings** on `TSUserSettings`:
  `validate_removed_card_in_decklist` (bool) — when on,
  `removed_card_name` must match a card present in the deck's current
  decklist content; `validate_added_card_exists` (bool) — when on,
  `added_card_name` must resolve via the existing
  `resolve_card_name()` utility against `mj_cards`. Both default off,
  enforced at write time (`POST`/`PUT /card-tests`), returning a 400
  on violation.
- **New opt-in `show_decklist_change_log`** (bool) — when on, the
  change-log entries (with their `notes` as user comments) render
  inline within the decklist view (`CurrentDecklistSection`), reusing
  [S15](../s15-decklist-version-diff/index.md)'s version-display UI
  pattern rather than inventing a new one.
- **Frontend labels are fixed end-to-end while already touching every
  reference**: table headers become "Removed Card" / "Added Card";
  the create-form's pre-existing "Card name" vs. table's "Card"
  mismatch is resolved to a single consistent label at the same time.

## ⚠️ Open question 1 — blocking, not guessed

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

Confirm before implementation begins.

## Done statement

- `TSCardTest.removed_card_name`/`added_card_name` replace
  `tester`/`card_name`; `rating`/`notes` unchanged.
- `POST`/`PUT /card-tests` enforce
  `validate_removed_card_in_decklist`/`validate_added_card_exists` when
  the owner has opted in, returning a 400 with a clear message on
  violation; both checks are bypassed when their setting is off.
- `CardTestsSection`'s table and create form read "Removed Card"/
  "Added Card" consistently in both places (fixing the pre-existing
  Nickname/Card-name inconsistency).
- With `show_decklist_change_log` enabled, `CurrentDecklistSection`
  renders the change-log entries (removed/added card + comment)
  inline, using S15's version-display pattern.

## Tasks

### 1. Schema pivot

- [ ] **Resolve Open question 1 first.**
- [ ] Migration: rename `tester`→`removed_card_name`,
      `card_name`→`added_card_name` (adjust `removed_card_name`'s
      length to 255, matching `added_card_name`'s convention).
- [ ] Update `CardTestWrite`/`ResponseCardTest` schemas.

### 2. Validation settings

- [ ] Migration: `TSUserSettings.validate_removed_card_in_decklist`,
      `validate_added_card_exists` (both bool, default `false`).
- [ ] `UserSettingsUpdate`/`ResponseUserSettings`: expose both.
- [ ] `POST`/`PUT /card-tests`: enforce `removed_card_name` against
      the deck's current decklist content when opted in.
- [ ] `POST`/`PUT /card-tests`: enforce `added_card_name` via
      `resolve_card_name()` when opted in.
- [ ] `AccountSettingsDialog`: two new Switches.

### 3. Frontend renames

- [ ] `CardTestsSection.tsx`: table headers, create-form labels/ids,
      and any bound field names (`newDraft.tester`→
      `newDraft.removedCardName`, etc.) — consistent end to end.
- [ ] Inline error display for the two new validation failures.

### 4. Inline change-log display

- [ ] Migration: `TSUserSettings.show_decklist_change_log` (bool,
      default `false`).
- [ ] `AccountSettingsDialog`: new Switch.
- [ ] `CurrentDecklistSection`: render change-log entries (reusing
      S15's version-display pattern) when enabled.

## UAT (manual)

- [ ] With both validation settings off (default) → creating a card
      test accepts any text in Removed/Added Card, as today.
- [ ] Enable "Removed Card must be in decklist" → submitting a card
      not present in the deck's current decklist is rejected with a
      clear error; a card that is present succeeds.
- [ ] Enable "Added Card must exist" → submitting an unresolvable card
      name is rejected; a real card name succeeds.
- [ ] Enable the decklist change-log display → the current decklist
      view shows the change-log entries with their comments inline.
- [ ] Table and create-form labels read "Removed Card"/"Added Card"
      consistently in both places.

## Non-regression tests

- Backend: existing `card_tests.py` create/update/list/delete tests
  updated for the renamed fields; add cases for both opt-in
  validations (on and off).
- Backend: confirm `resolve_card_name()`'s existing test coverage
  (from its decklist-line use) generalizes correctly to this new call
  site — same function, new caller.
- Frontend: existing `CardTestsSection` tests updated for the renamed
  labels/field bindings.

## See also

- [s15-decklist-version-diff/](../s15-decklist-version-diff/index.md) —
  UI pattern reused by item 4 (inline change-log display).
- `app/services/scripture/card_resolver.py` — the existing
  `resolve_card_name()` utility reused for the Added-Card validation.
