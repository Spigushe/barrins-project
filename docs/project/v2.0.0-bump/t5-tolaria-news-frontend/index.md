# T5. `apps/tolaria_news` real frontend

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tolaria_news` (React/Vite) | Currently a one-line README only |
| **Initial date** | 2026-08-14 | / |
| **Status** | 🟡 **In progress** (2026-08-14) — app scaffolded (routing, BFF client, all v1 screens, tests), lint/typecheck/build/test all clean; staging deploy UAT not yet exercised. A further Landing/Tournaments appearance-and-data study against the archive prototype is done, decisions pending — see [archive-comparison.md](archive-comparison.md) | / |
| **Source** | Request item 1 | / |
| **Dependency** | T4 (done), I1 (resolved — see Context) | Blocks nothing further downstream |

---

## Context

`ops/my-server/tolaria_news.yml` already exists and deploys
`apps/tolaria_news` from this monorepo — it's just waiting for real
code. Its own comments note today's state plainly: "no application code
(README.md only)." Since the Tolaria News BFF (T4) is public/read-only,
this frontend may not need any authentication at all for its core
purpose (browsing tournament results) — worth confirming during design
whether any admin/write surface is planned for it, which would be the
only reason I1 actually blocks this item.

**Unblocked (2026-08-14)**: T4 shipped 2026-08-11 — every
`/bff/tolaria-news/*` route is public, with zero `CurrentUser` usage
(enforced by its own `TestNoAuthRequired` suite) and no admin/write
surface planned. That answers this item's own first task directly: this
frontend needs no authenticated surface for v2.0.0, so I1 (already
resolved project-wide in §1.5 as "not blocking, with a condition") stops
blocking this item entirely. Implementation started the same day.

**Design handoff discovered during implementation (2026-08-14)**: a full
design handoff exists at `handoff/design_handoff_tolaria_news/`
(`DESIGN_SYSTEM.md`, `PAGES.md`, `BFF.md`, `API_TYPES.ts`), describing a
materially larger app — a landing page with a decorative node-graph viz,
six routes including `/decklists` with a search DSL, forecasts, `⌘K`
search, sign-in — against a speculative `/bff/v1/*` API that doesn't
exist (T4 only ships `/bff/tolaria-news/*`; T6 "Karn Tablets," which
would back archetypes/metagame/trends, is not started). **Scoped by the
user, 2026-08-14: restyle only.** The design system (Midnight palette,
EB Garamond/Geist/JetBrains Mono, teal accent, the `icon.svg` sigil,
Nav+BottomRail shell, Eyebrow component) is adopted; the larger
speculative IA/BFF is not built. Karn-Tablets-tied pages stay prepared
ahead of their backend and gated behind `VITE_FEATURE_KARN_TABLETS`
(default off) — the same pattern already used for T4 iteration 2's
BFF routes, now carried through to the frontend. The tournament list's
`format` filter is fixed to `"Duel Commander"` (this app's sole scope,
per its own README) rather than user-editable, per the same 2026-08-14
direction.

## Done statement

- A real React/Vite app scaffolded at `apps/tolaria_news`, calling only
  T4's BFF (Constitution §4.1/§4.2 — no client-side computation of
  aggregates), matching `VITE_API_BASE_URL`'s existing build-time
  injection pattern already used by `tamiyo_scroll`
  (`ops/my-server/`'s `react_frontend_build_env`).
- Deployable through the existing `tolaria_news.yml` playbook with no
  playbook changes needed — it was built in advance for exactly this.

## Tasks

- [x] Confirm whether this frontend needs any authenticated surface at
      all for v2.0.0 (if none: I1 stops blocking this item entirely) —
      confirmed no, see Context.
- [x] Scaffold with Vite + React + TypeScript, matching
      `tamiyo_scroll`'s toolchain choices (TanStack Query, Zod, Tailwind,
      shadcn/ui) for consistency unless a reason emerges not to.
- [x] Build the core screens (tournament list/detail, deck/standing
      views) against T4's routes — plus the bracket route (added to v1
      after this page was first written) as a third detail tab.
- [x] Prepare `/metagame`, `/archetypes`, `/trends` (T4 iteration 2 / T6)
      ahead of their backend, gated behind `VITE_FEATURE_KARN_TABLETS`
      (default off) — not in this item's original task list, added
      2026-08-14 per user direction alongside the design restyle below.
- [x] Apply the design handoff's visual system (restyle only — see
      Context) — Midnight palette, EB Garamond/Geist/JetBrains Mono,
      teal accent, `icon.svg` sigil as favicon + nav mark, Nav+BottomRail
      shell, Eyebrow component.
- [x] Update `apps/tolaria_news/README.md`/`CHANGELOG.md` (currently
      placeholders) with real content.
- [ ] **Optional**: render the Manatraders "rent this deck" link on each
      deck view, once T4 adds it to `DeckDetail` — see "Optional
      enhancement" below. No client-side link-building; the backend
      provides the finished URL. Not required for T5's own done statement.
- [ ] **Pending decision (2026-08-14)**: whether to further adapt
      Landing/Tournaments' appearance and data toward
      `barrins-archive/tolaria_news` (the same design-handoff prototype
      referenced above) — study and per-page breakdown at
      [archive-comparison.md](archive-comparison.md). Not started; waiting
      on the two open calls recorded there.

## UAT (manual)

- [ ] `ansible-playbook tolaria_news.yml -e deploy_env=staging` succeeds
      and serves the real app. Not yet exercised from this environment
      (no infra access) — `npm run build` succeeds locally and the
      playbook needs no changes to pick up the new code (§ Done
      statement).
- [ ] Browsing the deployed staging site shows real tournament data from
      the BFF, with no client-side recomputation of anything the backend
      already provides.
- [ ] With `VITE_FEATURE_KARN_TABLETS` unset in the deployed environment,
      confirm the Metagame/Archetypes/Trends nav links and routes are
      unreachable (redirect to `/`).

## Non-regression tests

- Vitest + Testing Library suite, mirroring `tamiyo_scroll`'s existing
  test conventions (colocated `*.test.tsx`, hooks layer mocked rather
  than `fetch`): `TournamentListPage` (rows, pagination via cursor,
  empty state), `TournamentDetailPage` (tab switching, empty-bracket
  state), `DeckDetailPage` (with/without resolved commanders),
  `FeatureGate` and `AppShell` nav (both flag states). 12 tests, all
  passing; `npm run lint`/`format:check`/`build` also clean.

---

## Optional enhancement: Manatraders "rent this deck" link

**Status**: 🔲 Optional, not scheduled — investigated 2026-08-11, no
decision to build yet. Not a T5 blocker; T5 ships without this either way.

### Request

For each deck displayed on Tolaria News, add an "MTGO Rent" link using the
[Manatraders API](https://www.manatraders.com/settings/api) — a service
that lets players rent Magic Online cards/decks instead of buying them.

### Investigation

Manatraders' API documentation (`manatraders.com/settings/api`) describes
several endpoint families. The relevant one for this request needs no
account, no API key, and no server-to-server call at all:

- **Load Deck** (public deep-link, no auth):
  `https://www.manatraders.com/load-deck?medium=<tag>&c=<qty> <name>||<qty>
  <name>&friendly_name=<optional>` — encodes an entire decklist (`||`
  between entries, `||||` before the sideboard) into one URL that opens
  Manatraders with the deck pre-loaded into the rental cart. Rate limit:
  200 requests/10s per IP for public deep-links (irrelevant here — this is
  a user-clicked link, not a server call).
- **Rent single card** / **Buy single card**: same shape, per-card
  (`?name=<card>` / `?scryfall_id=<id>`), also public/unauthenticated.
- A separate, *authenticated* API family exists (bearer-token, "All Cards"
  catalog, subscription price calculator) — not needed for this feature;
  not investigated further since the public deep-link covers the request.
- `medium` is an optional referral tag. Using one requires registering as
  a Manatraders partner ("submit a request and we'll review it") — without
  it, the link still works, it just carries no referral attribution.

### Costs

- **No monetary cost.** No API key, no paid tier, no rate-limit-driven
  infrastructure need — this is a plain URL built from data
  `GET /bff/tolaria-news/decks/{id}` already returns (`mainboard`,
  `commanders`).
- **Third-party dependency, but a soft one.** No secret, no server-side
  call, no new Python/JS package (Constitution §22 doesn't apply — it's
  string formatting + URL encoding, not a client library). If Manatraders
  changes its URL format, the link breaks silently (a dead/wrong outbound
  link), not an outage of Tolaria News itself — the BFF has nothing to
  catch or retry.
- **Product/brand consideration, not a technical one**: this sends users
  to a commercial rental service. Worth the user's explicit sign-off as a
  deliberate choice, not something to ship silently because it's cheap.
- **Referral registration**, if pursued, is a small one-time step (an
  account and a partner-access request) — optional, not required for the
  link to function.

### Gains

- User convenience: one click from a decklist to "rent this on MTGO"
  instead of manually re-typing/importing the list elsewhere.
- Optional referral revenue if registered as a Manatraders partner (paid
  monthly to a Manatraders wallet, per their docs) — small, passive upside
  with no development cost beyond adding the `medium` param once an id
  exists.

### If pursued: where it lands

- **Backend** (T4): `GET /bff/tolaria-news/decks/{id}` gains a computed
  field (e.g. `manatraders_rent_url: str`) built from the same
  `mainboard`/`commanders` data already in `DeckDetail` — no new query, no
  schema change, no new dependency. See T4's page, "Optional enhancement"
  note.
- **Frontend** (T5): renders the link as-is; no URL-building logic in
  `apps/tolaria_news` (Constitution §4.1 — the frontend displays, it
  doesn't compute).

### Open, if the user decides to move forward

- Confirm the product/brand call above.
- Decide whether to register for a `medium` referral id before or after
  shipping the link (the link works either way).
- Decide priority relative to T4 iteration 2 (Karn Tablets-tied routes) —
  this has no dependency on that work and could ship first, since it's
  strictly smaller.
