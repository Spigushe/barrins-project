# #141 — Archive card log

[← Back to issue-scoping index](README.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` + `apps/tamiyo_scroll` | Card-log CRUD + the decklist-diff / change-log surfaces |
| **Initial date** | 2026-09-08 | Scoped from the code |
| **Status** | 🟡 **Approach decided 2026-09-08 — 3 minor questions open** | See "Decided approach" + "Remaining open questions" |
| **Source** | GitHub issue [#141](https://github.com/Spigushe/barrins-project/issues/141), reported 2026-09-07 | Author: repo owner |
| **Roadmap** | Not on the [feature roadmap](../../content/front/tamiyo_scroll/roadmap.md) | Post-dates the S16/S17 card-log work |
| **Related** | `v2.0.0-bump/s16-tested-card-changelog/`, `s17-card-log-matchup-evaluations/`, `s18-deletion-defaults-to-archive/` (⚠️ not started) | See "Interaction with S18" |

---

## The request, verbatim

> My card log is becoming longer and longer and I can only delete
> elements, not archive them.
>
> 1. Archive logs would help keep comments and evaluations so it stay in
>    the decklist diff block.
> 2. Delete would happen from archived lines

## Context — verified against the code (2026-09-08, `staging`)

### The card log's one destructive action already archives

The "Tested cards — card log" table
([`CardTestsSection.tsx`](../../../apps/tamiyo_scroll/src/pages/suivi-bo3/CardTestsSection.tsx))
has a single `✕` per row, wired to `setPendingDelete(test)`, a
`ConfirmDialog` ("It will disappear from this deck's test feedback,
along with any evaluations logged against it."), then
`deleteTest.mutateAsync(id)`.

That calls `DELETE /card-tests/{id}`
([`delete_card_test`](../../../apps/barrins_api/app/api/tamiyo_scroll/card_tests.py)),
which **already soft-deletes**: stamps `TSCardTest.archived_at`, commits,
never a SQL `DELETE` (Constitution §11.8; the S17 same-day correction
after an early hard delete cascaded away every evaluation). The log's
evaluations are left in the database, only hidden by the read filter.

So "Delete" is really "archive with no way back and no visibility". The
gaps: no archived view, no restore, and archiving currently strips the
log from the one surface the user wants it to keep feeding.

### `TSCardTest.archived_at` already exists

`archived_at` (nullable `DateTime(timezone=True)`) is on both
`TSCardTest` and `TSCardTestEvaluation`. The evaluations of an archived
*log* are **not** touched when the log is archived — they keep their own
`archived_at IS NULL`, so "keep comments and evaluations" needs no data
change on that path, only a read-filter change.

### "Archived" currently means "invisible everywhere"

| Surface | Code | Today | After #141 |
| --- | --- | --- | --- |
| Working card-log table (`GET /card-tests`) | `card_tests.py` `list_card_tests` — `archived_at.is_(None)`, comment *"no `include_archived` toggle yet"* | Hidden | **Hidden** unless `?include_archived=` |
| Standalone change-log block (`GET /card-tests/change-log`, feeds `CurrentDecklistSection`) | `card_tests.py` `list_card_test_change_log` — `archived_at.is_(None)` **and** drops ids that matched a real decklist change | Hidden | **Shown** if archived, **hidden** if deleted |
| Inline version-diff comments (`GET .../versions/{id}/diff`) | `personal_decks.py` ~L526 — `select(TSCardTest).where(… archived_at.is_(None))` then `annotate_diff_cards_with_card_tests` | Hidden | **Shown** if archived, **hidden** if deleted |
| `compute_matched_card_test_ids` | `card_test_matching.py` ~L64 — already does **not** filter archived | (matched-id set only) | Filter out `deleted_at` |
| Structured decklist view — S17 inline "pending" rows (`build_decklist_view`) | `personal_decks.py` ~L429 — `archived_at.is_(None)` | Hidden | **Open question 1** |
| Deck-level PDF report | `personal_decks.py` ~L598 — `archived_at.is_(None)` | Hidden | **Open question 2** — recommend unchanged |

## Decided approach (user, 2026-09-08)

Two statements from the user set the model:

- *"141 would behave like sessions as far as I understand"* — plus issue
  point 1, archived logs keep feeding the decklist annotations.
- *"deleted archive is unlinked to the user but still in database as per
  constitution"* — the archived-view Delete is an **unlink**, never a
  physical `DELETE`.

### Three states

| State | Column | Working "Tested cards" table | Decklist annotations (diff + change-log) | "See archived" dialog | Restorable |
| --- | --- | --- | --- | --- | --- |
| **Active** | both `NULL` | ✅ shown | ✅ shown | — | — |
| **Archived** | `archived_at` set | ❌ hidden | ✅ **still shown** (issue point 1) | ✅ listed, with Restore + Delete | ✅ → Active |
| **Deleted (unlinked)** | `deleted_at` set | ❌ hidden | ❌ hidden | ❌ not listed | ❌ (row retained in DB only) |

- **Archive** = today's `DELETE /card-tests/{id}` (unchanged) — declutters
  the working table but the log keeps annotating the decklist, and it's
  restorable.
- **Delete** = a new action **only reachable from the archived view**
  (issue point 2). It stamps a new `deleted_at` column: the row is
  removed from every one of the owner's surfaces, but **kept in the
  database** — Constitution §11.8 (real hard delete only as a
  documented exception) and §51 (archived rows kept indefinitely, no
  purge). `owner_id` is left intact for provenance / future §45.2 ML
  use; the row is simply invisible to that owner and everyone else.
- There is **no hard `session.delete()`** anywhere in this feature.

### Reference pattern — `SessionsSections.tsx`

| Sessions | Card log equivalent |
| --- | --- |
| `DELETE /sessions/{id}` → `archived_at` | `DELETE /card-tests/{id}` → `archived_at` (**already exists, unchanged**) |
| `PATCH /sessions/{id}` `{restore: true}` → clears `archived_at` | **new**: `PATCH /card-tests/{id}` `{restore: true}` |
| `GET /sessions?include_archived=true` | **new**: `GET /card-tests?include_archived=true` |
| `ArchivedSessionsSection` — "See archived" `Dialog`, search, Restore per row, edit available, `canEdit`-gated | **new**: `ArchivedCardTestsSection` — same shape, **plus a Delete (unlink) action per row** |
| (sessions have no delete tier) | `PATCH /card-tests/{id}` `{delete: true}` → stamps `deleted_at` |

## Tasks

### Backend (`apps/barrins_api`)

- [ ] **Migration**: add `deleted_at` (nullable `DateTime(timezone=True)`)
      to `ts_card_tests` (and `ts_card_test_evaluations` — see task
      below). Additive, no backfill *of the column itself* — but see the
      one-time data step in open question 3.
- [ ] `GET /card-tests` — add `include_archived: bool = False`. `False`
      → current behaviour. `True` → the owner's active **and** archived
      logs (never `deleted_at`-stamped ones). Owner-only.
- [ ] New `CardTestPatch` request schema `{restore: bool | None,
      delete: bool | None}` and `PATCH /card-tests/{test_id}`:
      `restore` clears `archived_at`; `delete` stamps `deleted_at`
      (and cascades to the log's evaluations — stamp their `deleted_at`
      too, keep the rows). Owner-checked via `_get_owned_card_test`.
      Mirror `SessionPatch`'s `restore` shape. 404 for a foreign id.
- [ ] Every existing card-test read filter gains `deleted_at.is_(None)`
      (it's a new column, so this is the safe default everywhere):
      `list_card_tests`, `list_card_test_change_log`,
      `_evaluations_by_test_id`, the `personal_decks.py` selects
      (~L429 / ~L526 / ~L598), `compute_matched_card_test_ids`.
- [ ] Then, for the "archived still annotates" behaviour, **drop only
      the `archived_at.is_(None)` predicate** (keeping `deleted_at.is_(None)`)
      from:
  - `list_card_test_change_log` (keep its "not matched by a real
    decklist change" filter);
  - the `personal_decks.py` version-diff annotation select (~L526).
- [ ] Leave `delete_card_test` (the `DELETE` route) exactly as it is —
      it archives.
- [ ] Resolve open questions 1 & 2 (decklist-view pending rows; PDF
      report).
- [ ] Tests — archived log: absent from `GET /card-tests`, present with
      `?include_archived=true`, still annotates `.../versions/{id}/diff`
      and `/card-tests/change-log`. `PATCH {restore:true}` → back to
      active. `PATCH {delete:true}` → gone from all reads incl. the
      annotations and the archived list, evaluations also `deleted_at`,
      **rows still in the DB**. Foreign id → 404.

### Frontend (`apps/tamiyo_scroll`)

- [ ] `api/cardTests.ts` — `listCardTests(deckId, { includeArchived })`;
      `restoreCardTest(id)` and `deleteCardTest(id)` → `PATCH`
      (the current `deleteCardTest` that hits `DELETE` is the **archive**
      action; rename to `archiveCardTest` for clarity).
- [ ] `hooks/useCardTests.ts` — thread `includeArchived`; add
      `useRestoreCardTest` + `useDeleteCardTest`, both invalidating
      card-tests **and** the decklist-view / version-diff queries.
- [ ] `CardTestsSection.tsx`:
  - row `✕` → "Archive" (copy: leaves the list but still shows on your
    decklist annotations; restore from See archived);
  - "See archived" button → `Dialog` → `ArchivedCardTestsSection`
    (archived rows for the active deck; **Restore** and **Delete** per
    row; `canEdit`-gated; optional name search), mirroring
    `ArchivedSessionsSection`;
  - Delete confirm copy: *"Delete "{added card}" for good? It won't
    appear anywhere in Tamiyo Scroll again."* (true from the user's
    side; the row is retained server-side for data purposes only — no
    need to surface that).
- [ ] Tests — archived dialog lists only archived rows; Restore and
      Delete fire the right mutations; the main table is unaffected by
      archived/deleted rows; confirm copy names the target.

### Docs

- [ ] `barrins_api` + `tamiyo_scroll` CHANGELOG entries.
- [ ] Add a roadmap row linking this page.
- [ ] Note in `s16`/`s17` "Done" sections that archived logs now keep
      annotating, and that a second `deleted_at` unlink state exists.

## Remaining open questions (flagged, not guessed)

1. **S17 inline "pending" decklist rows.** `build_decklist_view`
   (`personal_decks.py` ~L429) shows an active log's removed→added swap
   inline in the current decklist (struck-through removed → arrow →
   added). Does an **archived** log keep showing its inline pending row,
   or only its diff/change-log comments? Recommendation: keep it — it's
   still a real recorded swap the user reads on the decklist. Deleted
   logs never show it.
2. **Deck-level PDF report** (`personal_decks.py` ~L598). Recommendation:
   **unchanged** — archived logs stay out of the PDF (it's a
   point-in-time "current testing" snapshot). Confirm.
3. **Existing `archived_at` rows on deploy.** Without a data step, every
   log a user "deleted" (= archived) in the past would suddenly
   **reappear** in the version-diff comments and change-log block —
   they archived those expecting them gone. Recommendation: a one-time
   migration stamps every existing `archived_at IS NOT NULL` row (and
   its evaluations) with `deleted_at = archived_at`, so they land in the
   new **Deleted** state (invisible everywhere) rather than the new
   **Archived** state. Only logs archived *after* this ships get the
   "still annotates" behaviour. Confirm.

## Interaction with S18 (`s18-deletion-defaults-to-archive`)

S18 is **scoped, not started**. It plans to *"fill the missing restore
path on `TSPersonalDeck`/`TSMetaDeck`"* and convert `TSMatch` deletion.

This issue gives the card log a **two-tier** archive model
(`archived_at` restorable + `deleted_at` unlink-and-retain) that goes
beyond S18's single archive/restore tier. Sequencing recommendation: land #141 first;
S18 then decides per entity whether it needs the second tier too, or
just the `archived_at` + restore one. The "archived still annotates the
decklist" behaviour is unique to the card log's tie to the decklist-diff
feature and does not generalise.

## Consequences

- **Schema:** +1 nullable timestamp column on `ts_card_tests` and
  `ts_card_test_evaluations` (`deleted_at`). Additive; a one-time data
  step for pre-existing archived rows (open question 3).
- **API contract:** `GET /card-tests` gains optional
  `?include_archived=` (default `false`, backward-compatible); new
  `PATCH /card-tests/{id}` `{restore|delete}`. `DELETE /card-tests/{id}`
  unchanged (archive). Documented per §21.1.
- **Behaviour change:** newly-archived logs stay visible in the
  version-diff comments and change-log block (issue point 1). Pre-existing
  archived logs move to the Deleted state and stay hidden (open
  question 3).
- **No data is ever physically removed** — `archived_at` and
  `deleted_at` are both retain-in-DB states (§11.8, §51). "Delete" =
  unlink from every user-facing surface.
- **Frontend:** new "See archived" dialog with Restore **and** Delete,
  reworked confirm copy, renamed `archiveCardTest` + new
  `useRestoreCardTest` / `useDeleteCardTest`.
- **Tests:** as listed per side above; both app suites stay green.
