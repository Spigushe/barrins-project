# S7. Tutorial + demo interface (combined), no persistence

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tamiyo_scroll` only — no backend changes | / |
| **Initial date** | / | Not started |
| **Status** | ✅ Done (S7 shipped `2b956b4`); extended 2026-08-03 — 5 bugs found comparing `/demo` against prod, all fixed. See "Extension (2026-08-03)" below | / |
| **Source** | Request; `v2.0.0-bump/index.md` §1.8 | / |
| **Dependency** | None | / |

---

## Context

**Fully decided, nothing open**: one combined demo + tutorial
experience, pure frontend mock (no network calls at all — "no
persistence" holds structurally, not by a reset job), fixture data
authored in a single JSON file, guided-tour overlay built with the
existing Radix/shadcn primitives already in `src/components/ui/` (no
new dependency — this also settles the Playwright question raised
during planning: Playwright doesn't fit this item and isn't part of it).

## Done statement

- A new public route (e.g. `/demo`), reachable with no authentication,
  never issuing or requiring a token, never calling `barrins_api`.
- A parallel data-source module mirrors each `src/api/*.ts` file's
  function signatures, backed by `src/demo/fixtures.json` (static
  import), held in local component/context state reset fresh on every
  page load.
- A `DemoModeProvider` (or equivalent context) supplies this module in
  place of the real one; `MetagameTab`, `SuiviBo3Tab`, and
  `DecklistTab` render **unmodified** against whichever source is
  active.
- A guided-tour overlay (tooltips/step markers using existing
  `popover.tsx`/`dialog.tsx`/`card.tsx` primitives) walks through the
  seeded demo screens.
- Entry point: a link from `LoginPage` (near its existing "Account
  managed by `barrins_api`" footer line) and from `RootRedirect` in
  `App.tsx`.
- Anything a demo visitor adds, edits, or deletes during the session
  disappears on reload — verified, not just assumed from the
  architecture.

## Tasks

- [x] Author `src/demo/fixtures.json`: sample personal decks, meta
      decks/roster, matches, and card-tests across all three tabs —
      invented for this purpose, never real user data.
- [x] Build the parallel data-source module (one function per
      `src/api/*.ts` file's exported functions, same signatures).
- [x] Build `DemoModeProvider` and wire it so `MetagameTab`/
      `SuiviBo3Tab`/`DecklistTab` consume it transparently in demo mode.
- [x] Add the `/demo` route in `App.tsx`, fully public.
- [x] Build the guided-tour overlay with existing primitives.
- [x] Add entry-point links from `LoginPage` and `RootRedirect`.

## UAT (manual)

- [x] Visit `/demo` with no account; confirm every tab renders
      pre-filled data with no login prompt.
- [x] Add a match/edit a decklist/create a card-test in the demo;
      reload the page; confirm none of it persisted.
- [x] Confirm the browser's network tab shows zero requests to
      `barrins_api` at any point while in `/demo`.
- [x] Walk through the guided tour end-to-end; confirm every step
      points at real, visible content on screen (no step pointing at an
      element that isn't rendered).

## Non-regression tests

- New Vitest suite for the demo data-source module (same function
  signatures as the real `src/api/*.ts` modules, verified via a shared
  type/interface both implement).
- A test asserting `MetagameTab`/`SuiviBo3Tab`/`DecklistTab` render
  identically (same component tree) whether fed by the real API client
  or the demo module — the "reuse, don't fork" requirement.

---

## Extension (2026-08-03)

**Context**: `/demo` was built for S7 against the 3-tab app that existed
at the time. Prod grew to 5 tabs since (S9 Sessions, S2 Teams), and the
user found 5 concrete divergences testing `/demo` against prod. All are
fixed on `feat/v2-tamiyo-upgrade`, no doc/scope decisions left open.

### Bugs found + root cause + fix

1. **Tab order didn't match prod.** `DemoPage.tsx`'s `TAB_LABELS` was
   `metagame, tracker, decklist`; `AppShell.tsx`'s `TABS` is
   `tracker, metagame, decklist, sessions, team`. Reordered to match
   exactly (default *landing* tab stays `metagame`, matching
   `RootRedirect`'s `Navigate to="/app/metagame"` for a logged-in user —
   tab *order* and default *landing tab* are independently prod-accurate
   facts, not the same thing).

2. **Sessions and Teams tabs missing.** Didn't exist yet when S7 shipped.
   Added both:
   - **Sessions**: `SessionsTab`/`SessionsOverviewSection` reused
     **unmodified** (already router-free, local-state-driven — same
     "reuse, don't fork" bar as the original 3 tabs). `demo/api/sessions.ts`
     extended with the full CRUD + comparison surface
     (`createSession`/`updateSession`/`archiveSession`/
     `getSessionComparison`/`getSessionReportPdf`), mirroring
     `_compute_session_stats` exactly: baseline = the same personal
     deck's matches with `created_at < session.created_at`, session =
     matches with that `session_id`.
   - **Teams**: the real `TeamsTab`/`TeamPage`/`TeamCreateJoinPage`
     navigate via `/app/team/*` routes (`NavLink`/`Outlet`/`useParams`),
     which sit outside `/demo` and behind `ProtectedRoute` — reusing them
     unmodified was the root cause of bug 5 below, not a viable path.
     Instead: `TeamPage.tsx` split into a thin route wrapper (`TeamPage`,
     unchanged behavior — pulls `teamId`/`currentUserId` from
     `useParams`/`useCurrentUser`) and a new `TeamPageContent({ teamId,
     currentUserId })` taking both as props. A new demo-only
     `DemoTeamsSection.tsx` composes `TeamJoinCreatePanel` (already
     prop-driven, reused as-is) and `TeamPageContent` with a local
     `useState` team switcher instead of routing — same pattern
     `DemoPage`'s own top-level tabs already use. `demo/api/teams.ts`
     (new) implements the full surface (team CRUD, member management,
     deck flagging, discussion threads) against a new `DemoTeam` shape in
     `demoStore.ts` (richer than the wire `Team` schema — adds the
     member-deck pool and per-name-key flags/threads the real backend
     derives from separate tables). A fixed demo identity
     (`DEMO_CURRENT_USER_ID`, sourced from `fixtures.json`'s
     `currentUser`) stands in for `useCurrentUser()` so `TeamPageContent`
     can render the *owner* experience (flagging, description edit,
     member removal) without the demo ever touching real auth/session
     state — considered and rejected faking an access token for this:
     it would let a stray browser back/forward into `/app/*` present a
     token with nothing real behind it.

3. **Winrate was structurally wrong, not just off.** `demo/api/stats.ts`
   computed *match*-level majority-of-3 (draws weighted 0.5) and
   returned a 0-1 fraction. The real backend
   (`app/services/tamiyo_scroll/stats.py`) tallies *games*
   (`game1`/`game2`/`game3`) directly — `wins/(wins+losses)*100`, draws
   excluded entirely from the denominator, 0-100 scale. Since
   `formatPercent()` assumes an already-0-100 value, every demo winrate
   rendered as `0%` or `1%`. Fixed by extracting the calculation into
   `demo/api/statsCore.ts`, a line-for-line port of `_tally_games`/
   `_winrate`/`_ratio`/`compute_archetype_summary`/
   `compute_matchup_summary` (Constitution §4.2 — no parallel
   calculation path), reused by both `stats.ts` and the new session
   comparison endpoint.

4. **Conversion had the same scale bug, plus one inconsistent fixture
   value.** `conversionOf()` returned `top8/presence` (0-1) instead of
   the backend's `@computed_field` (`round(top8/presence*100, 2)`), and
   `listMetaDecks()` returned the fixture's stored `conversion` as-is
   instead of recomputing it — Mono White Aggro's stored value (`0.5`)
   didn't match its own `top8`/`presence` (2/7 ≈ 28.6%) under *either*
   scale. Fixed: `conversionOf()` now matches the backend formula
   exactly, and `listMetaDecks()` recomputes it on every read (never
   trusts storage), matching the backend's always-fresh computed field.

5. **Top8 counts, demo-only rule**: per the user, the *sum* of `top8`
   across the demo's seeded meta decks must stay ≤ 8 (only 8 seats exist
   in an actual top 8) — a constraint specific to this fixture set for
   plausibility, not a backend validation rule. The seeded values summed
   to 15 (4+3+2+5+1); rebalanced to sum to 8 (2+2+1+2+1), conversions
   recomputed to match.

6. **UI "crash"/"blink to login" switching tabs** turned out to be
   *three* independent bugs, all fixed:
   - Clicking into a team (once Teams existed) navigated through
     `TeamsTab`'s real `/app/team/*` routes, which `ProtectedRoute`
     bounces to `/login` with no access token present — this is bug 2's
     Teams root cause, not a separate defect. Fixed by never routing at
     all in `DemoTeamsSection` (see above).
   - The guided tour's highlight ring/popover (`DemoTour.tsx`) was
     offset from its target heading. It called
     `target.scrollIntoView({ behavior: 'smooth' })` then immediately
     read `target.getBoundingClientRect()` on the next line — a smooth
     scroll animates over several frames, so that rect reflects the
     heading's *pre-scroll* position, and nothing re-measured it once
     the animation finished (only a `resize` listener existed, and
     `scrollIntoView` doesn't fire one). Fixed by switching to
     `behavior: 'auto'` (no `scroll-behavior: smooth` CSS anywhere in
     this app, so `'auto'` scrolls synchronously — the immediate rect
     read is already correct).
   - **The actual dominant cause, found after the above two didn't fully
     account for a persisting (if less frequent) blink-to-login on
     plain tab switches, unrelated to Teams or the tour**:
     `DemoModeProvider` installed the fetch interceptor via a lazy
     `useState` initializer (so it's live before any child's first query
     — a child's effects run before its parent's, so installing in
     `useEffect` would let that first query leak through un-intercepted)
     but only *tore it down* via `useEffect`'s cleanup, returning the
     already-captured cleanup closure rather than calling
     `installDemoFetch()` again. React's Strict Mode (`main.tsx` wraps
     `<App />` in it, dev-only) mounts effects, runs their cleanup, then
     mounts them again specifically to catch exactly this shape of bug:
     install fires once, the simulated cleanup reverts `window.fetch` to
     the real one, and the simulated remount's effect body does nothing
     to put it back. Radix `Tabs` unmounts inactive content
     (`staleTime: 0` forces a refetch on remount), so the *first* tab's
     queries — fired before Strict Mode's cycle completed — looked fine,
     but every subsequent tab switch fired fresh queries over the real
     `fetch`, 401'd with no token, and `client.ts`'s
     `fetchWithAuthRetry` hard-navigated to `/login` on the failed
     refresh (`window.location.assign('/login')`). Fixed by having the
     effect call `installDemoFetch()` itself (idempotent — a no-op on
     the very first pass, a genuine reinstall on Strict Mode's simulated
     remount) instead of just re-returning a stale cleanup reference.

### Non-regression tests added

- `demo/api/__tests__/demoApi.test.ts`: full CRUD/schema coverage for
  the expanded `sessions`/new `teams` demo modules (mirrors the existing
  per-module pattern), plus explicit regression assertions for bugs 3-5
  (winrate on a 0-100 scale from a known fixture match, conversion
  matching `top8/presence*100` and always recomputed, `sum(top8) <= 8`).
- `demo/__tests__/demoPage.test.tsx` (new): asserts the 5-tab order
  matches `AppShell.TABS` exactly, and that switching into Sessions then
  Teams renders their content locally with no redirect away from
  `/demo` — the regression test for bug 6's Teams-routing cause.
- `demo/__tests__/demoModeProvider.strictMode.test.tsx` (new): renders
  `DemoModeProvider` inside an explicit `<StrictMode>` (RTL's `render`
  doesn't add one by default) and asserts `window.fetch` is still the
  demo router afterward — the regression test for bug 6's dominant
  cause. Verified meaningful by temporarily reverting the
  `DemoModeProvider` fix and confirming this test fails without it.
