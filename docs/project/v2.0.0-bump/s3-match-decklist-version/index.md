# S3. Auto-flag a match to a decklist version

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api`, `apps/tamiyo_scroll` | / |
| **Initial date** | 2026-07-30 | In progress |
| **Status** | 🔶 In progress — core auto-flag done; Moxfield staleness flag (brought into scope 2026-07-30) still to implement | / |
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

- [x] Add the migration (nullable FK, no backfill).
- [x] Update the match-creation service to resolve and stamp the current
      version.
- [ ] Add the field to `MatchWrite`/`MatchRead` schemas and to
      `MatchForm.tsx`/`MatchFormFields.tsx` (edit affordance).
- [x] Confirm `matchup-summary`/other stats routes are unaffected —
      `app/services/tamiyo_scroll/stats.py` operates on full `TSMatch`
      ORM objects, no column enumeration to update.

## Moxfield staleness flag — decided in scope for v2.0.0 (2026-07-30)

The user raised checking Moxfield during deck retrieval to flag a
version as **"in the past"**: A3's `MoxfieldClient`
(`app/services/moxfield/`) already calls
`GET https://api2.moxfield.com/v2/decks/all/{publicId}` on import, but
today only extracts board contents into a text blob — the response's own
last-updated timestamp is fetched and discarded. This would compare that
timestamp against the locally-stamped version's creation date (this
item's core feature) and surface a flag when Moxfield's deck has since
changed.

**Decided (2026-07-30): brought into v2.0.0 scope**, still bound by the
2026-07-27 constraint below (opportunistic only, never a dedicated call).

**Verified against the live API (2026-07-30)**, using the real
`MOXFIELD_USER_AGENT` secret from `.env` against a real deck URL: the
response shape assumed by `http_client.py`'s docstring ("not verified
against a live response... no outbound network access in this
environment") is now confirmed correct where it matters for this
feature —

- The deck's own last-update timestamp is a **top-level** field:
  `lastUpdatedAtUtc` (ISO 8601 UTC, e.g. `"2026-07-29T11:54:52.473Z"`),
  sitting right after `createdAtUtc` and `hubs` at the response root.
- **Trap**: `lastUpdatedAtUtc` also appears **~100+ times nested inside
  each card's `prices` object** (per-card price-refresh time, unrelated
  to the deck). Extracting via a naive top-level key search on a
  flattened dict, or `"lastUpdatedAtUtc" in str(response_text)`, would
  silently grab the wrong value. Must read it from the response root
  object specifically (`data["lastUpdatedAtUtc"]`, not a recursive
  search).
- `createdAtUtc` is also present at deck level, unused by this feature
  but confirms the root-level shape.

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
- The only existing caller of `MoxfieldClient` is
  `POST .../versions/import-moxfield` (A3's one-shot import route) — so
  the natural hook, satisfying the "already being made for another
  reason" constraint, is: every time that route is called (first import
  **or** a later re-import of the same deck), capture the response's
  root-level `lastUpdatedAtUtc` alongside the content already being
  extracted. A brand-new "check for updates" endpoint whose sole purpose
  is querying Moxfield would violate the constraint — not built.

## Tasks — Moxfield staleness flag (added 2026-07-30)

- [ ] `MoxfieldClient.fetch_decklist` (or a sibling method) also returns
      the deck's top-level `lastUpdatedAtUtc`, not just the board content
      — read from the response root, not a recursive/flattened search
      (see the per-card `prices.lastUpdatedAtUtc` trap above).
- [ ] `TSPersonalDecklistVersion` gains a nullable
      `moxfield_last_updated_at` timestamp column, set only for
      `source = moxfield_import` versions (NULL for manual entries).
- [ ] On a re-import (`import-moxfield` called again for a deck that
      already has a prior Moxfield-sourced version), compare the fresh
      `lastUpdatedAtUtc` against the prior Moxfield-sourced version's
      stored value to determine whether Moxfield's deck changed since the
      last import; surface this on the response (exact field/UI
      presentation not yet designed).
- [ ] Frontend: surface the flag somewhere in the decklist-version UI —
      placement TBD, not yet designed.

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
