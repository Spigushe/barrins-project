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

## Enhancement under consideration (flagged 2026-07-26, not decided)

The user raised checking Moxfield during deck retrieval to flag a
version as **"in the past"**: A3's `MoxfieldClient`
(`app/services/moxfield/`) already calls
`GET https://api2.moxfield.com/v2/decks/all/{publicId}` on import, but
today only extracts board contents into a text blob — the response's own
last-updated timestamp is fetched and discarded. This would compare that
timestamp against the locally-stamped version's creation date (this
item's core feature) and surface a flag when Moxfield's deck has since
changed.

**Constraint, decided (2026-07-27)**: this check is used **only if the
last-update value arrives as part of an API call already being made for
another reason** — never a dedicated Moxfield call made specifically to
check staleness. Concretely: if/when `MoxfieldClient` is invoked for an
actual purpose (e.g. a user-triggered re-import/refresh, which already
calls `GET .../v2/decks/all/{publicId}`), that same response's
last-updated field is captured and compared against the locally-stamped
version's creation date — no new call is added to the rate-limited path
just for this feature. If no such call happens (the common case — a
deck-page view doesn't itself call Moxfield today), no staleness flag is
computed or shown; the UI doesn't show a stale/fresh indicator that
requires reaching out to Moxfield on its own. This resolves the earlier
open question about caching/throttling: there's no separate cache to
invalidate, because there's no separate call to make.

**Still open, not guessed**:

- Only applies to Moxfield-imported decks — manually-entered decks have
  no external source to compare against.
- Not scoped for v2.0.0 by this remark alone — recorded here so it isn't
  lost, not scheduled as a task above. Confirm with the user before
  treating it as in-scope work. If it is scoped, it likely rides on a
  future "re-sync from Moxfield" action (not yet designed) rather than
  the one-shot import A3 already built.

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
