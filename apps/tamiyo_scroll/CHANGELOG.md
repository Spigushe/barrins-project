# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

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

### Fixed

- `VerifyEmailPage.tsx`: footer credit read "Account managed by
  barrins_api" — corrected to `barrins_identity`, the actual identity
  service.
- `vite.config.ts`: stubbed `VITE_API_BASE_URL` via Vitest's `test.env`
  so `src/api/client.ts` doesn't build requests against `"undefined"`
  during tests. The variable was only ever supplied by a local,
  gitignored `.env` file, so every CI run (including the `front` job
  for otherwise-unrelated Dependabot bumps) failed 6 `client.test.ts`
  tests with `TypeError: Invalid URL`.
