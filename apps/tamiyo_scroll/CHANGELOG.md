# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [2.0.0-alpha.2] - 2026-08-25

### Added

- Metagame roster scoped to the active personal deck (F10): a new
  "Store roster decks per game" switch (`AccountSettingsDialog`) toggles
  between one shared roster per game (default) and a roster scoped to
  just the active personal deck — the Deck roster and Expected metagame
  sections follow whichever is selected.
- Decklist version history — view past content + diff (S15):
  `VersionHistorySection` becomes expand-in-place — clicking a version
  shows its full structured content (new shared `DecklistViewContent`,
  extracted from `CurrentDecklistSection` so the two never drift) or,
  when the new "Decklist version diff" setting is on (default,
  `AccountSettingsDialog`), a card-aware diff against the immediately
  prior version instead — the two are mutually exclusive, not shown
  together. The first version shows an explicit "no prior version"
  message rather than an empty-looking diff.
- **Breaking**: Tested Cards → decklist change log (S16).
  `CardTestsSection`'s "Nickname"/"Card" table columns and create-form
  fields are relabeled "Removed Card"/"Added Card" (also fixing the
  pre-existing "Card"/"Card name" label mismatch between the table and
  the form); the stale autofill that prefilled the removed-card field
  with the current user's display name (a leftover from the old
  "who's testing" semantics) is removed. Failed validation on create/
  update now shows the backend's error message inline. Three new
  `AccountSettingsDialog` switches: "Validate removed card is in
  decklist" (on by default), "Validate added card exists" (off,
  Magic-only), "Show decklist change log" (off). With the change-log
  setting on: `VersionHistorySection`'s diff view shows a matched card
  test's note as a comment under its `+`/`-` line, anywhere in version
  history; `CurrentDecklistSection` lists card tests that match no real
  decklist change in a standalone "Card change being considered in
  this version" block.
- Fix: `src/demo/api/personalDecks.ts` was missing S15's
  `getDecklistVersionView`/`getDecklistVersionDiff`, failing `tsc -b`
  and `demoApi.test.ts`'s module-shape check. Demo mode now implements
  both, mirroring the real backend's `diff_decklist_cards` and version
  view construction against the in-memory store.
- Shared `ConfirmDialog` component (`components/ui/confirm-dialog.tsx`,
  built on the existing `Dialog` primitive, no new dependency — S13):
  deleting a Match journal row, a Card test, a Decklist version, or
  archiving a Session now opens a confirmation dialog naming the target
  instead of firing the mutation immediately on click.
- Decklist view (`CurrentDecklistSection`) rebuilt around the backend's
  new structured `ResponseDecklistView` (S4): a Commander table (when
  the decklist has one) plus one table per card-type section
  (Planeswalkers/Battles/Creatures/.../Lands), each row showing qty,
  name, mana-cost pips (`ManaPips`, new `lib/mana-symbols.ts`), and an
  info popover with oracle text/keywords. Hovering a card name previews
  its front/back-face art (`CardFacesPreview`, new
  `components/ui/hover-card.tsx`) via the backend's new Scryfall image
  proxy. Replaces the old flat colored-text-line rendering; any
  unparsable line still renders as before, in its own section.
- Session overhaul (S14): a session gains a `location` field and an
  inline-editable `started_at`/`ended_at` date pair (independent of
  Close/Reopen — see Changed), a freeform 0-359 hue (native range
  slider, server-persisted, replaces the type-based color on every
  session tag app-wide — `SessionTypeBadge`), and `GET /sessions` gains
  `sort_by`/`sort_dir`/`limit`/`offset`/`search`. The Sessions tab table
  supports sortable columns, 10-per-page pagination, and inline editing
  (name/location/notes/dates/hue) regardless of a session's status. A
  "See archived" dialog lists archived sessions with a name search and a
  restore action (`PATCH .../restore`). Auto-archive (opt-in,
  `AccountSettingsDialog`): once a session's most recent match's
  decklist version falls a configurable number of versions behind, it's
  archived automatically the next time a new decklist version is
  imported for that deck (Moxfield or plain-text) — event-triggered, not
  a periodic job.
- Session creation (S14 follow-up): the "New session" form now reuses
  `SessionEditFields` — the same location/notes/started_at/ended_at/hue
  fields used to edit a session — instead of just name/type, so a
  session can be fully filled in at creation rather than requiring an
  immediate follow-up edit.
- **Breaking**: card log / match-up evaluation split (S17). Tested
  cards' creation form only collects Removed Card, Added Card, and
  Notes now — match-up (opponent deck) and effectiveness rating moved
  to an expandable evaluations sub-list on each card log, added from
  the edit row (one card log, many evaluations). Removed-Card suggests
  from the current decklist as you type; Added-Card suggests from a
  live, debounced card-name search (3-character minimum), with a "not
  found" hint when nothing matches — free text stays valid either way.
  A decklist line whose card is still present but targeted by a card
  log's `removed_card_name` renders inline as **pending** (blue): the
  removed name struck through, an arrow, then the added name, same
  row — replacing the old separate "Card change being considered"
  block for changes reflected this way (that block still lists changes
  not yet reflected in the current decklist). Hovering either name in
  a pending row, or either name in the "Tested cards" block itself,
  shows that card's image.
- Route paths dropped their `/app` prefix (`/app/tracker` → `/tracker`,
  same for `/metagame`/`/decklist`/`/sessions`/`/team`/`/admin/metrics`)
  — old `/app/*` links still resolve, redirected to the flattened path.
  The post-login/first-access landing tab is now Tracker (BO3 Tracking),
  not Metagame.

### Changed

- `MetaDecksSections` (`RosterRow`), `PersonalDeckSelector`, and
  `AccountSettingsTeamSection`'s existing confirm-before-delete dialogs
  are refactored onto the shared `ConfirmDialog` (S13); behavior is
  unchanged, including the team flow's extra invite-code-retype step.
- `getDecklistView`'s Zod schema (`decklistViewSchema`) replaces the old
  flat `decklistLineSchema.array()`; the demo-mode API
  (`demo/api/personalDecks.ts`) mirrors the backend's grouping logic
  client-side (no `mj_cards` in the browser, so demo cards always
  categorize as "other").
- `TSSession.ended_at` (the Close/Reopen workflow field) is renamed to
  `closed_at` (S14) — the Status ("Ongoing"/"Closed") badge and the
  match-logging session picker now read `closed_at`. A new, separate
  `ended_at` is purely informational and freely editable, independent
  of Close/Reopen.
- The "Team de test" section is dropped from `AccountSettingsDialog` —
  Teams itself (`TeamPage`, `TeamDeckSelector`, etc.) is unaffected, only
  this redundant entry point is removed.

### Fixed

- `CardTestsSection`'s Added-Card "not found" hint (S17) now respects
  the "Validate added card exists" setting (S16, off by default) — it
  was flagging every non-Magic card name for decks that never opted
  into that validation.
- `useMetaDecks`' create/update/archive mutations now invalidate the
  matches cache too (F10) — a roster change can shift which opponent id
  a cached match should resolve against.
- `demo/api/metaDecks.ts`'s `createMetaDeck` mock now sets `merged_ids`
  (F10), fixing a `tsc -b` break introduced by the new required field.
- Session hue badge text color adjusted for readability in dark theme
  (`lib/mtg-format.ts`).

## [2.0.0-alpha] - 2026-08-03

### Added

- Account-settings popup (`AccountSettingsDialog.tsx`): display-name
  field, "Share my data"/"Receive shared data" switches (new
  `components/ui/switch.tsx`, no new dependency), and an explanatory
  line that sharing is matched by deck name. Replaces the header's old
  inline "Share my data" checkbox and "View: {user}" selector
  entirely — sharing is now an automatic, read-only merge (matched by
  exact, trimmed, case-insensitive personal-deck name) directly into
  the viewer's own Journal and Metagame, instead of a separate "view
  as" mode. "Receive shared data" is disabled and auto-cleared
  whenever "Share my data" is off, since receiving now requires
  sharing on the same account.
- Read-only shared matches (Journal row + View popup) and shared
  roster entries show a "from: {sharer}" badge and hide Edit/Delete.
  Two different sharers contributing the same-named deck (no owning
  copy) consolidate into a single read-only roster line labeled
  "multi share" instead of two. An owned deck that also merged in
  shared data is flagged separately ("with shared"/"w/ shared") from
  a fully-foreign entry, in the roster, archetype breakdown, and
  matchup summary.
- Selecting a shared-only opponent deck (`OpponentDeckField`) when
  logging a match now opens the create-deck dialog pre-filled with
  the shared tier/category instead of silently failing — submitting
  it creates the viewer's own same-named roster entry and uses that
  as the opponent.
- "Teams" nav tab (`/app/team`): create/join a team via an 8-character
  invite code, a per-team page (member list with per-member
  match/card-test activity counts, owner-only "flag a deck" picker,
  per-deck-name discussion threads, two-step delete requiring the
  invite code to be retyped), and a "Team Decks" selector next to the
  personal deck selector in the header — one merged, read-only row
  per flagged deck name, with a cumulative PDF report download.
  "Quick mode" (create/join/leave/delete) is also reachable from the
  account-settings popup (`AccountSettingsTeamSection`).
- `PersonalDeckSelector.tsx`: a rename control per deck
  (`useRenamePersonalDeck`) — renaming a deck into or out of a
  team-flagged name is how a member joins or leaves that team-deck's
  rotation under the name-based sharing model.
- Match-edit flow gains a decklist-version selector, so a logged
  match's auto-stamped decklist version can be corrected after the
  fact.
- `PersonalDecklistImportSection.tsx` shows a one-line warning under
  the Moxfield-import form when a re-import's response flags that the
  deck has changed on Moxfield since the last import
  (`moxfield_deck_changed_since_last_import`).
- "Download report (PDF)" buttons trigger a server-rendered PDF
  download (no client-side composition): on the Sessions tab's session
  summary panel and as a per-row icon button (inlined Font Awesome
  file-pdf SVG, no new icon-library dependency) for a session-scoped
  report, and on the Current decklist section, next to the active
  deck's version badge, for a rolling last-30-days deck-level report.
- Optional "Session" combobox on the BO3 match form (create + edit),
  matching `OpponentDeckField`'s searchable-combobox + inline-create
  UX; a closed session still resolves its name for an already-assigned
  match but can't be re-selected.
- Dedicated "Sessions" tab (`/app/sessions`, 4th tab, after "My
  decklist"): a single list of sessions scoped to the active personal
  deck (create/close/reopen/archive, a status badge per row) and a
  summary for whichever session is selected — stat tiles, W/L record,
  and a per-opponent-deck matchup comparison table (session vs. the
  deck's history before it started). `ExpectedMetagameSection` moved
  out of the Metagame tab into this summary, shown only for
  tournament-typed sessions.
- Match journal rows and the View popup show a session badge (name,
  colored by session type) when a match belongs to one.
- New `owner`/`shared`/`tournament` badge variants with dedicated
  OKLCH color tokens, visually distinct from the existing semantic
  badges (`warning`/`destructive`/`success`).
- App logo (`/favicon.svg`) shown next to the "Tamiyo Scroll" header
  title.
- Admin-only usage/metrics page (`AdminMetricsPage`, gated the same way
  as every other protected route, reachable only to `admin`-role
  accounts): flat account/deck/match totals, plus a day/week/month
  time-bucketed chart per metric (new `recharts` dependency — no
  charting library existed in this app before).
- Public, unauthenticated demo/tutorial interface at `/demo` (linked
  from `LoginPage` and `RootRedirect`): a fixture-backed
  (`src/demo/fixtures.json`) mirror of the real app — all five tabs
  (Tracker, Metagame, Decklist, Sessions, Team), matching prod's tab
  order and default landing tab — plus a guided-tour overlay (existing
  Radix/shadcn primitives, no new dependency) walking through the seeded
  data. Nothing typed/edited during a demo session is ever sent to
  `barrins_api` or persisted anywhere; a page reload resets it. Winrate/
  conversion figures are computed by a line-for-line port of the
  backend's own formulas (`demo/api/statsCore.ts`), not a separate,
  divergent calculation.
- `game` (S10) and `category`/macrotype (S11) selectors, **required**,
  on personal-deck creation; an inline "set game"/"set macrotype"
  affordance (calling the new `PATCH /personal-decks/{id}`) wherever a
  `NULL`-valued historical deck blocks match logging/editing; a
  one-time, dismissible migration notice explaining the new required
  fields; and a colored macrotype badge (same tokens as the stats block)
  shown wherever a deck is displayed or selected.
- Personal-deck creation's inline "Create …" row now shows a green
  `[new]` label while the typed name doesn't match an existing deck.
- The tested-cards deck select (`CardTestsSection`, create form and edit
  row) is rebuilt on the same search + shared-deck-badge combobox
  pattern already used by the BO3 opponent select.
- A new "Display" section in the account-settings popup: four
  `localStorage`-backed, per-browser preferences (not synced
  server-side) — match-up row background tint by winrate band (default
  on), "2W / 0L"-style result format (default off), colored roster
  archetype cell (default off), and a 3-color roster tier background
  (default off).
- Deleting a roster deck now asks for confirmation before archiving it.

### Changed

- The existing "shared"/"multi share"/"w/ shared" data-sharing badges
  and the session type "Tournament" badge now use the new dedicated
  `shared`/`tournament` badge colors instead of piggybacking on
  `accent`; the match journal's session tag is now prefixed with its
  type label, since color alone no longer doubles as the "shared"
  indicator.
- `useUpdateMySettings` now invalidates matches/meta-decks/stats
  queries, so toggling share/receive updates those views immediately
  instead of showing stale merge results until an unrelated refetch.
- Route `/app/bo3-tracker` renamed to `/app/tracker` (`App.tsx`,
  `LoginPage.tsx`/`VerifyEmailPage.tsx` redirects, `README.md`).
- Favicon redesigned as a dark card with a white open-book mark and a
  small accent checkmark, replacing the previous abstract purple mark,
  to match the app's own OKLCH design tokens.
- `MetagameTab.tsx`: sections reordered for improved layout.
- Match journal's "Final turn" field relabelled; the underlying
  `final_turn`/`finalTurn` field name is unchanged (display-only).
- Match-up summary table: "Games" column header relabelled "Matches"
  (still the same `match_count` value); the six non-"Vs. deck" columns
  are narrower so the deck-name column gets the freed space; the
  winrate-band legend now renders above the table instead of below;
  the W/L OTP/OTD cells render in muted grey instead of the default
  text color.

### Fixed

- A BO3 with no game won at all (e.g. a loss + a draw with the third
  game unplayed) now reads as a loss instead of falling through to the
  "draw" badge — the match can no longer be won at that point. "Draw"
  is now reserved for a genuine no-majority result once all three
  games have actually been played.
- `index.html` title: corrected spelling from "Tamyio" to "Tamiyo".
- Current-decklist legend swatch color never applied — it was derived
  at runtime (`DECKLIST_LINE_STATUS_TEXT_CLASS[status].replace('text-',
  'bg-')`), which Tailwind's class scanner can't detect since only
  literal class strings get built. Added an explicit
  `DECKLIST_LINE_STATUS_BG_CLASS` map instead, and moved the legend row
  up next to the version controls.

## [1.0.0] "WorldWake" - 2026-07-24

### Added

- Initial scaffold of the Tamiyo Scroll frontend (React 19, TypeScript,
  Vite, React Router, TanStack Query, Zod, TailwindCSS, shadcn/ui
  components).
- Authentication flow: login page, self-registration email verification
  page, and a `ProtectedRoute` guard backed by a session store
  consuming the `barrins_api` `/api/v1/auth` endpoints.
- Metagame tab: personal decks list with Moxfield decklist import, a
  meta/opponent deck roster, and aggregated archetype/matchup
  statistics sections.
- Suivi BO3 tab: match journal, new-match form, and card-test feedback
  section, backed by the BO3 match log and card-test BFF endpoints.
- Decklist tab: current decklist view (colored by card-test feedback)
  and version history section.
- Read-only "viewing owner" selector (header) and `active-deck-context`
  for sharing another user's data without allowing edits, per the
  BFF's read-only sharing settings.
- App shell layout with tab navigation, and a centralized typed API
  client (`src/api/client.ts`) with Zod-validated request/response
  schemas (`src/schemas/tamiyoScroll.ts`).
- Test suite (Vitest + Testing Library) covering the API client, card
  tests, active-deck context, match form, and card-tests section.
- `LoginPage.tsx`: live password requirements checklist on signup,
  mirroring `PASSWORD_PATTERN` in `apps/barrins_api/app/schemas/auth.py`
  (12+ characters, upper/lowercase, digit, symbol) so users see which
  rules they still need to satisfy as they type. UX feedback only —
  the backend remains the sole source of truth on submit.
- `PersonalDeckSelector.tsx`: an archive (delete) button per deck in
  the list, wired to the already-existing `DELETE
  /personal-decks/{id}` endpoint (soft-delete via `archived_at`, never
  a hard delete) and `useArchivePersonalDeck` hook — both existed
  backend-side but had no UI entry point. Guarded behind a
  confirmation dialog (`ui/dialog.tsx`) so a stray click can't archive
  a deck. Archiving the currently-active deck also clears
  `active_personal_deck_id`.
- `AppShell.tsx`: a "Welcome, {display_name}" greeting next to the Log
  out button, using `useCurrentUser` (`GET /api/v1/auth/me`, already
  implemented but unused in the UI). Falls back to the account email
  when no display name is set.

### Changed

- Route `/app/suivi-bo3` renamed to `/app/bo3-tracker` (`App.tsx`,
  `AppShell.tsx`'s tab nav, `LoginPage.tsx`, `VerifyEmailPage.tsx`,
  `README.md`). The `pages/suivi-bo3/` folder and `SuiviBo3Tab`
  component name are unaffected — internal naming, not the route.
- Post-login, post-signup, and post-email-verification now redirect to
  `/app/bo3-tracker` instead of `/app/metagame`, landing users on the
  match tracker first.
- Translated `README.md` from French to English.
- Translated remaining French UI text (labels, buttons, placeholders,
  error messages) and code comments across the app — `index.css`,
  `active-deck-context.tsx`, `lib/mtg-format.ts`,
  `schemas/tamiyoScroll.ts`, `LoginPage.tsx`, `VerifyEmailPage.tsx`,
  the decklist, metagame, and Suivi BO3 sections, `AppShell.tsx`,
  `lib/store.ts`, `lib/queryClient.ts`, `api/client.ts`,
  `api/viewingOwner.ts`, and `hooks/useViewingOwner.ts` — to English.
- The "Share my data" checkbox and "View: {user}" selector extracted
  into `SharingControls`, disabled for v1.0.0 (not mature enough — the
  underlying backend enforcement is fully tested, but this UI had no
  component-level test). `AppShell`'s deck selector no longer branches
  on `canEdit`/viewing-mode, since there's no UI path left to enter it.
- `CurrentDecklistSection.tsx`, `PersonalDecklistImportSection.tsx`,
  and `CardTestsSection.tsx` now render nothing (`null`) instead of a
  "Select or create a personal deck…" placeholder card when no
  personal deck is active (e.g. right after archiving one) — matches
  `VersionHistorySection.tsx`'s existing behavior for the same state.

### Fixed

- `VerifyEmailPage.tsx`: footer credit read "Account managed by
  barrins_api" — corrected to `barrins_identity`, the actual identity
  service.
- `PersonalDecklistImportSection.tsx`: `handleImport` (Moxfield URL)
  and `handleSaveRaw` (raw decklist text) never caught a failed
  mutation, so a backend error (e.g. `400` on an invalid/non-Moxfield
  URL) silently vanished instead of reaching the user — found via the
  A3 manual UAT step. Both now catch `ApiError` and render the message
  inline, mirroring `LoginPage`'s existing pattern.
- `vite.config.ts`: stubbed `VITE_API_BASE_URL` via Vitest's `test.env`
  so `src/api/client.ts` doesn't build requests against `"undefined"`
  during tests. The variable was only ever supplied by a local,
  gitignored `.env` file, so every CI run (including the `front` job
  for otherwise-unrelated Dependabot bumps) failed 6 `client.test.ts`
  tests with `TypeError: Invalid URL`.
