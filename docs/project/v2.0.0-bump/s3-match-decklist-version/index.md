# S3. Auto-flag a match to a decklist version

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api`, `apps/tamiyo_scroll` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — unblocked, can start immediately | / |
| **Source** | Request item 2.2 | / |
| **Dependency** | None | S5 (PDF report) is more useful once this lands |

---

## Context

`ts_matches` currently has no reference to a decklist version — only
`personal_deck_id`. `ts_personal_decklist_versions` already tracks
version history (`version: int`, unique per deck). The request wants
each logged match auto-tagged with whichever version was active at
creation time, editable afterward.

## Done statement

- `ts_matches` gains a nullable `decklist_version_id` FK to
  `ts_personal_decklist_versions`.
- On match creation, the backend auto-fills it with the deck's current
  latest version at that moment (server-side, Constitution §4.1 — never
  the frontend guessing which version is "current").
- The match-edit flow allows changing which version a match is
  attributed to, after the fact.
- Existing matches (created before this migration) have `NULL` here —
  no retroactive guessing.

## Tasks

- [ ] Add the migration (nullable FK, no backfill).
- [ ] Update the match-creation service to resolve and stamp the current
      version.
- [ ] Add the field to `MatchWrite`/`MatchRead` schemas and to
      `MatchForm.tsx`/`MatchFormFields.tsx` (edit affordance).
- [ ] Confirm `matchup-summary`/other stats routes are unaffected (this
      field is informational, not part of any existing aggregate
      calculation) unless a future request asks to filter stats by
      version.

## UAT (manual)

- [ ] Create a personal deck, save two decklist versions, log a match —
      confirm it's stamped with version 2 (the latest at creation time).
- [ ] Edit the match to point at version 1 instead; confirm it persists.

## Non-regression tests

- New test in `tests/tamiyo_scroll/test_matches.py`: auto-stamping on
  creation, and re-pointing on edit.
- Confirm existing match tests (draft ↔ `MatchWrite` mapping,
  win-rate/coloring calculations) are unaffected by the new nullable
  column.
