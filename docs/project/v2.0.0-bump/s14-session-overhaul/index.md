# S14. Session overhaul — rename, editable dates, sort/paginate, hue, archive search, auto-archive

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` + `apps/tamiyo_scroll` | Schema change (`TSSession`, `TSUserSettings`) + several API/frontend changes |
| **Initial date** | 2026-08-23 | Drafted 2026-08-23 |
| **Status** | Not started | / |
| **Source** | GitHub issue [#80](https://github.com/Spigushe/barrins-project/issues/80) — 5 "Suggested Change" items + 4 "Related possible change" items; user confirmed 2026-08-23 both groups are in scope for this item | / |
| **Dependency** | Auto-archive (item 9) needs a periodic job — see Open questions; not yet confirmed whether `barrins_api` has any existing in-process scheduler to reuse | / |

---

## Context

**Verified against the code (2026-08-23, `feat/tolaria_news_backend`):**

- `TSSession` (`app/models/tamiyo_scroll.py:431-474`, table `ts_sessions`):
  `id`, `owner_id`, `personal_deck_id` (required, one deck per session),
  `name`, `type` (`tournament`/`training`), `notes`, `created_at`
  (doubles as the session's implicit start — **no separate start-date
  column exists**), `ended_at` (nullable, set only via close/reopen),
  `archived_at` (nullable — archiving is the existing soft-delete;
  sessions are never hard-deleted).
- `app/api/tamiyo_scroll/sessions.py`: `GET /sessions` (owner-scoped,
  `include_archived` flag, ordered `created_at DESC`, **no sort or
  pagination params**), `POST /sessions`, `PATCH /sessions/{id}`
  (**already supports** `name` rename and `notes` via `SessionPatch`,
  plus `close`/`reopen` boolean flags that stamp/clear `ended_at` —
  **no direct date field is PATCH-able today**), `DELETE
  /sessions/{id}` (archives, 204, **no restore/un-archive endpoint
  exists**), `GET /sessions/{id}/comparison`, `GET
  /sessions/{id}/report.pdf`.
- `pages/sessions/SessionsSections.tsx`: `SessionsOverviewSection`
  renders one flat, unsorted, unpaginated table (`Session | Type |
  Status | Period | actions`). The **Period** column (`sessionPeriodLabel`,
  lines 44-48) renders `"Since {created_at}"` or `"{created_at} →
  {ended_at}"` — derived text, not editable. Row actions: Close/Reopen,
  PDF download, and the unconfirmed archive `✕` (fixed by
  [S13](../s13-delete-confirmation/index.md)).
- `useUpdateSession` (`hooks/useSessions.ts`) already calls `PATCH` —
  a rename UI reuses this hook directly.
- **No per-entity persisted color exists anywhere in the schema.** The
  only existing color pattern (`lib/displayPrefs.ts` +
  `useLocalStorageFlag`) is a fixed-palette, client-only,
  never-synced-to-backend toggle over enum categories (archetype/tier),
  documented in its own docstring as deliberately not backend-synced.
  It doesn't fit a freeform, per-row, user-chosen hue.
- `archived_at` is a repeated soft-delete pattern (`TSSession`,
  `TSMetaDeck`, `TSPersonalDeck`) — "deletion = archiving, never a SQL
  DELETE." `TSCardTest`/`TSPersonalDecklistVersion`/`TSMatch`/`TSTeam`
  are hard-deleted, by contrast.
- `TSUserSettings` (`ts_user_settings`, one row per user) already
  carries `data_shared`, `receive_shared_data`, `active_personal_deck_id`,
  `metagame_roster_scope` — direct precedent for adding new opt-in
  boolean/int columns here, exposed via `GET`/`PATCH /me/settings`.
- `TSMatch.session_id` and `TSMatch.decklist_version_id` (from
  [S3](../s3-match-decklist-version/index.md)) both already exist —
  the auto-archive algorithm below reads the latter; the Match-journal
  session tag (item 7) needs the former surfaced on the match response.
- The match list response today does **not** embed the session's name
  or any color — needed for item 7 (session tag in Match journal).

## Design decisions

- **New `started_at` column** (nullable datetime, backfilled from
  `created_at` on migration, directly `PATCH`-able going forward).
  `created_at` stays untouched as the true creation-audit timestamp;
  `started_at` is the user-editable "when did this session actually
  start" field the issue asks for.
- **`ended_at` becomes directly `PATCH`-able too**, per the user's
  2026-08-23 decision (not `started_at`-only). `close`/`reopen` remain
  as convenience shortcuts (`close` → `ended_at = now()`, `reopen` →
  `ended_at = null`) layered over the same field — no separate state
  machine, just two ways to set the same column.
- **New `hue` column** (`int`, nullable, `CheckConstraint` 0-359) on
  `TSSession`, stored **server-side**, not via the existing
  `localStorage` display-pref pattern — this is user-chosen identity
  data tied to one specific row (like `name`), not a fixed-palette
  toggle over a shared enum. Diverging from S12's precedent here is
  deliberate, not an oversight — flagged in Open questions in case the
  user prefers the lighter-weight client-only route instead.
- **Server-side pagination + sorting** on `GET /sessions` (`limit`/
  `offset`, page size fixed at 10 per the issue; `sort_by`/`sort_dir`
  over name/type/started_at/status). Client-side sort was rejected —
  it doesn't compose correctly once results are paginated.
- **New `restore` PATCH flag** (mirrors `close`/`reopen`, clears
  `archived_at`) — a gap found during this review, not named in the
  issue: today's archive is one-way from the frontend's perspective,
  which the new archived-sessions search tool (item 8) needs to be
  useful rather than read-only.
- **New optional `search` query param** on `GET /sessions` (name,
  case-insensitive contains) for the archived-sessions browsing tool.
- **Match list response gains an embedded session summary**
  (`name` + `hue`) for the Match-journal tag (item 7).
- **Auto-archive** (item 9): new `TSUserSettings` fields
  `auto_archive_stale_sessions` (bool, opt-in) and
  `auto_archive_decklist_version_gap` (int, only meaningful when the
  bool is true). Algorithm: for each open (non-archived) session, take
  `decklist_version_id` off its most recent match; compare that
  version number against `MAX(version)` for the session's
  `personal_deck_id`; if the gap is ≥ the threshold, archive the
  session. Sessions with no matches are never auto-archived (nothing
  to compare). This needs a **periodic job**, not an on-read check
  (a `GET` shouldn't have side effects) — see Open questions.
- **"Period" → "Starting date"**: the column now shows `started_at`
  only, not the current start→end range. This is narrower information
  at a glance than today (no visible end date in the main table) —
  flagged, since it's literally what the issue asks for, not a design
  improvement being smuggled in.

## Done statement

- `TSSession` has `started_at` and `hue` columns; `ended_at` is
  directly editable via `PATCH /sessions/{id}`, alongside the existing
  `close`/`reopen` shortcuts and the existing `name`/`notes` fields.
- `GET /sessions` accepts `limit`/`offset` (10 per page), `sort_by`/
  `sort_dir`, and `search` (name, case-insensitive contains, primarily
  for the archived view).
- `PATCH /sessions/{id}` accepts a `restore` flag that clears
  `archived_at`.
- The Sessions table supports renaming, editing start/end dates,
  clicking column headers to sort, and paging through results 10 at a
  time. The former "Period" column reads "Starting date" and shows
  `started_at` only.
- Each session can be given a hue via a color picker; that hue tints
  the session's row and its tag elsewhere in the app.
- Match journal rows show a small tag with the match's session name
  (colored per that session's hue, if set).
- A dedicated "Archived sessions" view lists archived sessions with a
  name search and a restore action per row.
- With `auto_archive_stale_sessions` enabled (opt-in, default off) and
  a configured version-gap threshold, sessions whose most recent
  match's decklist version has fallen that far behind the deck's
  current version are automatically archived by the periodic job.

## Tasks

### 1. Rename (core)

- [ ] Frontend: rename UI (inline-edit or small dialog) wired to the
      existing `useUpdateSession`/`PATCH` — no new endpoint needed.

### 2. Editable dates (core)

- [ ] Migration: add `started_at` (nullable, backfilled from
      `created_at`).
- [ ] `SessionPatch` schema: accept `started_at`/`ended_at` directly.
- [ ] Frontend: date-edit UI (start + end) in the session's
      rename/edit surface.
- [ ] Decide close/reopen's exact interaction with a manually-set
      `ended_at` (see Open questions).

### 3. Sortable columns (core)

- [ ] `GET /sessions`: add `sort_by`/`sort_dir` query params
      (name/type/started_at/status).
- [ ] Frontend: clickable column headers, re-fetching on change.

### 4. Pagination (core)

- [ ] `GET /sessions`: add `limit`/`offset`, default page size 10.
- [ ] Frontend: Prev/Next controls.

### 5. "Period" → "Starting date" (core)

- [ ] Rename the column header; render `started_at` only.

### 6. Per-session hue (related)

- [ ] Migration: add `hue` (nullable int, 0-359 check constraint).
- [ ] `SessionPatch`/`SessionCreate` schemas: accept `hue`.
- [ ] Frontend: color picker in the session edit surface; apply the
      hue to the session's row/tag.

### 7. Session tag in Match journal (related)

- [ ] Embed session `name`/`hue` on the match list/detail response.
- [ ] Frontend: render a small colored tag per match row in
      `MatchJournalSection`.

### 8. Archived-session search tool (related)

- [ ] `GET /sessions`: add `search` query param.
- [ ] `PATCH /sessions/{id}`: add `restore` flag.
- [ ] Frontend: new "Archived sessions" view/section with a search box
      and a restore action per row.

### 9. Auto-archive by decklist-version age (related)

- [ ] Migration: `TSUserSettings.auto_archive_stale_sessions` (bool),
      `auto_archive_decklist_version_gap` (int).
- [ ] `UserSettingsUpdate`/`ResponseUserSettings`: expose both fields.
- [ ] Frontend: opt-in toggle + threshold input in
      `AccountSettingsDialog`.
- [ ] Backend: the eligibility predicate (session → its latest match's
      `decklist_version_id` → deck's `MAX(version)` → gap ≥ threshold),
      unit-testable in isolation from any scheduling mechanism.
- [ ] Backend: the periodic job itself — **blocked on the scheduler
      investigation below**.

## Open questions (flagged, not guessed)

1. **Scheduling mechanism for item 9's periodic job.** `barrins_api`
   has no confirmed in-process scheduler today. Two precedents exist
   elsewhere in this repo for periodic work: the old VPS-side
   `scripture_scraper` systemd timers, and their replacement,
   `.github/workflows/scripture-scrape.yml` (moved off the VPS after
   the 2026-08-10 MTGO IP-block incident, see `s3`/T-group history).
   Needs a short Agent 1/Agent 3 spike to confirm which shape fits
   here (an on-VPS timer calling an internal endpoint, vs. a GitHub
   Actions workflow, vs. something else) before this task starts —
   not decided here.
2. **`hue`: server-persisted column vs. client-only `localStorage`.**
   This doc recommends server-persisted (see Design decisions); if the
   user prefers the lighter-weight, S12-consistent `localStorage`
   route instead (accepting it won't follow the user across devices),
   that's a smaller change — confirm before implementation.
3. **Manually-set `ended_at` vs. close/reopen state.** If a user sets
   `ended_at` directly via the new date-edit UI, is the session then
   simply "closed" (same as clicking Close), and does `reopen` clear
   whatever `ended_at` was set to, including a manually-chosen one?
   Assumed yes (both fields ultimately just read/write the same
   column) — confirm no other state needs tracking.
4. **Exact color-picker UI for item 6.** A fixed swatch palette (like
   the existing archetype/tier colors) vs. a free hue slider — the
   issue says "hue customisation," suggesting the latter; not fully
   specified. Pick a reasonable implementation unless the user has a
   preference.
5. **Search scope for item 8.** Name-only search (as scoped above) vs.
   also matching type/notes — assumed name-only as the minimal useful
   version; extend later if requested.

## UAT (manual)

- [ ] Rename a session → name updates everywhere it's shown.
- [ ] Edit a session's start and end dates directly → both persist and
      display correctly; Close/Reopen still work as before.
- [ ] Click each sortable column header → table re-sorts; sorting
      persists correctly across pages.
- [ ] With more than 10 sessions, page through the list → 10 per page,
      Prev/Next work at the boundaries.
- [ ] Set a session's hue → its row and its Match-journal tag both
      reflect the chosen color.
- [ ] Log a match under a session → the journal row shows that
      session's tag, correctly colored.
- [ ] Archive a session, open the Archived sessions view, search for
      it by name, restore it → it reappears in the main list.
- [ ] Enable auto-archive with a low threshold, let the job run (or
      trigger it manually in a test environment) → a session whose
      last match is far enough behind the deck's current decklist
      version gets archived automatically.

## Non-regression tests

- Backend: existing `PATCH /sessions/{id}` (rename, notes, close,
  reopen), `GET /sessions` (default ordering/`include_archived`), and
  `DELETE /sessions/{id}` (archive) tests still pass with the new
  fields/params added.
- Backend: `GET /sessions/{id}/comparison` and `.../report.pdf` are
  unaffected by pagination/sort/date-field changes — confirm no
  implicit ordering assumption broke.
- Frontend: `SessionsSections` tests updated for the new columns/
  controls; existing Close/Reopen/PDF-download assertions still pass.

## See also

- [s3-match-decklist-version/](../s3-match-decklist-version/index.md) —
  origin of `TSMatch.decklist_version_id`, read by item 9's algorithm.
- [s9-tournament-session/](../s9-tournament-session/index.md) — origin
  doc for `TSSession` itself.
- [s12-uiux-polish/](../s12-uiux-polish/index.md) — origin of the
  `localStorage` display-pref pattern this item's `hue` deliberately
  diverges from (see Design decisions).
