# S15. Decklist version history — view past content + diff

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` + `apps/tamiyo_scroll` | New read endpoints, no write-path change |
| **Initial date** | 2026-08-23 | Drafted 2026-08-23 |
| **Status** | Done | / |
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
- **Item 2 (view past content) ships default-on; item 1 (diff) is a
  setting** — new `TSUserSettings.show_decklist_version_diff` (bool).
  Amended 2026-08-24 (implementation-time decision, overriding the
  issue's own item-3 framing of "1 as an opt-in setting"): defaults
  **`true`** for every account, not `false`. When on, expanding a
  version in `VersionHistorySection` shows its diff against the prior
  version *instead of* its full content (not alongside it) — toggling
  the setting off switches back to always showing full content.

## Done statement

- `GET /personal-decks/{id}/versions/{version_id}` returns a
  structured, card-resolved view of that specific version's content
  (same shape as the existing latest-version `decklist-view`
  endpoint).
- `GET /personal-decks/{id}/versions/{version_id}/diff` returns a
  structured line-level diff against the immediately-prior version.
- `TSUserSettings.show_decklist_version_diff` is exposed via `GET`/
  `PATCH /me/settings` and toggleable from `AccountSettingsDialog`.
  Defaults `true` (2026-08-24 decision).
- Clicking a version in `VersionHistorySection` expands it to show its
  full content when the setting is off, or a diff against the prior
  version when the setting is on — the two are mutually exclusive, not
  shown together.

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

### 3. Backend — setting

- [x] Migration: `TSUserSettings.show_decklist_version_diff` (bool,
      default `true` — amended 2026-08-24, see Design decisions).
- [x] `UserSettingsUpdate`/`ResponseUserSettings`: expose the field.

### 4. Frontend

- [x] `VersionHistorySection`: clicking a version expands it to show
      full content, or a diff against the prior version when the
      setting is on (mutually exclusive — see Design decisions).
- [x] `AccountSettingsDialog`: new Switch for the setting.

## Open questions (flagged, not guessed) — resolved 2026-08-24

1. **Diff granularity: line-level text diff vs. card-level structured
   diff.** Resolved: **card-level**, matching by card name so pure
   reordering doesn't appear as added+removed. Card lines are matched
   by name (`app/services/tamiyo_scroll/decklist_diff.py`); lines that
   aren't a `"<qty> <name>"` card line fall back to a plain line-level
   diff, mirroring `decklist_view.py`'s `unparsed_lines`.
2. **UI placement: expand-in-place vs. modal vs. separate page.**
   Resolved: **expand-in-place** within `VersionHistorySection`, as
   assumed.
3. **Comparing to something other than the immediately-prior
   version.** Out of scope, as assumed — not built.

## UAT (manual)

- [ ] Open a decklist's version history, click an older version → its
      full content displays (structured, card-resolved) when the diff
      setting is off.
- [ ] With the diff setting on (default) → the same version instead
      shows a diff against the immediately-prior version, correctly
      marking added/removed/quantity-changed cards (matched by name,
      not by line position).
- [ ] View the very first version with the diff setting on → clearly
      indicates there's no prior version to compare, rather than an
      error or an empty-looking diff.
- [ ] Toggle the setting off in `AccountSettingsDialog` → expanded
      versions go back to showing full content only.

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
