# T5. `apps/tolaria_news` real frontend

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tolaria_news` (React/Vite) | Currently a one-line README only |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on T4 and I1 | / |
| **Source** | Request item 1 | / |
| **Dependency** | T4, I1 (shared identity — if this app needs auth at all) | Blocks nothing further downstream |

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

## Done statement

- A real React/Vite app scaffolded at `apps/tolaria_news`, calling only
  T4's BFF (Constitution §4.1/§4.2 — no client-side computation of
  aggregates), matching `VITE_API_BASE_URL`'s existing build-time
  injection pattern already used by `tamiyo_scroll`
  (`ops/my-server/`'s `react_frontend_build_env`).
- Deployable through the existing `tolaria_news.yml` playbook with no
  playbook changes needed — it was built in advance for exactly this.

## Tasks

- [ ] Confirm whether this frontend needs any authenticated surface at
      all for v2.0.0 (if none: I1 stops blocking this item entirely).
- [ ] Scaffold with Vite + React + TypeScript, matching
      `tamiyo_scroll`'s toolchain choices (TanStack Query, Zod, Tailwind,
      shadcn/ui) for consistency unless a reason emerges not to.
- [ ] Build the core screens (tournament list/detail, deck/standing
      views) against T4's routes.
- [ ] Update `apps/tolaria_news/README.md`/`CHANGELOG.md` (currently
      placeholders) with real content.
- [ ] **Optional**: render the Manatraders "rent this deck" link on each
      deck view, once T4 adds it to `DeckDetail` — see "Optional
      enhancement" below. No client-side link-building; the backend
      provides the finished URL. Not required for T5's own done statement.

## UAT (manual)

- [ ] `ansible-playbook tolaria_news.yml -e deploy_env=staging` succeeds
      and serves the real app (today it would serve nothing/fail, since
      there's no code).
- [ ] Browsing the deployed staging site shows real tournament data from
      the BFF, with no client-side recomputation of anything the backend
      already provides.

## Non-regression tests

- New Vitest + Testing Library suite, mirroring `tamiyo_scroll`'s
  existing test conventions (`__tests__/`, component tests colocated
  with pages).

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
