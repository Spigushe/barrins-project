# S15. Decklist version history — view past content + diff

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` + `apps/tamiyo_scroll` | New read endpoints, no write-path change |
| **Initial date** | 2026-08-23 | Drafted 2026-08-23 |
| **Status** | Not started | / |
| **Source** | GitHub issue [#81](https://github.com/Spigushe/barrins-project/issues/81) — "Decklists are versioned but history can't be accessed and no diff is displayed" | / |
| **Dependency** | None. [S16](../s16-tested-card-changelog/index.md) reuses this item's UI patterns for its own inline history display | / |

---

## Context

**Verified against the code (2026-08-23, `feat/tolaria_news_backend`):**

- `TSPersonalDecklistVersion` (`app/models/tamiyo_scroll.py:339-378`,
  table `ts_personal_decklist_versions`): each edit is a **new row**
  (append-only, `version` monotonically increasing per
  `personal_deck_id`, `content` = full raw decklist text). **No diff is
  ever computed or stored** — every version is an independent full
  snapshot.
- `app/api/tamiyo_scroll/personal_decks.py`: `GET
  /personal-decks/{id}/versions` lists version metadata (already used
  by the frontend); `POST .../versions` and `.../versions/import-
  moxfield` create versions; `DELETE .../versions/{version_id}` hard-
  deletes. **No endpoint returns a single arbitrary version's content**
  — `GET /personal-decks/{id}/decklist-view` (the structured
  Commander/Library view from [S4](../s4-decklist-display-redesign/index.md))
  always resolves the **latest** version only.
- `pages/decklist/VersionHistorySection.tsx`: a flat metadata list
  (version number, timestamp, source) with no click handler — no
  version's content is ever shown, and there is no diff/comparison UI
  anywhere in the frontend.
- **No diffing library exists** in either `apps/barrins_api`'s
  `pyproject.toml` or `apps/tamiyo_scroll`'s `package.json`. Python's
  stdlib `difflib` is available and unused by app code today.

## Design decisions

- **Generalize the existing decklist-view service to accept an
  explicit `version_id`**, rather than always resolving latest — new
  `GET /personal-decks/{id}/versions/{version_id}` returns the same
  `ResponseDecklistView` shape S4 already built (Commander/Library
  grouping, card-resolved). This satisfies item 2 (view previous
  content) as a thin reuse of S4's existing structured view, not a new
  rendering path.
- **Diff is computed server-side**, per Constitution §4.1 (backend
  owns business/domain logic) — new `GET
  /personal-decks/{id}/versions/{version_id}/diff` (comparing against
  the immediately-prior version by default), using stdlib `difflib`.
  No new dependency in either app (§4.7/§22) — the frontend only
  renders a structured added/removed/unchanged payload the backend
  already computed.
- **Item 2 (view past content) ships default-on; item 1 (diff) is
  opt-in** — new `TSUserSettings.show_decklist_version_diff` (bool,
  default `false`), matching the issue's own item-3 framing ("1 as an
  opt-in setting, 2 is default behaviour").

## Done statement

- `GET /personal-decks/{id}/versions/{version_id}` returns a
  structured, card-resolved view of that specific version's content
  (same shape as the existing latest-version `decklist-view`
  endpoint).
- `GET /personal-decks/{id}/versions/{version_id}/diff` returns a
  structured line-level diff against the immediately-prior version.
- `TSUserSettings.show_decklist_version_diff` is exposed via `GET`/
  `PATCH /me/settings` and toggleable from `AccountSettingsDialog`.
- Clicking a version in `VersionHistorySection` expands it to show its
  full content; with the new setting enabled, a diff view against the
  prior version is also available.

## Tasks

### 1. Backend — view an arbitrary version

- [ ] Generalize the decklist-view service function to accept an
      explicit `version_id` instead of always resolving latest.
- [ ] `GET /personal-decks/{id}/versions/{version_id}` route, reusing
      the existing `ResponseDecklistView` schema.
- [ ] Ownership/auth checks match the existing `decklist-view` route.

### 2. Backend — diff endpoint

- [ ] `GET /personal-decks/{id}/versions/{version_id}/diff`, default
      comparison target = immediately-prior version by `version`
      number (decide the response shape — see Open questions).
- [ ] Handle the first version (no prior version to diff against)
      explicitly, not as an error.
- [ ] Unit tests for the diff algorithm: added/removed/unchanged
      lines, identical content, no-prior-version case.

### 3. Backend — opt-in setting

- [ ] Migration: `TSUserSettings.show_decklist_version_diff` (bool,
      default `false`).
- [ ] `UserSettingsUpdate`/`ResponseUserSettings`: expose the field.

### 4. Frontend

- [ ] `VersionHistorySection`: clicking a version expands it to show
      full content (always available).
- [ ] When the opt-in setting is enabled, add a diff view against the
      prior version.
- [ ] `AccountSettingsDialog`: new Switch for the setting.

## Open questions (flagged, not guessed)

1. **Diff granularity: line-level text diff vs. card-level structured
   diff.** `content` is free-text (one card per line, typically), so a
   plain `difflib`-style line diff is the cheapest correct
   implementation; a card-aware diff (matching by card name across
   lines, ignoring pure reordering) would read better but is more
   work and a separate design decision. Default assumption: line-level
   text diff for v1 — confirm before implementation if card-level is
   actually wanted instead.
2. **UI placement: expand-in-place vs. modal vs. separate page.**
   Assumed expand-in-place within `VersionHistorySection` (cheapest,
   keeps context) — confirm if a dedicated comparison view is
   preferred instead.
3. **Comparing to something other than the immediately-prior
   version.** The issue only asks for "diff with the prior version" —
   comparing two arbitrary versions is out of scope for this item
   unless requested.

## UAT (manual)

- [ ] Open a decklist's version history, click an older version → its
      full content displays (structured, card-resolved).
- [ ] With the diff setting off (default) → no diff UI is shown.
- [ ] Enable the diff setting → the same version now also shows a
      diff against the immediately-prior version, correctly marking
      added/removed lines.
- [ ] View the very first version → content displays; diff view (if
      enabled) clearly indicates there's no prior version to compare.

## Non-regression tests

- Backend: existing `GET /personal-decks/{id}/decklist-view` (latest-
  version) tests still pass unchanged after the service function is
  generalized to accept an explicit version.
- Backend: existing `GET .../versions` (list) and `POST .../versions`
  (create) tests unaffected.
- Frontend: existing `VersionHistorySection` tests (if any) still pass
  with the new expand/diff UI added.

## See also

- [s4-decklist-display-redesign/](../s4-decklist-display-redesign/index.md) —
  origin of the structured `ResponseDecklistView` this item reuses.
- [s3-match-decklist-version/](../s3-match-decklist-version/index.md) —
  origin of decklist versioning itself.
- [s16-tested-card-changelog/](../s16-tested-card-changelog/index.md) —
  reuses this item's version-display UI pattern for its own inline
  change-log display.
